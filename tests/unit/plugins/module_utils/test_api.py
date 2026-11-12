# -*- coding: utf-8 -*-
# Copyright: (c) 2026, NightLabs
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/api.py.

No console is involved: fetch_url is replaced with a fake that returns canned
(response, info) pairs, the same shape the real one returns.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

import pytest

from ansible_collections.nightlabs.unifi.plugins.module_utils import api
from ansible_collections.nightlabs.unifi.plugins.module_utils.api import (
    PAGE_LIMIT,
    UnifiAPIError,
    UnifiClient,
    UnifiNotFoundError,
)

HOST = "192.0.2.1"
API_KEY = "test-api-key"
BASE = "https://%s:443%s" % (HOST, api.API_BASE)
SITE_UUID = "88f7af54-98f8-306a-a1c7-c9349722b1f6"
SITES = [
    {"id": SITE_UUID, "internalReference": "default", "name": "Default"},
    {"id": "11111111-2222-3333-4444-555555555555", "internalReference": "lab", "name": "Bob's Lab"},
]

POLICY_A_UUID = "6c1f0b7e-3a2d-4e5f-9b8a-1d2c3e4f5a6b"
POLICY_CNAME_UUID = "9e8d7c6b-5a4f-4e3d-8c2b-1a0f9e8d7c6b"
POLICIES = [
    {
        "type": "A_RECORD",
        "id": POLICY_A_UUID,
        "enabled": True,
        "metadata": {"origin": "USER_DEFINED"},
        "domain": "host1.example.lan",
        "ipv4Address": "192.0.2.10",
        "ttlSeconds": 0,
    },
    {
        "type": "CNAME_RECORD",
        "id": POLICY_CNAME_UUID,
        "enabled": True,
        "metadata": {"origin": "USER_DEFINED"},
        "domain": "app.example.lan",
        "targetDomain": "host1.example.lan",
        "ttlSeconds": 0,
    },
]


# --- helpers -----------------------------------------------------------------

def ok(payload, status=200):
    """A successful fetch_url result: a response object whose read() returns the body."""
    resp = MagicMock()
    resp.read.return_value = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return resp, {"status": status}


def err(status, body=b"", msg="HTTP Error"):
    """A failed fetch_url result: no response object, the body is in info instead."""
    return None, {"status": status, "body": body, "msg": msg}


def query_of(call):
    """The query string of one fetch_url call, as {name: value}."""
    url = call.args[1]
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}


def paged_server(items, max_limit=25):
    """A fake list endpoint that honours offset/limit, clamping limit like the console does."""
    def respond(module, url, **kwargs):
        q = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        offset = int(q.get("offset", 0))
        limit = min(int(q.get("limit", max_limit)), max_limit)
        page = items[offset:offset + limit]
        return ok({"offset": offset, "limit": limit, "count": len(page), "totalCount": len(items), "data": page})
    return respond


# --- fixtures ----------------------------------------------------------------

@pytest.fixture
def client():
    module = SimpleNamespace(params=dict(host=HOST, port=443, api_key=API_KEY, validate_certs=False, timeout=30))
    return UnifiClient(module)


@pytest.fixture
def fetch():
    """Patch fetch_url where api.py looks it up; set .return_value or .side_effect per test."""
    with patch.object(api, "fetch_url") as fake:
        yield fake


# --- request -----------------------------------------------------------------

def test_request_builds_url_headers_and_method(client, fetch):
    fetch.return_value = ok({})
    client.request("/sites")

    call = fetch.call_args
    assert call.args[1] == BASE + "/sites"
    assert call.kwargs["method"] == "GET"
    assert call.kwargs["timeout"] == 30
    assert call.kwargs["headers"]["X-API-KEY"] == API_KEY
    assert call.kwargs["data"] is None
    assert "Content-Type" not in call.kwargs["headers"]


def test_request_encodes_query(client, fetch):
    fetch.return_value = ok({})
    client.request("/sites", query={"offset": 0, "filter": "name.eq('x')"})
    assert query_of(fetch.call_args) == {"offset": "0", "filter": "name.eq('x')"}


def test_request_sends_json_body(client, fetch):
    fetch.return_value = ok({})
    client.request("/sites", method="POST", body={"name": "lab"})

    call = fetch.call_args
    assert json.loads(call.kwargs["data"]) == {"name": "lab"}
    assert call.kwargs["headers"]["Content-Type"] == "application/json"
    assert call.kwargs["method"] == "POST"


