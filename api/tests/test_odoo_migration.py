"""Unit tests for the three non-obvious behaviours the Odooly migration introduced.

All offline: no Odoo server, no network. They guard the parts where a silent
regression would corrupt data rather than raise.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from src.odoo import OdooConnector, field, normalize_conditions


# --------------------------------------------------------------------------
# normalize_conditions: Odooly serialises domains with json.dumps, which
# raises TypeError on a datetime. ErpPeek's XML-RPC marshalled them natively.
# --------------------------------------------------------------------------
class TestNormalizeConditions:
    def test_datetime_becomes_iso_string(self):
        dt = datetime(2026, 9, 21, 14, 30, 5)
        out = normalize_conditions([("create_date", ">=", dt)])
        assert out == [("create_date", ">=", "2026-09-21T14:30:05")]

    def test_result_is_json_serialisable(self):
        import json
        dom = [("create_date", ">=", datetime(2026, 1, 1)),
               ("create_date", "<", datetime(2026, 2, 1))]
        with pytest.raises(TypeError):
            json.dumps(dom)               # the pre-migration failure
        json.dumps(normalize_conditions(dom))   # must not raise

    def test_datetime_nested_in_a_list_value(self):
        dom = [("create_date", "in", [datetime(2026, 1, 1), datetime(2026, 1, 2)])]
        assert normalize_conditions(dom) == [
            ("create_date", "in", ["2026-01-01T00:00:00", "2026-01-02T00:00:00"])
        ]

    def test_other_values_pass_through_untouched(self):
        dom = [("barcode_base", "=", 42), ("state", "!=", "unsubscribed"),
               ("ok", "=", True), ("x", "=", None)]
        assert normalize_conditions(dom) == dom


# --------------------------------------------------------------------------
# field(): Odooly's Record.__getattr__ returns a bound METHOD for any unknown
# non-underscore attribute, so a renamed field yields a callable instead of
# raising, and flows on into the refund barcode as corrupt data.
# --------------------------------------------------------------------------
class _FakeModel:
    def __init__(self, name, keys):
        self._name, self._keys = name, keys


class _FakeRecord:
    """Mimics Odooly: known field -> value, anything else -> a callable."""
    def __init__(self, name, values):
        self._model = _FakeModel(name, list(values))
        self._values = values

    def __getattr__(self, attr):
        if attr in self._values:
            return self._values[attr]
        return lambda *a, **k: "I am a model method, not your data"


class TestFieldGuard:
    def test_returns_the_value_of_a_real_field(self):
        rec = _FakeRecord("res.partner", {"barcode_base": 1234})
        assert field(rec, "barcode_base") == 1234

    def test_raises_instead_of_returning_a_bound_method(self):
        rec = _FakeRecord("res.partner", {"name": "SEVRIN"})
        # Without the guard this silently yields a callable:
        assert callable(getattr(rec, "barcode_base"))
        with pytest.raises(AttributeError, match="has no field 'barcode_base'"):
            field(rec, "barcode_base")

    def test_error_names_the_model_and_the_field(self):
        rec = _FakeRecord("product.template", {"name": "x"})
        with pytest.raises(AttributeError) as exc:
            field(rec, "returnable")
        assert "product.template" in str(exc.value)
        assert "returnable" in str(exc.value)

    def test_a_falsy_real_field_is_returned_not_rejected(self):
        rec = _FakeRecord("product.template", {"returnable": False})
        assert field(rec, "returnable") is False


# --------------------------------------------------------------------------
# OdooConnector.url: Odooly reads HTTP Basic credentials off the URL, then
# strips them from client._server -- so the URL must be rebuilt on every
# client construction or session renewal loses the credentials.
# --------------------------------------------------------------------------
class TestConnectorUrl:
    def test_no_basic_credentials_leaves_the_host_untouched(self, monkeypatch):
        monkeypatch.delenv("ERP_BASIC_USER", raising=False)
        monkeypatch.delenv("ERP_BASIC_PASSWORD", raising=False)
        c = OdooConnector(host="https://erp.example.com", database="db")
        assert c.url == "https://erp.example.com"

    def test_credentials_are_injected_as_userinfo(self, monkeypatch):
        monkeypatch.setenv("ERP_BASIC_USER", "user")
        monkeypatch.setenv("ERP_BASIC_PASSWORD", "secret")
        c = OdooConnector(host="https://erp.example.com", database="db")
        assert c.url == "https://user:secret@erp.example.com"

    def test_special_characters_are_percent_encoded(self, monkeypatch):
        monkeypatch.setenv("ERP_BASIC_USER", "a@b")
        monkeypatch.setenv("ERP_BASIC_PASSWORD", "p/w:d")
        c = OdooConnector(host="https://erp.example.com", database="db")
        # an unencoded '@' or ':' would truncate the host when Odooly splits it
        assert c.url == "https://a%40b:p%2Fw%3Ad@erp.example.com"

    def test_existing_userinfo_is_replaced_not_doubled(self, monkeypatch):
        monkeypatch.setenv("ERP_BASIC_USER", "new")
        monkeypatch.setenv("ERP_BASIC_PASSWORD", "pass")
        c = OdooConnector(host="https://old:creds@erp.example.com", database="db")
        assert c.url == "https://new:pass@erp.example.com"
        assert c.url.count("@") == 1

    def test_url_is_recomputed_each_access(self, monkeypatch):
        """renew_session() relies on this: a cached value would lose the
        credentials Odooly strips from client._server."""
        monkeypatch.setenv("ERP_BASIC_USER", "u")
        monkeypatch.setenv("ERP_BASIC_PASSWORD", "p1")
        c = OdooConnector(host="https://erp.example.com", database="db")
        assert c.url == "https://u:p1@erp.example.com"
        monkeypatch.setenv("ERP_BASIC_PASSWORD", "p2")
        assert c.url == "https://u:p2@erp.example.com"


# --------------------------------------------------------------------------
# credentials(): Odoo 14+ API keys, for deployments that refuse password
# authentication on external RPC.
# --------------------------------------------------------------------------
class TestCredentials:
    def test_password_mode_by_default(self, monkeypatch):
        monkeypatch.setenv("ERP_USERNAME", "api")
        monkeypatch.setenv("ERP_PASSWORD", "pw")
        monkeypatch.delenv("ERP_API_KEY", raising=False)
        assert OdooConnector.credentials() == ("api", "pw", None)

    def test_api_key_is_sent_in_the_password_slot(self, monkeypatch):
        """Odooly only honours its own api_key argument on Odoo >= 19; below
        that it authenticates with `password` alone and discards the key. So
        the key must occupy the password slot, or it never reaches the wire."""
        monkeypatch.setenv("ERP_USERNAME", "api")
        monkeypatch.setenv("ERP_PASSWORD", "pw")
        monkeypatch.setenv("ERP_API_KEY", "key123")
        user, password, api_key = OdooConnector.credentials()
        assert (user, password) == ("api", "key123")   # key, NOT "pw"
        assert api_key == "key123"

    def test_api_key_alone_is_sufficient(self, monkeypatch):
        monkeypatch.setenv("ERP_USERNAME", "api")
        monkeypatch.delenv("ERP_PASSWORD", raising=False)
        monkeypatch.setenv("ERP_API_KEY", "key123")
        assert OdooConnector.credentials() == ("api", "key123", "key123")

    def test_missing_both_secrets_raises(self, monkeypatch):
        monkeypatch.setenv("ERP_USERNAME", "api")
        monkeypatch.delenv("ERP_PASSWORD", raising=False)
        monkeypatch.delenv("ERP_API_KEY", raising=False)
        with pytest.raises(ValueError):
            OdooConnector.credentials()
