#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, John Cuckovich
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
module: device_info
short_description: List devices on a UniFi Network site
version_added: 0.1.0
description:
  - Returns the adopted devices on one site of a UniFi Network application using the official Integration API.
author:
  - John Cuckovich (@jpcuckovi)
options:
  device:
    description:
      - Only return this device. Without it, every device on the site is returned.
      - UUID of the device, as returned in RV(devices[].id).
      - The task fails if the site has no device with this UUID.
    type: str
extends_documentation_fragment:
  - nightlabs.unifi.api
  - nightlabs.unifi.api.site
attributes:
  check_mode:
    description: Can run in check_mode and return changed status prediction without modifying target.
    support: full
"""

EXAMPLES = r"""
- name: List every device on the default site
  nightlabs.unifi.device_info:
    host: 192.0.2.1
    api_key: "{{ unifi_api_key }}"
    validate_certs: false
    site: default
  register: unifi_devices

- name: Get one device by UUID
  nightlabs.unifi.device_info:
    host: 192.0.2.1
    api_key: "{{ unifi_api_key }}"
    validate_certs: false
    site: default
    device: "{{ unifi_devices.devices[0].id }}"
  register: one_device

- name: Show its name
  ansible.builtin.debug:
    var: one_device.devices[0].name
"""

RETURN = r"""
devices:
  description:
    - Devices returned by the console. Always a list, with one element when O(device) is set.
    - A single-device lookup (O(device) set) returns more fields than the listing.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: Device UUID, used by other Integration API endpoints and by O(device).
      type: str
      sample: 3f1c2a9e-5b7d-4e8f-9a1b-2c3d4e5f6a7b
    name:
      description: Display name of the device.
      type: str
      sample: Office AP
    model:
      description: Hardware model.
      type: str
      sample: UCG Max
    macAddress:
      description: MAC address of the device, colon-separated lowercase hex.
      type: str
    ipAddress:
      description: Management IP address of the device.
      type: str
      sample: 192.0.2.10
    state:
      description: Connection state reported by the console.
      type: str
      sample: ONLINE
    supported:
      description: Whether the Integration API supports this device model.
      type: bool
      returned: when O(device) is set
      sample: true
    firmwareVersion:
      description: Firmware version running on the device.
      type: str
      returned: when O(device) is set
      sample: 5.1.35
    firmwareUpdatable:
      description: Whether a newer firmware version is available.
      type: bool
      returned: when O(device) is set
      sample: false
    adoptedAt:
      description: When the device was adopted, as an ISO 8601 UTC timestamp.
      type: str
      returned: when O(device) is set
      sample: "2026-01-01T12:00:00Z"
    provisionedAt:
      description: When configuration was last provisioned to the device, as an ISO 8601 UTC timestamp.
      type: str
      returned: when O(device) is set
      sample: "2026-01-01T12:00:00Z"
    configurationId:
      description: Identifier of the configuration last provisioned to the device.
      type: str
      returned: when O(device) is set
    uplink:
      description: The device this one connects upstream through. Absent on the gateway, which has no upstream UniFi device.
      type: dict
      returned: when O(device) is set and the device has an uplink
      contains:
        deviceId:
          description: UUID of the upstream device, usable as O(device).
          type: str
          sample: 3f1c2a9e-5b7d-4e8f-9a1b-2c3d4e5f6a7b
    features:
      description:
        - Feature-specific details, keyed by feature. Which keys appear depends on the device model,
          for example C(switching) on devices with switch ports and C(accessPoint) on access points.
      type: dict
      returned: when O(device) is set
      sample:
        switching:
          lags: []
        accessPoint: {}
    interfaces:
      description: Physical interfaces of the device. Which keys appear depends on the device model.
      type: dict
      returned: when O(device) is set
      contains:
        ports:
          description: One entry per physical port.
          type: list
          elements: dict
          returned: when the device has wired ports
          sample:
            - idx: 1
              connector: RJ45
              state: UP
              speedMbps: 2500
              maxSpeedMbps: 2500
        radios:
          description: One entry per Wi-Fi radio.
          type: list
          elements: dict
          returned: when the device has Wi-Fi radios
          sample:
            - wlanStandard: 802.11be
              frequencyGHz: 2.4
              channelWidthMHz: 20
              channel: 1
            - wlanStandard: 802.11be
              frequencyGHz: 5
              channelWidthMHz: 40
              channel: 36
"""

from ansible.module_utils.basic import AnsibleModule
from uuid import UUID

from ansible_collections.nightlabs.unifi.plugins.module_utils.api import (
    UnifiAPIError,
    UnifiClient,
    UnifiNotFoundError,
    unifi_argument_spec,
    unifi_site_argument_spec,
)


def main():
    argument_spec = unifi_argument_spec()
    argument_spec.update(unifi_site_argument_spec())
    # Optional: without it, list every device.
    argument_spec.update(device=dict(type="str"))
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    client = UnifiClient(module)
    device = module.params["device"]
    try:
        site_id = client.resolve_site(module.params["site"])
        path = "/sites/%s/devices" % site_id
        if device:
            device_id = str(UUID(device))
            devices = [client.request("%s/%s" % (path, device_id))]
        else:
            devices = client.get_all(path)
    except ValueError as e:
        module.fail_json(msg="Invalid UUID for device: %s" % e)
    except UnifiNotFoundError:
        module.fail_json(msg="Device '%s' not found on site '%s'" % (device, module.params["site"]))
    except UnifiAPIError as e:
        module.fail_json(msg=str(e))

    module.exit_json(changed=False, devices=devices)


if __name__ == "__main__":
    main()