def test_request_does_not_mutate_shared_headers(client, fetch):
    fetch.return_value = ok({})
    client.request("/sites", method="POST", body={})
    assert "Content-Type" not in client.headers


def test_request_returns_parsed_json(client, fetch):
    fetch.return_value = ok({"id": SITE_UUID})
    assert client.request("/sites/x") == {"id": SITE_UUID}


def test_request_returns_none_for_empty_body(client, fetch):
    fetch.return_value = ok(b"", status=204)
    assert client.request("/sites/x") is None


def test_request_connection_failure(client, fetch):
    fetch.return_value = err(-1, msg="Connection refused")
    with pytest.raises(UnifiAPIError, match="Could not connect to .*Connection refused"):
        client.request("/sites")


def test_request_401_points_at_api_key(client, fetch):
    fetch.return_value = err(401, b'{"message": "unauthorized"}')
    with pytest.raises(UnifiAPIError, match=r"Authentication failed \(HTTP 401\)"):
        client.request("/sites")


def test_request_404_with_empty_body(client, fetch):
    # The console sends no body on an unknown UUID.
    fetch.return_value = err(404, b"")
    # The _info modules catch UnifiNotFoundError by name, so check the exact class.
    with pytest.raises(UnifiNotFoundError, match=r"Resource not found \(HTTP 404\)"):
        client.request("/sites/x")


def test_request_error_includes_body(client, fetch):
    fetch.return_value = err(500, b'{"message": "boom"}')
    with pytest.raises(UnifiAPIError, match="HTTP 500 .*boom"):
        client.request("/sites")


def test_request_non_json_body(client, fetch):
    fetch.return_value = ok(b"<html>proxy error</html>")
    with pytest.raises(UnifiAPIError, match="Non-JSON response .*proxy error"):
        client.request("/sites")


@pytest.mark.parametrize("result", [err(-1), err(401), err(404), err(500, b"x"), ok(b"not json")])
def test_errors_never_contain_api_key(client, fetch, result):
    fetch.return_value = result
    with pytest.raises(UnifiAPIError) as excinfo:
        client.request("/sites")
    assert API_KEY not in str(excinfo.value)


# --- get_all -----------------------------------------------------------------

def test_get_all_single_page(client, fetch):
    items = [{"id": str(i)} for i in range(9)]
    fetch.side_effect = paged_server(items)
    assert client.get_all("/sites") == items
    assert fetch.call_count == 1


def test_get_all_follows_clamped_pages(client, fetch):
    # The console clamps limit to 25 whatever is asked for; every item must still come back.
    items = [{"id": str(i)} for i in range(60)]
    fetch.side_effect = paged_server(items, max_limit=25)

    assert client.get_all("/sites") == items
    assert [query_of(c)["offset"] for c in fetch.call_args_list] == ["0", "25", "50"]
    assert all(query_of(c)["limit"] == str(PAGE_LIMIT) for c in fetch.call_args_list)


def test_get_all_empty_collection(client, fetch):
    fetch.side_effect = paged_server([])
    assert client.get_all("/sites") == []
    assert fetch.call_count == 1


def test_get_all_stops_on_empty_page_despite_totalcount(client, fetch):
    # A totalCount larger than what the server actually returns must not loop forever.
    fetch.side_effect = [
        ok({"data": [{"id": "a"}], "totalCount": 5}),
        ok({"data": [], "totalCount": 5}),
    ]
    assert client.get_all("/sites") == [{"id": "a"}]
    assert fetch.call_count == 2


def test_get_all_without_totalcount_pages_until_empty(client, fetch):
    # A missing totalCount must not cut the listing off after the first page.
    fetch.side_effect = [
        ok({"data": [{"id": "a"}]}),
        ok({"data": [{"id": "b"}]}),
        ok({"data": []}),
    ]
    assert client.get_all("/sites") == [{"id": "a"}, {"id": "b"}]
    assert fetch.call_count == 3


def test_get_all_keeps_caller_query_on_every_page(client, fetch):
    items = [{"id": str(i)} for i in range(30)]
    fetch.side_effect = paged_server(items)
    caller_query = {"filter": "state.eq('ONLINE')"}

    client.get_all("/devices", query=caller_query)

    assert all(query_of(c)["filter"] == "state.eq('ONLINE')" for c in fetch.call_args_list)
    assert caller_query == {"filter": "state.eq('ONLINE')"}


