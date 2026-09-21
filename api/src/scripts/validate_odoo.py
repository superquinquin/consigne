"""Validate the Odooly migration against a live Odoo instance.

Designed for vendor-hosted environments protected by intrusion detection:
every check runs in a SINGLE pass over ONE connection, ordered so that a
truncated run still yields the most valuable answers. A failed
authentication is never retried -- repeating it adds no information and is
what the defences count.

    python -m src.scripts.validate_odoo                 # uses $ERP_URL / $ERP_DB
    python -m src.scripts.validate_odoo --host URL --db NAME
    python -m src.scripts.validate_odoo --discover-db   # probe db candidates
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timedelta

import requests
from urllib.parse import urlsplit

from src.odoo import OdooConnector

# models -> fields the consigne app depends on. Most live in foodcoop addons
# (shift.*, barcode_base, cooperative_state), not in core Odoo, so they are
# the real portability risk across a major version jump.
# Fields the consigne app reads, tagged by origin:
#   "core"  -> ships with Odoo. Missing = a genuine incompatibility.
#   "addon" -> foodcoop/louve addons. Missing on a vanilla instance is
#              EXPECTED and says nothing about the migration; missing on the
#              real staging box means the addon is absent or renamed.
REQUIRED: dict[str, dict[str, str]] = {
    "res.partner":        {"display_name": "core", "barcode_base": "addon",
                           "cooperative_state": "addon"},
    "res.users":          {"partner_id": "core"},
    "product.product":    {"barcode": "core", "product_tmpl_id": "core"},
    "product.template":   {"list_price": "core", "categ_id": "core",
                           "sale_ok": "core", "purchase_ok": "core",
                           "uom_id": "core", "available_in_pos": "core",
                           "returnable": "addon", "return_product_id": "addon",
                           "fiscal_classification_id": "addon",
                           "barcode_base": "addon"},
    "product.category":   {"name": "core", "parent_id": "core"},
    "shift.shift":        {"date_begin_tz": "addon", "date_end_tz": "addon",
                           "shift_type_id": "addon"},
    "shift.registration": {"shift_id": "addon", "partner_id": "addon"},
    "pos.order.line":     {"order_id": "core", "price_unit": "core",
                           "product_id": "core", "create_date": "core"},
}

DB_CANDIDATES = [
    "superquinquin_staging", "superquinquin_staging18", "superquinquin18_staging",
    "superquinquin_18_staging", "superquinquin", "superquinquin18",
]


def discover_db(url: str) -> list[str]:
    """Best-effort database names scraped from the login page."""
    found: list[str] = []
    try:
        r = requests.get(url.rstrip("/") + "/web/login", timeout=20)
        for pat in (r'name="db"[^>]*value="([^"]+)"', r'"db_name"\s*:\s*"([^"]+)"',
                    r'<option[^>]*value="([^"]+)"[^>]*>\s*\1\s*</option>'):
            found += re.findall(pat, r.text)
    except Exception as exc:
        print(f"  (login-page probe failed: {type(exc).__name__})")
    return list(dict.fromkeys(found))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.environ.get("ERP_URL"))
    ap.add_argument("--db", default=os.environ.get("ERP_DB"))
    ap.add_argument("--discover-db", action="store_true")
    args = ap.parse_args()
    if not args.host:
        print("no --host and no $ERP_URL"); return 2

    conn = OdooConnector(host=args.host, database=args.db or "", verbose=False)
    print(f"host   : {urlsplit(args.host).netloc}")
    print(f"basic  : {'yes' if '@' in urlsplit(conn.url).netloc else 'no'}")

    candidates = [args.db] if args.db and not args.discover_db else []
    if args.discover_db:
        scraped = discover_db(conn.url)
        print(f"scraped db names: {scraped or 'none'}")
        candidates = scraped + [d for d in ([args.db] if args.db else []) + DB_CANDIDATES
                                if d not in scraped]

    # --- 1. establish exactly one connection; each db attempted at most once
    import odooly
    try:
        user, pwd, api_key = conn.credentials()
    except ValueError as exc:
        print(exc); return 2
    print(f"auth   : {'api-key' if api_key else 'password'} (user={user!r})")

    client = None
    for db in candidates:
        try:
            client = odooly.Client(conn.url, db, user, pwd, api_key=api_key)
            print(f"\nCONNECTED db={db!r} uid={client.env.uid}")
            break
        except Exception as exc:
            # full error, verbatim: 'invalid credentials' and 'no such database'
            # are NOT distinguishable from the message alone.
            print(f"  db={db!r:32} -> {type(exc).__name__}: {str(exc)[:160]}")
    if client is None:
        print("\nNo database accepted these credentials. The message above is "
              "identical for a wrong password and a wrong database name.")
        return 1

    print(f"odoo version : {client.server_version}")
    print(f"env.db_name  : {client.env.db_name}")

    # --- 2. schema compatibility (cheap, and the real Odoo-18 risk)
    print("\n== models / fields required by the consigne app ==")
    core_gaps: list[str] = []
    addon_gaps: list[str] = []
    for model, fields in REQUIRED.items():
        try:
            present = set(client.env[model].keys())
        except Exception:
            origin = "addon" if all(o == "addon" for o in fields.values()) else "core"
            (addon_gaps if origin == "addon" else core_gaps).append(f"{model} (whole model)")
            print(f"  {'--' if origin == 'addon' else 'XX'}   {model:22} model absent [{origin}]")
            continue
        miss_core = [f for f, o in fields.items() if o == "core" and f not in present]
        miss_addon = [f for f, o in fields.items() if o == "addon" and f not in present]
        core_gaps += [f"{model}.{f}" for f in miss_core]
        addon_gaps += [f"{model}.{f}" for f in miss_addon]
        if not miss_core and not miss_addon:
            print(f"  ok   {model:22} all present")
        else:
            bits = []
            if miss_core:
                bits.append(f"CORE missing {miss_core}")
            if miss_addon:
                bits.append(f"addon missing {miss_addon}")
            print(f"  {'XX' if miss_core else '--'}   {model:22} {' | '.join(bits)}")

    print(f"\n  core gaps  : {len(core_gaps)} {core_gaps if core_gaps else ''}")
    print(f"  addon gaps : {len(addon_gaps)} (expected on an instance without the foodcoop addons)")
    missing_total = len(core_gaps)

    # --- 3. read-only behaviour of the migrated session
    print("\n== migrated OdooSession methods (read-only) ==")
    ok = fail = 0
    with OdooSessionFrom(client, conn) as s:
        for label, fn in session_checks(s):
            try:
                print(f"  PASS  {label}: {str(fn())[:90]}"); ok += 1
            except Exception as exc:
                print(f"  FAIL  {label}: {type(exc).__name__} {str(exc)[:110]}"); fail += 1

    print(f"\nRESULT methods ok={ok} fail={fail} | schema gaps={missing_total}")
    return 0 if (fail == 0 and missing_total == 0) else 1


def OdooSessionFrom(client, connector):
    from src.odoo import OdooSession
    return OdooSession(client, connector)


def session_checks(s):
    """Ordered by value: the deposit core flow first, so a truncated run
    still answers the question that matters."""
    def product_flow():
        tmpls = s.search("product.template", [("returnable", "=", True)])
        for t in tmpls[:10]:
            ps = s.search("product.product",
                          [("product_tmpl_id", "=", t.id), ("barcode", "!=", False)])
            if len(ps):
                p = s.get_product_from_barcode(ps[0].barcode)
                returnable, ret = s.get_product_return(p)
                out = {"product_to_record": s.product_to_record(p),
                       "returnable": returnable}
                if ret is not None:
                    out["return_to_record"] = s.product_return_to_record(ret)
                return out
        return "no returnable product carries a barcode"

    def auth_positive():
        user, pwd, api_key = s.connector.credentials()
        if api_key:
            return "skipped (auth_provider validates operator passwords, not api keys)"
        okauth, rec = s.auth_provider(user, pwd)
        return (okauth, s.user_to_record(rec) if rec is not None else None)

    return [
        ("deposit core flow (positive)", product_flow),
        ("auth_provider (positive)",     auth_positive),
        ("fuzzy_code_search(1)",         lambda: s.fuzzy_code_search(1)),
        ("fuzzy_name_search('a')",       lambda: len(s.fuzzy_name_search("a"))),
        ("get_existing_consigne_barcodes", lambda: len(s.get_existing_consigne_barcodes())),
        ("get_current_shifts",           lambda: len(s.get_current_shifts())),
        ("get_current_shifts_members",   lambda: s.get_current_shifts_members()[0]),
        ("get_current_shift_end_time_dist", lambda: s.get_current_shift_end_time_dist()),
        ("get_redeemed_tickets (datetime args)",
         lambda: len(s.get_redeemed_tickets(["999"], datetime.now(),
                                            datetime.now() - timedelta(days=30)))),
        ("renew_session (keeps basic auth)", lambda: (s.renew_session(), s.client.env.uid)[1]),
    ]


if __name__ == "__main__":
    sys.exit(main())
