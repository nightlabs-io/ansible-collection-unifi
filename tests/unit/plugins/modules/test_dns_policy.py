# -*- coding: utf-8 -*-
# Copyright: (c) 2026, John Cuckovich
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

from ansible_collections.nightlabs.unifi.plugins.module_utils.api import (
    UnifiAPIError,
    UnifiClient,
    unifi_argument_spec,
    unifi_site_argument_spec,
)
from ansible_collections.nightlabs.unifi.plugins.modules import dns_policy

SITE_UUID = "88f7af54-98f8-306a-a1c7-c9349722b1f6"
POLICY_UUID = "6c1f0b7e-3a2d-4e5f-9b8a-1d2c3e4f5a6b"
POLICIES_PATH = "/sites/%s/dns/policies" % SITE_UUID
POLICY_PATH = "%s/%s" % (POLICIES_PATH, POLICY_UUID)

EXISTING_A = {
    "type": "A_RECORD",
    "id": POLICY_UUID,
    "enabled": True,
    "metadata": {"origin": "USER_DEFINED"},
    "domain": "host1.example.lan",
    "ipv4Address": "192.0.2.10",
    "ttlSeconds": 3600,
}

EXISTING_MX = {
    "type": "MX_RECORD",
    "id": POLICY_UUID,
    "enabled": True,
    "metadata": {"origin": "USER_DEFINED"},
    "domain": "example.lan",
    "mailServerDomain": "mail1.example.lan",
    "priority": 10,
}

CONNECTION = dict(host="192.0.2.1", api_key="test-api-key", site="default")

A_ARGS = dict(domain="host1.example.lan", record_type="A_RECORD", ipv4_address="192.0.2.10")
MX_ARGS = dict(domain="example.lan", record_type="MX_RECORD", mail_server_domain="mail1.example.lan", priority=10)
SRV_ARGS = dict(domain="example.lan", record_type="SRV_RECORD", service="_ldap", protocol="_tcp",
                server_domain="ldap.example.lan", service_port=389, priority=10, weight=5)
TXT_ARGS = dict(domain="example.lan", record_type="TXT_RECORD", text="v=spf1 mx -all")
FORWARD_ARGS = dict(domain="corp.example", record_type="FORWARD_DOMAIN", ip_address="2001:db8::53")


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
        resolve_policy.side_effect = lambda *args, **kwargs: copy.deepcopy(fake.policy)
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


def posted(api):
    """The body of the single POST the module made."""
    api.request.assert_called_once()
    assert api.request.call_args.args == (POLICIES_PATH,)
    assert api.request.call_args.kwargs["method"] == "POST"
    return api.request.call_args.kwargs["body"]


# --- lookup ------------------------------------------------------------------

@pytest.mark.parametrize("args, identity", [
    (A_ARGS, {}),
    (MX_ARGS, {"mailServerDomain": "mail1.example.lan"}),
    (TXT_ARGS, {"text": "v=spf1 mx -all"}),
    (SRV_ARGS, {"service": "_ldap", "protocol": "_tcp", "serverDomain": "ldap.example.lan"}),
    (FORWARD_ARGS, {"ipAddress": "2001:db8::53"}),
])
def test_lookup_uses_type_domain_and_identity(api, args, identity):
    run(args)
    api.resolve_policy.assert_called_once_with(
        SITE_UUID, args["record_type"], args["domain"], identity, case_sensitive=("text",))


def test_lookup_lowercases_domain(api):
    run(dict(A_ARGS, domain="Host1.Example.LAN"))
    assert api.resolve_policy.call_args.args[2] == "host1.example.lan"


# --- create ------------------------------------------------------------------

def test_create_a_with_defaults(api):
    api.request.return_value = {"id": POLICY_UUID}
    kind, result = run(dict(A_ARGS, domain="Host1.Example.LAN"))

    assert kind is ExitJson
    assert result["changed"] is True
    assert result["policy"] == {"id": POLICY_UUID}
    assert posted(api) == {
        "type": "A_RECORD",
        "domain": "host1.example.lan",
        "ipv4Address": "192.0.2.10",
        "enabled": True,
        "ttlSeconds": 14400,
    }


def test_create_keeps_given_enabled_and_ttl(api):
    run(dict(A_ARGS, enabled=False, ttl_seconds=300))
    body = posted(api)
    assert body["enabled"] is False
    assert body["ttlSeconds"] == 300


def test_create_cname_sends_only_its_fields(api):
    run(dict(domain="app.example.lan", record_type="CNAME_RECORD", target_domain="host1.example.lan"))
    assert posted(api) == {
        "type": "CNAME_RECORD",
        "domain": "app.example.lan",
        "targetDomain": "host1.example.lan",
        "enabled": True,
        "ttlSeconds": 14400,
    }


def test_create_mx_has_no_ttl(api):
    run(MX_ARGS)
    assert posted(api) == {
        "type": "MX_RECORD",
        "domain": "example.lan",
        "mailServerDomain": "mail1.example.lan",
        "priority": 10,
        "enabled": True,
    }


def test_create_srv(api):
    run(SRV_ARGS)
    assert posted(api) == {
        "type": "SRV_RECORD",
        "domain": "example.lan",
        "service": "_ldap",
        "protocol": "_tcp",
        "serverDomain": "ldap.example.lan",
        "port": 389,
        "priority": 10,
        "weight": 5,
        "enabled": True,
    }


def test_create_txt(api):
    run(TXT_ARGS)
    assert posted(api) == {"type": "TXT_RECORD", "domain": "example.lan", "text": "v=spf1 mx -all", "enabled": True}


