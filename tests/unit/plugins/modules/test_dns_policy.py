# -*- coding: utf-8 -*-
# Copyright: (c) 2026, NightLabs
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/dns_policy.py.

The UnifiClient lookups are patched to return canned records, and request() is a mock, so
each test checks which call the module would make and what it reports, without a console.
exit_json and fail_json are patched to raise, which stops main() where the real module exits.
"""

from __future__ import annotations

import copy
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ansible.module_utils import basic
from ansible.module_utils.testing import patch_module_args

from ansible_collections.nightlabs.unifi.plugins.module_utils.api import UnifiAPIError, UnifiClient
from ansible_collections.nightlabs.unifi.plugins.modules import dns_policy

SITE_UUID = "88f7af54-98f8-306a-a1c7-c9349722b1f6"
POLICY_UUID = "6c1f0b7e-3a2d-4e5f-9b8a-1d2c3e4f5a6b"
POLICY_PATH = "/sites/%s/dns/policies/%s" % (SITE_UUID, POLICY_UUID)

EXISTING_A = {
    "type": "A_RECORD",
    "id": POLICY_UUID,
    "enabled": True,
    "metadata": {"origin": "USER_DEFINED"},
    "domain": "host1.example.lan",
    "ipv4Address": "192.0.2.10",
    "ttlSeconds": 3600,
}

CONNECTION = dict(host="192.0.2.1", api_key="test-api-key", site="default")


class ExitJson(Exception):
    pass


class FailJson(Exception):
    pass


def exit_json(self, **kwargs):
    raise ExitJson(kwargs)


def fail_json(self, **kwargs):
    raise FailJson(kwargs)


@pytest.fixture(autouse=True)
def module_exits():
    with patch.multiple(basic.AnsibleModule, exit_json=exit_json, fail_json=fail_json):
        yield


@pytest.fixture
def api():
    """Patch the client; set api.policy to the record resolve_policy should find."""
    with patch.object(UnifiClient, "resolve_site", return_value=SITE_UUID), \
            patch.object(UnifiClient, "resolve_policy") as resolve_policy, \
            patch.object(UnifiClient, "request") as request:
        fake = SimpleNamespace(policy=None, request=request, resolve_policy=resolve_policy)
        # The module pops keys from the record it gets, so hand it a fresh copy every time.
        resolve_policy.side_effect = lambda site_id, domain: copy.deepcopy(fake.policy)
        yield fake


def run(args, check_mode=False):
    """Run the module with CONNECTION plus args; return (exception type, result dict)."""
    module_args = dict(CONNECTION, **args)
    if check_mode:
        module_args["_ansible_check_mode"] = True
    with patch_module_args(module_args):
        with pytest.raises((ExitJson, FailJson)) as excinfo:
            dns_policy.main()
    return excinfo.type, excinfo.value.args[0]


A_ARGS = dict(domain="host1.example.lan", record_type="A_RECORD", ipv4_address="192.0.2.10")


# --- create ------------------------------------------------------------------

def test_create_posts_with_defaults(api):
    api.request.return_value = {"id": POLICY_UUID}
    kind, result = run(dict(A_ARGS, domain="Host1.Example.LAN"))

    assert kind is ExitJson
    assert result["changed"] is True
    assert result["policy"] == {"id": POLICY_UUID}
    api.request.assert_called_once_with(
        "/sites/%s/dns/policies" % SITE_UUID,
        method="POST",
        body={
            "type": "A_RECORD",
            "domain": "host1.example.lan",
            "ipv4Address": "192.0.2.10",
            "enabled": True,
            "ttlSeconds": 14400,
        },
    )


def test_create_keeps_given_enabled_and_ttl(api):
    run(dict(A_ARGS, enabled=False, ttl_seconds=300))
    body = api.request.call_args.kwargs["body"]
    assert body["enabled"] is False
    assert body["ttlSeconds"] == 300


def test_create_cname_sends_only_target_domain(api):
    run(dict(domain="app.example.lan", record_type="CNAME_RECORD", target_domain="host1.example.lan"))
    body = api.request.call_args.kwargs["body"]
    assert body["targetDomain"] == "host1.example.lan"
    assert "ipv4Address" not in body and "ipv6Address" not in body


def test_create_in_check_mode_makes_no_request(api):
    kind, result = run(A_ARGS, check_mode=True)
    assert kind is ExitJson
    assert result["changed"] is True
    assert "policy" not in result
    api.request.assert_not_called()


# --- update ------------------------------------------------------------------

def test_update_merges_set_fields_onto_existing(api):
    api.policy = EXISTING_A
    api.request.return_value = dict(EXISTING_A, ipv4Address="192.0.2.20")
    kind, result = run(dict(A_ARGS, ipv4_address="192.0.2.20"))

    assert kind is ExitJson
    assert result["changed"] is True
    assert result["policy"]["ipv4Address"] == "192.0.2.20"
    api.request.assert_called_once()
    assert api.request.call_args.args == (POLICY_PATH,)
    assert api.request.call_args.kwargs["method"] == "PUT"
    # Unset options keep the console's values; id and metadata are not sent back.
    assert api.request.call_args.kwargs["body"] == {
        "type": "A_RECORD",
        "enabled": True,
        "domain": "host1.example.lan",
        "ipv4Address": "192.0.2.20",
        "ttlSeconds": 3600,
    }


def test_unchanged_record_makes_no_request_and_returns_it_whole(api):
    api.policy = EXISTING_A
    kind, result = run(A_ARGS)

    assert kind is ExitJson
    assert result["changed"] is False
    assert result["policy"] == EXISTING_A
    api.request.assert_not_called()


def test_domain_case_does_not_count_as_a_change(api):
    api.policy = EXISTING_A
    kind, result = run(dict(A_ARGS, domain="HOST1.example.lan"))
    assert result["changed"] is False
    api.request.assert_not_called()


def test_update_in_check_mode_makes_no_request(api):
    api.policy = EXISTING_A
    kind, result = run(dict(A_ARGS, ttl_seconds=60), check_mode=True)
    assert kind is ExitJson
    assert result["changed"] is True
    api.request.assert_not_called()


def test_type_change_fails_without_a_request(api):
    api.policy = EXISTING_A
    kind, result = run(dict(domain="host1.example.lan", record_type="AAAA_RECORD", ipv6_address="2001:db8::10"))
    assert kind is FailJson
    assert "Cannot change type" in result["msg"]
    api.request.assert_not_called()


# --- delete ------------------------------------------------------------------

def test_delete_existing(api):
    api.policy = EXISTING_A
    kind, result = run(dict(domain="host1.example.lan", state="absent"))
    assert kind is ExitJson
    assert result["changed"] is True
    api.request.assert_called_once_with(POLICY_PATH, method="DELETE")


def test_delete_in_check_mode_makes_no_request(api):
    api.policy = EXISTING_A
    kind, result = run(dict(domain="host1.example.lan", state="absent"), check_mode=True)
    assert result["changed"] is True
    api.request.assert_not_called()


def test_delete_missing_is_unchanged(api):
    kind, result = run(dict(domain="host1.example.lan", state="absent"))
    assert kind is ExitJson
    assert result["changed"] is False
    api.request.assert_not_called()


# --- argument validation and errors -------------------------------------------

def test_present_requires_record_type(api):
    kind, result = run(dict(domain="host1.example.lan"))
    assert kind is FailJson
    assert "record_type" in result["msg"]
    api.resolve_policy.assert_not_called()


@pytest.mark.parametrize("args, missing", [
    (dict(record_type="A_RECORD"), "ipv4_address"),
    (dict(record_type="AAAA_RECORD"), "ipv6_address"),
    (dict(record_type="CNAME_RECORD"), "target_domain"),
])
def test_each_type_requires_its_value(api, args, missing):
    kind, result = run(dict(args, domain="host1.example.lan"))
    assert kind is FailJson
    assert missing in result["msg"]


def test_value_for_another_type_is_refused(api):
    kind, result = run(dict(A_ARGS, target_domain="other.example.lan"))
    assert kind is FailJson
    assert "target_domain cannot be set when record_type is A_RECORD" in result["msg"]
    api.resolve_policy.assert_not_called()


def test_api_error_becomes_fail_json(api):
    api.resolve_policy.side_effect = UnifiAPIError("boom")
    kind, result = run(A_ARGS)
    assert kind is FailJson
    assert result["msg"] == "boom"