# --- resolve_site ------------------------------------------------------------

def test_resolve_site_by_uuid(client, fetch):
    fetch.side_effect = paged_server(SITES)
    assert client.resolve_site(SITE_UUID) == SITE_UUID


def test_resolve_site_by_reference(client, fetch):
    fetch.side_effect = paged_server(SITES)
    assert client.resolve_site("default") == SITE_UUID


def test_resolve_site_by_name(client, fetch):
    fetch.side_effect = paged_server(SITES)
    assert client.resolve_site("Default") == SITE_UUID


def test_resolve_site_with_quotes(client, fetch):
    fetch.side_effect = paged_server(SITES)
    assert client.resolve_site("Bob's Lab") == SITES[1]["id"]


def test_resolve_site_uppercase_uuid(client, fetch):
    fetch.side_effect = paged_server(SITES)
    assert client.resolve_site(SITE_UUID.upper()) == SITE_UUID


def test_resolve_site_unknown_uuid(client, fetch):
    fetch.side_effect = paged_server(SITES)
    with pytest.raises(UnifiAPIError, match="Could not resolve site"):
        client.resolve_site("00000000-0000-0000-0000-000000000000")


def test_resolve_site_no_match(client, fetch):
    fetch.side_effect = paged_server(SITES)

    with pytest.raises(UnifiAPIError, match="Could not resolve site"):
        client.resolve_site("nope")


def test_resolve_site_ambiguous(client, fetch):
    # One site's internalReference equals another's name.
    fetch.return_value = ok({"data": [
        {"id": "a", "internalReference": "lab", "name": "Home"},
        {"id": "b", "internalReference": "office", "name": "lab"},
    ], "totalCount": 2})
    with pytest.raises(UnifiAPIError, match="matches more than one site"):
        client.resolve_site("lab")


@pytest.mark.parametrize("site", ["", None])
def test_resolve_site_empty(client, fetch, site):
    with pytest.raises(UnifiAPIError, match="site is required"):
        client.resolve_site(site)
    fetch.assert_not_called()


def test_get_site_returns_whole_record(client, fetch):
    fetch.side_effect = paged_server(SITES)
    assert client.get_site("lab") == SITES[1]
    assert fetch.call_count == 1


# --- resolve_policy ----------------------------------------------------------

def test_resolve_policy_returns_whole_record(client, fetch):
    fetch.side_effect = paged_server(POLICIES)
    assert client.resolve_policy(SITE_UUID, "app.example.lan") == POLICIES[1]


def test_resolve_policy_requests_the_site_path(client, fetch):
    fetch.side_effect = paged_server(POLICIES)
    client.resolve_policy(SITE_UUID, "app.example.lan")
    assert fetch.call_args.args[1].startswith(BASE + "/sites/%s/dns/policies?" % SITE_UUID)


def test_resolve_policy_ignores_case(client, fetch):
    fetch.side_effect = paged_server(POLICIES)
    assert client.resolve_policy(SITE_UUID, "Host1.Example.LAN")["id"] == POLICY_A_UUID


def test_resolve_policy_no_match_returns_none(client, fetch):
    fetch.side_effect = paged_server(POLICIES)
    assert client.resolve_policy(SITE_UUID, "missing.example.lan") is None


def test_resolve_policy_empty_site_returns_none(client, fetch):
    fetch.side_effect = paged_server([])
    assert client.resolve_policy(SITE_UUID, "host1.example.lan") is None


def test_resolve_policy_duplicate(client, fetch):
    fetch.side_effect = paged_server(POLICIES + [dict(POLICIES[0], id="dup")])
    with pytest.raises(UnifiAPIError, match="more than one DNS policy"):
        client.resolve_policy(SITE_UUID, "host1.example.lan")


@pytest.mark.parametrize("site_id, domain", [("", "host1.example.lan"), (SITE_UUID, ""), (None, None)])
def test_resolve_policy_missing_args(client, fetch, site_id, domain):
    with pytest.raises(UnifiAPIError, match="specified"):
        client.resolve_policy(site_id, domain)
    fetch.assert_not_called()


# --- _to_text ----------------------------------------------------------------

def test_to_text_replaces_invalid_utf8():
    assert api._to_text(b"ok \xff") == "ok �"


def test_to_text_passes_str_through():
    assert api._to_text("already text") == "already text"