def test_create_forward(api):
    run(FORWARD_ARGS)
    assert posted(api) == {"type": "FORWARD_DOMAIN", "domain": "corp.example", "ipAddress": "2001:db8::53", "enabled": True}


def test_create_keeps_zero_values(api):
    # The console stores 0 for priority and weight; a truthiness filter would drop them.
    run(dict(SRV_ARGS, priority=0, weight=0))
    body = posted(api)
    assert body["priority"] == 0
    assert body["weight"] == 0


@pytest.mark.parametrize("args, missing", [
    (dict(domain="host1.example.lan", record_type="A_RECORD"), "ipv4_address"),
    (dict(domain="host1.example.lan", record_type="AAAA_RECORD"), "ipv6_address"),
    (dict(domain="app.example.lan", record_type="CNAME_RECORD"), "target_domain"),
    (dict(MX_ARGS, priority=None), "priority"),
    (dict(SRV_ARGS, service_port=None, weight=None), "service_port, weight"),
])
@pytest.mark.parametrize("check_mode", [False, True])
def test_create_requires_attributes_without_defaults(api, args, missing, check_mode):
    args = {k: v for k, v in args.items() if v is not None}
    kind, result = run(args, check_mode=check_mode)
    assert kind is FailJson
    assert result["msg"].endswith("requires %s." % missing)
    api.request.assert_not_called()


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


def test_update_needs_no_value(api):
    # Only creating requires the address; an update may change just one attribute.
    api.policy = EXISTING_A
    run(dict(domain="host1.example.lan", record_type="A_RECORD", enabled=False))
    assert api.request.call_args.kwargs["body"]["enabled"] is False
    assert api.request.call_args.kwargs["body"]["ipv4Address"] == "192.0.2.10"


def test_update_mx_priority(api):
    api.policy = EXISTING_MX
    run(dict(MX_ARGS, priority=0))
    assert api.request.call_args.kwargs["method"] == "PUT"
    assert api.request.call_args.kwargs["body"]["priority"] == 0


def test_unchanged_record_makes_no_request_and_returns_it_whole(api):
    api.policy = EXISTING_A
    kind, result = run(A_ARGS)

    assert kind is ExitJson
    assert result["changed"] is False
    assert result["policy"] == EXISTING_A
    api.request.assert_not_called()


def test_unchanged_mx_without_ttl(api):
    api.policy = EXISTING_MX
    kind, result = run(MX_ARGS)
    assert result["changed"] is False
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


def test_another_type_on_the_domain_is_a_new_record(api):
    # resolve_policy finds nothing of the asked type, so an A record on the same domain
    # is not touched and the AAAA record is created next to it.
    run(dict(domain="host1.example.lan", record_type="AAAA_RECORD", ipv6_address="2001:db8::10"))
    assert posted(api)["type"] == "AAAA_RECORD"


# --- delete ------------------------------------------------------------------

def test_delete_existing(api):
    api.policy = EXISTING_MX
    kind, result = run(dict(MX_ARGS, state="absent"))
    assert kind is ExitJson
    assert result["changed"] is True
    api.request.assert_called_once_with(POLICY_PATH, method="DELETE")


def test_delete_in_check_mode_makes_no_request(api):
    api.policy = EXISTING_A
    kind, result = run(dict(domain="host1.example.lan", record_type="A_RECORD", state="absent"), check_mode=True)
    assert result["changed"] is True
    api.request.assert_not_called()


def test_delete_missing_is_unchanged(api):
    kind, result = run(dict(domain="host1.example.lan", record_type="A_RECORD", state="absent"))
    assert kind is ExitJson
    assert result["changed"] is False
    api.request.assert_not_called()


# --- argument validation and errors -------------------------------------------

@pytest.mark.parametrize("state", ["present", "absent"])
def test_record_type_is_required(api, state):
    kind, result = run(dict(domain="host1.example.lan", state=state))
    assert kind is FailJson
    assert "record_type" in result["msg"]
    api.resolve_policy.assert_not_called()


@pytest.mark.parametrize("args, missing", [
    (dict(record_type="MX_RECORD"), "mail_server_domain"),
    (dict(record_type="TXT_RECORD"), "text"),
    (dict(record_type="SRV_RECORD", service="_ldap"), "protocol"),
    (dict(record_type="FORWARD_DOMAIN"), "ip_address"),
])
@pytest.mark.parametrize("state", ["present", "absent"])
def test_identity_is_required_in_both_states(api, args, missing, state):
    kind, result = run(dict(args, domain="example.lan", state=state))
    assert kind is FailJson
    assert missing in result["msg"]
    api.resolve_policy.assert_not_called()


@pytest.mark.parametrize("args, stray", [
    (dict(A_ARGS, target_domain="other.example.lan"), "target_domain"),
    (dict(MX_ARGS, ttl_seconds=300), "ttl_seconds"),
    (dict(TXT_ARGS, priority=10), "priority"),
    (dict(FORWARD_ARGS, ipv4_address="192.0.2.53"), "ipv4_address"),
])
def test_option_of_another_type_is_refused(api, args, stray):
    kind, result = run(args)
    assert kind is FailJson
    assert result["msg"] == "%s cannot be set when record_type is %s" % (stray, args["record_type"])
    api.resolve_policy.assert_not_called()


def test_api_error_becomes_fail_json(api):
    api.resolve_policy.side_effect = UnifiAPIError("boom")
    kind, result = run(A_ARGS)
    assert kind is FailJson
    assert result["msg"] == "boom"


def test_record_options_do_not_shadow_shared_options():
    # A record option named like a connection option (an SRV `port`) would replace it.
    shared = set(unifi_argument_spec()) | set(unifi_site_argument_spec())
    assert not shared & set(dns_policy.FIELDS)
