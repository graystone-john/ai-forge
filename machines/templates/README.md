# Machine registration template

machine.yaml.example follows the existing Daedalus machine structure.
It is not an active registration. Inventory discovery reads only
machines/*/machine.yaml.

## Process

1. Copy the template to machines/<new-name>/machine.yaml.example.
2. Collect hardware information and fill the relevant descriptions.
3. Choose the machine identity, purpose, architecture, and profiles.
4. Select the provisioning NIC and installation disk explicitly.
5. Verify the native disk serial and installer udev serial with the disk
   connected through its intended installation interface.
6. Check required fields, supported provisioning configuration, and
   inventory uniqueness before creating machine.yaml.
7. Generate and validate installation files, then deploy explicitly.
8. Provision only as a separate, explicitly requested rebuild.

Drafts contain named uppercase placeholders. Active provisioning records must not
contain unresolved placeholders or missing required values. A draft filename alone does not
prevent someone from manually copying incomplete data into machine.yaml.

The existing inventory validator checks duplicate names, IPs, and MACs.
The existing generated-installation validator compares configured disk
identifiers; it does not verify the identity of connected hardware.

Hardware sections can be completed incrementally in drafts. Do not
remove fields from active records without checking their consumers.
Profiles select supported capabilities; hardware descriptions alone do
not establish that a machine or architecture can be provisioned.

Existing registrations are not automatically migrated when this template
changes. Keep athena-01 and daedalus-01 unchanged until their own updates
are intentionally undertaken.
