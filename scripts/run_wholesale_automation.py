#!/usr/bin/env python3
"""End-to-end wholesale demand align — dual demand paths + GHL + packets.

Modes:
  saved  — harvest DealDriven dashboard saved searches
  cash   — cash-buyer Property Type toggles (SFR + Multi Family)
  both   — default; run saved then cash

Uses warm Playwright profile (~/.cache/re-browser/dealdriven).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
from paths import (  # noqa: E402
    ALIGNED_DIR,
    DISCOVERY_DIR,
    PACKETS_DIR,
    ensure_skill_on_path,
)

ensure_skill_on_path()
CSV_PATH = DISCOVERY_DIR / "20260725.csv"
PROFILE = Path.home() / ".cache/re-browser/dealdriven"
from dd_demand import (  # noqa: E402
    default_seed_geos,
    fill_visible_address,
    harvest_cash_buyer_types,
    harvest_saved_searches,
    scrape_visible_rows,
)
from comp_geo import (  # noqa: E402
    MAX_COMPS,
    MAX_RADIUS_MILES,
    select_nearby_comps,
    subject_coords_from_gs,
)
from dd_repository import push_subject  # noqa: E402
from ghl_repository import GhlRepository  # noqa: E402
from gsccca_search import (  # noqa: E402
    search_pt61_by_address,
    search_pt61_by_county,
)
from multi_login import (  # noqa: E402
    load_env,
    login_dealdriven,
    login_gsccca,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("run_wholesale")

PROFILE_GSCCCA = Path.home() / ".cache/re-browser/gsccca"
MAX_GSCCCA_ROWS_PER_SEARCH = 100


def _street_address(text: str) -> str:
    """Return street portion if it looks like a real address (not zip/city-only)."""
    s = (text or "").split(",")[0].strip()
    if not s or s.isdigit() or len(s) < 6:
        return ""
    # Require a digit (house number) for PT-61 address search
    if not re.search(r"\d", s):
        return ""
    return s


def criteria_county(crit: dict[str, Any]) -> str:
    geo = crit.get("geo") or {}
    counties = geo.get("counties") or ["Fulton"]
    return counties[0]


def search_gsccca_for_criteria(page: Any, crit: dict[str, Any]) -> dict[str, Any]:
    """PT-61 search: MapSearch for streets; county+date AddressSearch otherwise."""
    county = criteria_county(crit)
    raw = crit.get("raw") or {}
    disc = raw.get("discovery") or {}
    geo = crit.get("geo") or {}
    street = _street_address(disc.get("address") or crit.get("notes") or "")
    if not street:
        return search_pt61_by_county(page, county, login_fn=login_gsccca)
    zips = geo.get("zips") or []
    cities = geo.get("cities") or []
    return search_pt61_by_address(
        page,
        street,
        county,
        city=(cities[0] if cities else ""),
        zip_code=(zips[0] if zips else ""),
        price_min=crit.get("price_min"),
        price_max=crit.get("price_max"),
        login_fn=login_gsccca,
    )


def comps_from_gsccca(
    gs: dict[str, Any],
    *,
    fallback_county: str = "",
    meta: Optional[dict[str, Any]] = None,
    max_rows: int = MAX_GSCCCA_ROWS_PER_SEARCH,
) -> list[dict[str, Any]]:
    """Expand a GSCCCA search result into supply comps (parsed PT-61 rows)."""
    rows = (gs.get("rows") or [])[: max(1, max_rows)]
    meta = meta or {}
    comps: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        # Already supply-schema from parse_pt61_rows
        if row.get("source") == "gsccca" or "sale_date" in row or "grantor" in row:
            comp = dict(row)
            comp.setdefault("source", "gsccca")
            comp.setdefault("county", fallback_county)
            raw = dict(comp.get("raw") or {})
            raw["gsccca_query"] = {
                "query": gs.get("query"),
                "url": gs.get("url"),
                "error": gs.get("error"),
            }
            raw.update(meta)
            comp["raw"] = raw
            comps.append(comp)
    return comps


def discovery_to_criteria(row: dict[str, str]) -> dict[str, Any]:
    return {
        "buyer_id": f"disc-{row.get('address', '').replace(' ', '-').lower()}",
        "source": "discovery-csv",
        "geo": {
            "counties": [row.get("county") or "Fulton"],
            "cities": [],
            "zips": [],
        },
        "property_type": "unknown",
        "vacant": False,
        "noo": False,
        "price_min": None,
        "price_max": None,
        "notes": f"discovery seed {row.get('address')}",
        "raw": {"discovery": row},
    }


def discovery_to_comp(row: dict[str, str], gs: dict[str, Any]) -> dict[str, Any]:
    """Fallback single comp when PT-61 returns no parsed rows."""
    sale_price = None
    try:
        eq = row.get("equity_potential")
        sale_price = int(float(eq)) if eq not in (None, "") else None
    except Exception:
        sale_price = None
    parsed = (gs.get("rows") or [None])[0] if gs.get("rows") else None
    if isinstance(parsed, dict) and (
        parsed.get("sale_date") or parsed.get("grantor") or parsed.get("address")
    ):
        comp = dict(parsed)
        comp.setdefault("source", "gsccca")
        comp.setdefault("county", row.get("county") or "")
        if not comp.get("address"):
            comp["address"] = row.get("address") or ""
        if comp.get("sale_price") is None and sale_price is not None:
            comp["sale_price"] = sale_price
        raw = dict(comp.get("raw") or {})
        raw["discovery"] = row
        raw["gsccca"] = {"url": gs.get("url"), "error": gs.get("error")}
        comp["raw"] = raw
        return comp
    return {
        "source": "gsccca",
        "county": row.get("county") or "",
        "address": row.get("address") or "",
        "parcel": "",
        "sale_date": "",
        "sale_price": sale_price,
        "grantor": "",
        "grantee": "",
        "book_page": "",
        "instrument": "",
        "raw": {"discovery": row, "gsccca": gs},
    }


def score_pair(criteria: dict[str, Any], comp: dict[str, Any]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    c_counties = {
        c.lower() for c in ((criteria.get("geo") or {}).get("counties") or [])
    }
    comp_county = (comp.get("county") or "").lower()
    if comp_county and comp_county in c_counties:
        score += 20
        reasons.append("same county")

    c_zips = set((criteria.get("geo") or {}).get("zips") or [])
    addr = comp.get("address") or ""
    if any(z in addr for z in c_zips):
        score += 15
        reasons.append("zip overlap")

    ptype = criteria.get("property_type") or "unknown"
    if ptype in ("sfr", "multifamily", "2-4"):
        score += 20
        reasons.append(f"property type target {ptype}")
    elif ptype != "unknown":
        score += 10
        reasons.append(f"property type {ptype}")

    if criteria.get("vacant"):
        score += 5
        reasons.append("vacant demand")
    if criteria.get("noo"):
        score += 5
        reasons.append("NOO demand")

    # Stronger when cash/saved harvest returned rows
    raw = criteria.get("raw") or {}
    row_count = 0
    if isinstance(raw.get("rows"), list):
        row_count = len(raw["rows"])
    cash = raw.get("cash_buyer") or {}
    if isinstance(cash.get("rows"), list):
        row_count = max(row_count, len(cash["rows"]))
    if row_count >= 5:
        score += 15
        reasons.append("strong buyer inventory")
    elif row_count >= 1:
        score += 8
        reasons.append("buyer inventory present")

    disc = raw.get("discovery") or {}
    if disc.get("address") and disc.get("address") == comp.get("address"):
        score += 20
        reasons.append("discovery address seed")
    try:
        if float(disc.get("investment_score") or 0) >= 70:
            score += 10
            reasons.append("high investment score")
    except Exception:
        pass

    pmin = criteria.get("price_min")
    pmax = criteria.get("price_max")
    price = comp.get("sale_price")
    if price is not None and (pmin is not None or pmax is not None):
        lo = pmin if pmin is not None else 0
        hi = pmax if pmax is not None else 10**12
        if lo <= price <= hi:
            score += 25
            reasons.append("price in band")

    return min(score, 100), reasons


def build_contract_packets(
    payload: dict[str, Any],
    ghl_summary: dict[str, Any],
    top_n: int = 5,
) -> list[Path]:
    PACKETS_DIR.mkdir(parents=True, exist_ok=True)
    subjects = payload.get("subjects") or []
    ghl_results = ghl_summary.get("results") or []
    paths: list[Path] = []
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    if subjects:
        for i, subject in enumerate(subjects[:top_n]):
            discovery = subject.get("discovery") or {}
            ghl = ghl_results[i] if i < len(ghl_results) else {}
            equity = discovery.get("equity_potential")
            try:
                offer_hint = int(float(equity)) if equity not in (None, "") else None
            except Exception:
                offer_hint = None
            packet = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": "draft",
                "submit_allowed": False,
                "subject": {
                    "address": subject.get("address"),
                    "county": subject.get("county"),
                    "lat": subject.get("lat"),
                    "lng": subject.get("lng"),
                },
                "comps": subject.get("comps") or [],
                "comp_filter": subject.get("comp_filter") or {},
                "demand": discovery_to_criteria(discovery),
                "supply": {
                    "source": "discovery",
                    "county": subject.get("county") or "",
                    "address": subject.get("address") or "",
                    "parcel": "",
                    "sale_date": "",
                    "sale_price": offer_hint,
                    "grantor": "",
                    "grantee": "",
                    "book_page": "",
                    "instrument": "",
                    "raw": {"discovery": discovery, "dealdriven": subject.get("dealdriven")},
                },
                "ghl": {
                    "contact_id": ghl.get("contact_id"),
                    "note_id": ghl.get("note_id"),
                    "tags": ghl.get("tags"),
                },
                "proposed_terms": {
                    "assignment_fee": None,
                    "offer_price": offer_hint,
                    "earnest_money": None,
                    "closing_days": 21,
                    "notes": "Fill before --submit",
                },
                "host_paths": {
                    "partnerdriven_enrollments": "https://partnerdriven.thinkific.com/enrollments",
                    "partnerdriven_video_walkthrough": (
                        "https://partnerdriven.thinkific.com/courses/take/deal-portal/"
                        "lessons/54832305-new-video-walk-through-of-automated-request-a-contract"
                    ),
                    "partnerdriven_request_lesson": (
                        "https://partnerdriven.thinkific.com/courses/take/deal-portal/"
                        "multimedia/47673171-request-a-contract"
                    ),
                    "partnerdriven_submit_lesson": (
                        "https://partnerdriven.thinkific.com/courses/take/deal-portal/"
                        "multimedia/47673172-submit-a-signed-property-contract"
                    ),
                    "request_typeform": "https://csquaredsystems.typeform.com/to/k5qo1JxL",
                },
            }
            path = PACKETS_DIR / f"packet-{stamp}-{i + 1}.json"
            path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
            paths.append(path)
            log.info("Wrote subject packet %s comps=%s", path.name, len(subject.get("comps") or []))
        return paths

    matches = sorted(
        payload.get("matches") or [],
        key=lambda m: int(m.get("score") or 0),
        reverse=True,
    )[:top_n]
    criteria_list = payload.get("criteria") or []
    comps = payload.get("comps") or []
    for i, match in enumerate(matches):
        ci = int(match.get("criteria_index", 0))
        pi = int(match.get("comp_index", 0))
        if ci >= len(criteria_list) or pi >= len(comps):
            continue
        ghl = ghl_results[i] if i < len(ghl_results) else {}
        packet = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "draft",
            "submit_allowed": False,
            "score": match.get("score"),
            "reasons": match.get("reasons"),
            "demand": criteria_list[ci],
            "supply": comps[pi],
            "ghl": {
                "contact_id": ghl.get("contact_id"),
                "note_id": ghl.get("note_id"),
                "tags": ghl.get("tags"),
            },
            "proposed_terms": {
                "assignment_fee": None,
                "offer_price": comps[pi].get("sale_price"),
                "earnest_money": None,
                "closing_days": 21,
                "notes": "Fill before --submit",
            },
            "host_paths": {
                "partnerdriven_enrollments": "https://partnerdriven.thinkific.com/enrollments",
                "partnerdriven_video_walkthrough": (
                    "https://partnerdriven.thinkific.com/courses/take/deal-portal/"
                    "lessons/54832305-new-video-walk-through-of-automated-request-a-contract"
                ),
                "partnerdriven_request_lesson": (
                    "https://partnerdriven.thinkific.com/courses/take/deal-portal/"
                    "multimedia/47673171-request-a-contract"
                ),
                "partnerdriven_submit_lesson": (
                    "https://partnerdriven.thinkific.com/courses/take/deal-portal/"
                    "multimedia/47673172-submit-a-signed-property-contract"
                ),
                "request_typeform": "https://csquaredsystems.typeform.com/to/k5qo1JxL",
            },
        }
        path = PACKETS_DIR / f"packet-{stamp}-{i + 1}.json"
        path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
        paths.append(path)
        log.info("Wrote contract packet %s score=%s", path.name, match.get("score"))
    return paths


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--modes",
        default="both",
        help="saved,cash,both (default both)",
    )
    p.add_argument(
        "--skip-discovery",
        action="store_true",
        help="Do not also process discovery CSV rows",
    )
    p.add_argument(
        "--discovery-only",
        action="store_true",
        help="Skip saved/cash demand harvest; run discovery CSV only",
    )
    p.add_argument(
        "--skip-ghl",
        action="store_true",
        help="Write aligned JSON only; skip GHL sync",
    )
    p.add_argument(
        "--skip-dd",
        action="store_true",
        help="Skip DealDriven property search sync",
    )
    p.add_argument(
        "--skip-packets",
        action="store_true",
        help="Skip contract packet generation",
    )
    p.add_argument(
        "--limit-discovery",
        type=int,
        default=0,
        help="Process only N discovery CSV rows (0 = all)",
    )
    p.add_argument(
        "--skip-demand-gsccca",
        action="store_true",
        help="Skip PT-61 searches for saved/cash criteria (discovery only)",
    )
    p.add_argument("--top-packets", type=int, default=5)
    p.add_argument(
        "--headless",
        action="store_true",
        help="Run browsers headless (default: headed when DISPLAY is set)",
    )
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    load_env()
    modes_raw = (args.modes or "both").lower().replace(" ", "")
    if args.discovery_only:
        modes: set[str] = set()
    elif modes_raw == "both":
        modes = {"saved", "cash"}
    else:
        modes = {m for m in modes_raw.split(",") if m}

    ALIGNED_DIR.mkdir(parents=True, exist_ok=True)

    health = GhlRepository().healthcheck()
    log.info("GHL health ok=%s %s", health.ok, health.detail)
    if not health.ok and not args.skip_ghl:
        return 1

    criteria_list: list[dict[str, Any]] = []
    comps: list[dict[str, Any]] = []
    subjects: list[dict[str, Any]] = []
    matches: list[dict[str, Any]] = []
    errors: list[str] = []
    raw_results: list[dict[str, Any]] = []

    with sync_playwright() as p:
        PROFILE.mkdir(parents=True, exist_ok=True)
        headless = args.headless or not bool(os.environ.get("DISPLAY"))
        context = p.chromium.launch_persistent_context(
            str(PROFILE),
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.new_page()

        dd_login = login_dealdriven(page)
        log.info("DealDriven login ok=%s method=%s", dd_login.ok, dd_login.method)
        if not dd_login.ok:
            context.close()
            return 1
        gs_login = login_gsccca(page)
        log.info("GSCCCA login ok=%s method=%s", gs_login.ok, gs_login.method)
        if not gs_login.ok:
            context.close()
            return 1

        if "saved" in modes:
            log.info("Path A: harvesting saved searches")
            try:
                saved_crit = harvest_saved_searches(page)
                criteria_list.extend(saved_crit)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"saved:{type(exc).__name__}:{exc}")
                log.exception("saved harvest failed")

        extra_zips: list[str] = []
        for c in criteria_list:
            extra_zips.extend((c.get("geo") or {}).get("zips") or [])

        if "cash" in modes:
            log.info("Path B: cash-buyer SFR + Multi Family")
            seeds = default_seed_geos(extra_zips)
            try:
                cash_crit = harvest_cash_buyer_types(page, seeds)
                criteria_list.extend(cash_crit)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"cash:{type(exc).__name__}:{exc}")
                log.exception("cash harvest failed")

        # GSCCCA comps for each demand criteria (PT-61; paced)
        if not args.skip_demand_gsccca:
            for crit in list(criteria_list):
                county = criteria_county(crit)
                log.info("GSCCCA PT-61 for %s (%s)", crit.get("buyer_id"), county)
                try:
                    gs = search_gsccca_for_criteria(page, crit)
                except PlaywrightTimeout:
                    gs = {"error": "timeout", "rows": [], "url": ""}
                if gs.get("error") == "gsccca.challenge":
                    errors.append("align.supply.gsccca.challenge")
                    log.error(
                        "GSCCCA challenge page — stopping further GSCCCA searches"
                    )
                    break
                if gs.get("error") == "gsccca.site_search_wrong_path":
                    errors.append("align.supply.gsccca.site_search_wrong_path")
                    log.error("GSCCCA landed on CMS site-search — aborting GSCCCA path")
                    break

                new_comps = comps_from_gsccca(
                    gs,
                    fallback_county=county,
                    meta={
                        "from_criteria": crit.get("buyer_id"),
                        "property_type": crit.get("property_type"),
                    },
                )
                if not new_comps:
                    new_comps = [
                        {
                            "source": "gsccca",
                            "county": county,
                            "address": "",
                            "parcel": "",
                            "sale_date": "",
                            "sale_price": None,
                            "grantor": "",
                            "grantee": "",
                            "book_page": "",
                            "instrument": "",
                            "raw": {
                                "from_criteria": crit.get("buyer_id"),
                                "gsccca": gs,
                                "row_count": 0,
                            },
                        }
                    ]

                ci = criteria_list.index(crit)
                best_sc = 0
                for comp in new_comps:
                    pi = len(comps)
                    comps.append(comp)
                    sc, reasons = score_pair(crit, comp)
                    best_sc = max(best_sc, sc)
                    if sc >= 50:
                        matches.append(
                            {
                                "criteria_index": ci,
                                "comp_index": pi,
                                "score": sc,
                                "reasons": reasons,
                            }
                        )
                raw_results.append(
                    {
                        "buyer_id": crit.get("buyer_id"),
                        "property_type": crit.get("property_type"),
                        "score": best_sc,
                        "gsccca_url": gs.get("url"),
                        "gsccca_error": gs.get("error"),
                        "gs_rows": len(gs.get("rows") or []),
                    }
                )
                log.info(
                    "  type=%s score=%s gs_rows=%s url=%s",
                    crit.get("property_type"),
                    best_sc,
                    len(gs.get("rows") or []),
                    (gs.get("url") or "")[:80],
                )

        if not args.skip_discovery and CSV_PATH.is_file():
            rows = list(csv.DictReader(CSV_PATH.open()))
            if args.limit_discovery and args.limit_discovery > 0:
                rows = rows[: args.limit_discovery]
            log.info("Discovery CSV rows=%s", len(rows))
            for row in rows:
                address = row.get("address") or ""
                county = row.get("county") or ""
                # Light DealDriven location check
                dd_rows: list[dict[str, Any]] = []
                try:
                    page.goto(
                        "https://app.dealdriven.com/apps/properties/search",
                        wait_until="domcontentloaded",
                        timeout=90000,
                    )
                    page.wait_for_timeout(2000)
                    if fill_visible_address(page, f"{address}, {county}"):
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(4000)
                        dd_rows = scrape_visible_rows(page, limit=15)
                except Exception as exc:  # noqa: BLE001
                    log.warning("discovery DD %s: %s", address, type(exc).__name__)
                try:
                    gs = search_pt61_by_address(
                        page, address, county, login_fn=login_gsccca
                    )
                except PlaywrightTimeout:
                    gs = {"error": "timeout", "rows": [], "url": ""}
                if gs.get("error") == "gsccca.challenge":
                    errors.append("align.supply.gsccca.challenge")
                    break
                if gs.get("error") == "gsccca.site_search_wrong_path":
                    errors.append("align.supply.gsccca.site_search_wrong_path")
                    break
                crit = discovery_to_criteria(row)
                crit["raw"]["dealdriven_rows"] = dd_rows
                # Prefer multifamily-leaning tag for platform inventory; not exclusive
                if not crit.get("property_type") or crit["property_type"] == "unknown":
                    crit["property_type"] = "multifamily"

                parsed_comps = comps_from_gsccca(
                    gs,
                    fallback_county=county,
                    meta={"discovery": row},
                )
                if not parsed_comps:
                    parsed_comps = [discovery_to_comp(row, gs)]

                subj_lat, subj_lng = subject_coords_from_gs(gs)
                nearby, comp_filter = select_nearby_comps(
                    parsed_comps,
                    subject_lat=subj_lat,
                    subject_lng=subj_lng,
                    subject_address=address,
                    max_comps=MAX_COMPS,
                    max_radius_miles=MAX_RADIUS_MILES,
                )

                subject_entry: dict[str, Any] = {
                    "address": address,
                    "county": county,
                    "lat": subj_lat,
                    "lng": subj_lng,
                    "property_type": crit.get("property_type"),
                    "discovery": row,
                    "comps": nearby,
                    "comp_filter": comp_filter,
                    "gsccca": {
                        "url": gs.get("url"),
                        "error": gs.get("error"),
                        "rows_fetched": len(gs.get("rows") or []),
                    },
                    "dealdriven": {
                        "rows_scraped": len(dd_rows),
                    },
                }
                if not args.skip_dd:
                    try:
                        push_subject(page, subject_entry)
                    except Exception as exc:  # noqa: BLE001
                        subject_entry["dealdriven"]["sync_error"] = (
                            f"{type(exc).__name__}:{exc}"
                        )
                subjects.append(subject_entry)

                ci = len(criteria_list)
                criteria_list.append(crit)
                best_sc = 0
                for comp in nearby:
                    pi = len(comps)
                    comps.append(comp)
                    sc, reasons = score_pair(crit, comp)
                    best_sc = max(best_sc, sc)
                    if sc >= 50:
                        matches.append(
                            {
                                "criteria_index": ci,
                                "comp_index": pi,
                                "score": sc,
                                "reasons": reasons,
                            }
                        )
                raw_results.append(
                    {
                        "address": address,
                        "score": best_sc,
                        "dd_rows": len(dd_rows),
                        "gs_rows": len(gs.get("rows") or []),
                        "comps_selected": len(nearby),
                        "comp_filter": comp_filter,
                        "gsccca_url": gs.get("url"),
                        "gsccca_error": gs.get("error"),
                    }
                )
                log.info(
                    "  discovery %s comps=%s within %.1fmi score=%s gs=%s url=%s",
                    address,
                    len(nearby),
                    MAX_RADIUS_MILES,
                    best_sc,
                    len(gs.get("rows") or []),
                    (gs.get("url") or "")[:80],
                )

        context.close()

    unmatched = [
        i
        for i, _ in enumerate(criteria_list)
        if not any(m.get("criteria_index") == i for m in matches)
    ]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    aligned_path = ALIGNED_DIR / f"aligned-{stamp}.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "modes": sorted(modes),
        "comp_policy": {
            "max_comps": MAX_COMPS,
            "max_radius_miles": MAX_RADIUS_MILES,
        },
        "subjects": subjects,
        "criteria": criteria_list,
        "comps": comps,
        "matches": matches,
        "unmatched_criteria": unmatched,
        "errors": errors,
        "raw_results": raw_results,
    }
    aligned_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info(
        "Wrote %s subjects=%s criteria=%s matches=%s types=%s",
        aligned_path,
        len(subjects),
        len(criteria_list),
        len(matches),
        sorted({c.get("property_type") for c in criteria_list}),
    )

    ghl_summary: dict[str, Any] = {"skipped": True}
    if not args.skip_ghl:
        ghl_summary = GhlRepository().sync_aligned_file(aligned_path)
        log.info(
            "GHL sync stored_ok=%s/%s",
            ghl_summary.get("stored_ok"),
            ghl_summary.get("subjects") or ghl_summary.get("matches"),
        )

    packet_paths: list[str] = []
    if not args.skip_packets and (subjects or matches):
        paths = build_contract_packets(payload, ghl_summary, top_n=args.top_packets)
        packet_paths = [str(p) for p in paths]

    dd_summary = {
        "skipped": args.skip_dd,
        "pushed_ok": sum(
            1 for s in subjects if (s.get("dealdriven") or {}).get("sync_ok")
        ),
        "subjects": len(subjects),
    }

    out = {
        "aligned": str(aligned_path),
        "subjects_count": len(subjects),
        "criteria_count": len(criteria_list),
        "match_count": len(matches),
        "property_types": sorted(
            {c.get("property_type") for c in criteria_list if c.get("property_type")}
        ),
        "ghl": ghl_summary,
        "dealdriven": dd_summary,
        "packets": packet_paths,
        "errors": errors,
    }
    print(json.dumps(out, indent=2))
    if args.skip_ghl:
        return 0
    expected = ghl_summary.get("subjects") or ghl_summary.get("matches") or 0
    return 0 if ghl_summary.get("stored_ok") == expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
