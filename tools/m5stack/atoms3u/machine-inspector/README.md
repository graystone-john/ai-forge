# ATOMS3U Machine Inspector

M5Stack ATOMS3U PlatformIO project providing USB keyboard, serial,
a writable FORGE drive, and BLE-to-keyboard control.

## Development

Open this directory in VS Code with the PlatformIO extension.
Run commands below from this directory.

Build firmware:
    ~/.platformio/penv/bin/pio run

Create the drive image:
    sudo apt install -y dosfstools mtools
    python3 build-drive.py

The builder copies scripts/inspect-hardware from the repository and
forge-drive/RUN.SH into build/forge.img.

Tested versions: Espressif32 7.1.3, Arduino ESP32 2.0.17,
NimBLE-Arduino 2.5.1, M5Unified 0.2.22.
Dependencies currently remain unpinned.

## Flashing

Close serial monitors. Hold the reset button for about two seconds
until the internal green LED lights, then release.

Upload firmware:
    ~/.platformio/penv/bin/pio run --target upload

Re-enter download mode before initializing storage:
    ~/.platformio/penv/bin/python ~/.platformio/packages/tool-esptoolpy/esptool.py --chip esp32s3 --port /dev/ttyACM0 --baud 460800 write_flash 0x670000 build/forge.img

Adjust the serial port if necessary. Unplug and reconnect normally.

Initializing storage replaces all files and reports on FORGE.
Ordinary firmware uploads preserve storage with the partition layout
unchanged. Do not use erase_flash or uploadfs for firmware updates.

## Inspection

1. Mount FORGE using the target Linux machine's file manager.
2. Focus an empty terminal prompt.
3. Press the top programmable button once and let typing finish.
4. Enter the target whole disk, for example /dev/nvme0n1.
5. Enter the sudo password if prompted.
6. Retrieve hardware-report-*.txt from FORGE.
7. Safely eject before unplugging.

Do not select the small FORGE drive as the target disk.
Ubuntu live sessions normally permit passwordless sudo.
Missing optional utilities can reduce report detail.

The inspector saves reports beside itself on the USB drive.
To update it without replacing reports, copy the repository's
scripts/inspect-hardware onto mounted FORGE and safely eject.

## Implementation notes

The existing default_8MB.csv partition labeled spiffs holds raw FAT:
offset 0x670000, size 0x180000 (1.5 MiB).
Do not mount this partition as SPIFFS in firmware.
Writes are synchronous and do not use wear leveling; this storage
is intended for occasional inspection reports.

BLE name: Graystone-HID
Service: 6E400001-B5A3-F393-E0A9-E50E24DCCA9E
RX: 6E400002-B5A3-F393-E0A9-E50E24DCCA9E

BLE writes become keyboard input in the focused host application.
The current characteristic does not require BLE authentication.
Typing uses a 20 ms character delay and the default US keyboard layout.
Concurrent typing requests are dropped while typing is in progress.

## Hardware validation

Tested on Artemis: firmware build, FORGE mounting, persistence after
reconnection, button-triggered inspection, and report creation.
