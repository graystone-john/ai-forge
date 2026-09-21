#include <Arduino.h>
#include <M5Unified.h>
#include "USB.h"
#include "USBHIDKeyboard.h"
#include <NimBLEDevice.h>


#include "USBMSC.h"
#include "esp_partition.h"

USBMSC ForgeDrive;
static const esp_partition_t* forgePartition = nullptr;
static uint8_t flashSector[4096];
static SemaphoreHandle_t keyboardMutex = nullptr;

static int32_t diskRead(uint32_t lba, uint32_t offset,
                        void* buffer, uint32_t length) {
  if (!forgePartition) return -1;
  uint64_t address = uint64_t(lba) * 512 + offset;
  if (address + length > forgePartition->size) return -1;
  return esp_partition_read(forgePartition, size_t(address),
                            buffer, length) == ESP_OK
         ? int32_t(length) : -1;
}

static int32_t diskWrite(uint32_t lba, uint32_t offset,
                         uint8_t* buffer, uint32_t length) {
  if (!forgePartition) return -1;
  uint64_t address = uint64_t(lba) * 512 + offset;
  if (address + length > forgePartition->size) return -1;

  uint32_t remaining = length;
  size_t position = size_t(address);
  while (remaining) {
    size_t base = position & ~size_t(4095);
    size_t within = position - base;
    size_t count = remaining;
    if (count > 4096 - within) count = 4096 - within;

    if (esp_partition_read(forgePartition, base,
                           flashSector, 4096) != ESP_OK) return -1;

    if (memcmp(flashSector + within, buffer, count) != 0) {
      memcpy(flashSector + within, buffer, count);
      if (esp_partition_erase_range(forgePartition, base, 4096)
          != ESP_OK) return -1;
      if (esp_partition_write(forgePartition, base,
                              flashSector, 4096) != ESP_OK) return -1;
    }

    position += count;
    buffer += count;
    remaining -= count;
  }
  return int32_t(length);
}

static bool diskStartStop(uint8_t powerCondition,
                          bool start, bool loadEject) {
  // Writes are synchronous; there is no pending RAM write cache.
  return true;
}

static void startForgeDrive() {
  // Reuse the existing partition's label and boundaries.
  // Do not mount this partition as SPIFFS in the firmware.
  forgePartition = esp_partition_find_first(
      ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_ANY, "spiffs");

  if (!forgePartition || forgePartition->size != 0x180000) {
    Serial.println("FORGE storage partition missing or wrong size");
    return;
  }

  ForgeDrive.vendorID("GRAYSTON");
  ForgeDrive.productID("FORGE");
  ForgeDrive.productRevision("1.0");
  ForgeDrive.onRead(diskRead);
  ForgeDrive.onWrite(diskWrite);
  ForgeDrive.onStartStop(diskStartStop);
  ForgeDrive.mediaPresent(true);
  ForgeDrive.begin(forgePartition->size / 512, 512);
}

USBHIDKeyboard Keyboard;

static const char* SERVICE_UUID =
    "6E400001-B5A3-F393-E0A9-E50E24DCCA9E";

static const char* RX_UUID =
    "6E400002-B5A3-F393-E0A9-E50E24DCCA9E";

void typeText(const char* text) {
  if (!keyboardMutex ||
      xSemaphoreTake(keyboardMutex, 0) != pdTRUE) return;
  while (*text) {
    Keyboard.write(*text);
    delay(20);
    text++;
  }
  xSemaphoreGive(keyboardMutex);
}

class ReceiveCallbacks : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic* characteristic,
               NimBLEConnInfo& connectionInfo) override {
    std::string value = characteristic->getValue();

    if (!value.empty()) {
      typeText(value.c_str());

      Serial.print("BLE received: ");
      Serial.println(value.c_str());
    }
  }
};

class ServerCallbacks : public NimBLEServerCallbacks {
  void onDisconnect(
      NimBLEServer* server,
      NimBLEConnInfo& connectionInfo,
      int reason
  ) override {
    delay(100);
    NimBLEDevice::startAdvertising();
    Serial.println("BLE client disconnected; advertising restarted");
  }
};

void setup() {
  auto config = M5.config();
  M5.begin(config);

  Serial.begin(115200);

  keyboardMutex = xSemaphoreCreateMutex();
  Keyboard.begin();
  startForgeDrive();
  USB.begin();

  NimBLEDevice::init("Graystone-HID");

  NimBLEServer* server = NimBLEDevice::createServer();
  server->setCallbacks(new ServerCallbacks());

  NimBLEService* service = server->createService(SERVICE_UUID);

  NimBLECharacteristic* rx = service->createCharacteristic(
      RX_UUID,
      NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR
  );

  rx->setCallbacks(new ReceiveCallbacks());

  service->start();

  NimBLEAdvertising* advertising = NimBLEDevice::getAdvertising();
  advertising->addServiceUUID(SERVICE_UUID);
  advertising->start();

  Serial.println("Graystone-HID BLE ready");
  Serial.println("Mount FORGE, focus a Linux terminal, then press the top button.");
}

void loop() {
  M5.update();

  if (M5.BtnA.wasPressed()) {
    typeText("bash -c 'd=$(readlink -f /dev/disk/by-label/FORGE); m=$(findmnt -nr -S \"$d\" -o TARGET); if [ -n \"$m\" ]; then bash \"$m/RUN.SH\"; else echo \"Mount the FORGE USB drive, then press the button again.\"; fi'\n");
    Serial.println("FORGE launcher command sent");
  }

  delay(40);
}