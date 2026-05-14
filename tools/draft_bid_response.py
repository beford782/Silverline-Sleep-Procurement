#!/usr/bin/env python3
"""
draft_bid_response.py

Render a starter bid response markdown by combining one opportunity
row (from bids/active/_pipeline.csv or the archive) with a vendor
profile JSON. The draft mirrors the 7-section structure of
bids/templates/bid_response_template.md.

Drafts are intentionally written to build/drafts/ (gitignored) so the
generator never overwrites committed bid markdown. When you're happy
with a draft, copy it into bids/active/<opportunity-id>.md and edit
from there.

Usage:
    python tools/draft_bid_response.py <opportunity-id> \
        --vendor vendor-profiles/<vendor>.profile.json \
        [--active bids/active/_pipeline.csv] \
        [--archive bids/archive/_pipeline_archive.csv] \
        [--output-dir build/drafts] \
        [--generated-date YYYY-MM-DD] \
        [--force]

Stdlib only. The vendor profile is validated against
vendor-profiles/vendor_profile.schema.json before drafting.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ACTIVE = REPO_ROOT / "bids" / "active" / "_pipeline.csv"
DEFAULT_ARCHIVE = REPO_ROOT / "bids" / "archive" / "_pipeline_archive.csv"
DEFAULT_OUTPUT = Path("build") / "drafts"
DEFAULT_SCHEMA = REPO_ROOT / "vendor-profiles" / "vendor_profile.schema.json"

# Make validate_vendor_profile.validate() importable without circular paths.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_vendor_profile import validate as validate_against_schema  # noqa: E402


# ---------------------------------------------------------------------
# Opportunity + profile loading
# ---------------------------------------------------------------------

def _read_pipeline(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def find_opportunity(
    opportunity_id: str,
    active_path: Path,
    archive_path: Path,
) -> tuple[dict, str]:
    """Look up the row by id in active first, then archive.

    Returns (row, source) where source is 'active' or 'archive'.
    Raises LookupError if not found in either.
    """
    for source, path in (("active", active_path), ("archive", archive_path)):
        for row in _read_pipeline(path):
            if (row.get("opportunity_id") or "").strip() == opportunity_id:
                return row, source
    raise LookupError(
        f"opportunity_id {opportunity_id!r} not found in {active_path} or {archive_path}"
    )


def load_vendor_profile(path: Path, schema_path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        profile = json.load(fh)
    with schema_path.open("r", encoding="utf-8") as fh:
        schema = json.load(fh)
    errors = validate_against_schema(profile, schema)
    if errors:
        raise ValueError(
            "vendor profile failed schema validation:\n  " + "\n  ".join(errors)
        )
    return profile


# ---------------------------------------------------------------------
# Derived facts
# ---------------------------------------------------------------------

def _split_semis(text: str) -> list[str]:
    """Pipeline CSV columns use '; ' as a separator inside cells."""
    return [t.strip() for t in (text or "").split(";") if t.strip()]


def _humanize_slug(slug: str) -> str:
    """vendor.products keys are snake_case slugs; humanize for matching."""
    return slug.replace("_", " ").lower()


def compute_product_fit(profile: dict, opportunity: dict) -> list[str]:
    """Return product slugs marked 'yes' in profile.products whose
    humanized form appears in opportunity.primary_products or .title.

    A 'yes' value is anything starting with 'yes' (case-insensitive),
    including 'yes (incl. 8-inch)' etc.
    """
    products = (profile.get("products") or {})
    opportunity_text = " ".join(
        (opportunity.get(field) or "").lower()
        for field in ("title", "primary_products", "commodity_terms")
    )
    matches: list[str] = []
    for slug, value in products.items():
        if not isinstance(value, str) or not value.lower().startswith("yes"):
            continue
        if _humanize_slug(slug) in opportunity_text:
            matches.append(slug)
        else:
            # Try a softer match: strip trailing '_mattress' / '_mattresses'.
            stem = re.sub(r"_(mattress|mattresses)$", "", slug)
            if stem and _humanize_slug(stem) in opportunity_text:
                matches.append(slug)
    return matches


def _present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def compute_compliance_status(profile: dict) -> dict[str, str]:
    """Map a fixed list of compliance fields to 'available' / 'TBD'."""
    compliance = profile.get("compliance") or {}
    keys = (
        "spec_sheets",
        "fire_safety",
        "sealed_covers",
        "tamper_resistant",
        "warranty_terms",
        "standard_sizes",
        "moq",
        "private_label",
        "insurance",
        "certifications",
    )
    return {k: ("available" if _present(compliance.get(k)) else "TBD") for k in keys}


def compute_delivery_fit(profile: dict, opportunity: dict) -> dict[str, str]:
    company = profile.get("company") or {}
    method = company.get("delivery_method") or "unknown"
    services = company.get("delivery_services") or []
    service_geography = [g.lower() for g in (company.get("service_geography") or [])]
    location = (opportunity.get("delivery_location") or "").strip()
    if not location:
        coverage = "delivery location not stated"
    elif any(geo in location.lower() for geo in service_geography):
        coverage = f"{location} is inside listed service geography"
    else:
        coverage = (
            f"{location} is outside the vendor's listed service geography "
            f"({', '.join(company.get('service_geography') or []) or 'none recorded'})"
        )
    return {
        "method": method.replace("_", " "),
        "services": ", ".join(services) if services else "none recorded",
        "coverage": coverage,
    }


def compute_pricing_fit(profile: dict) -> dict[str, str]:
    prefs = profile.get("contract_preferences") or {}
    return {
        "fixed_price_comfort": prefs.get("fixed_price_comfort") or "TBD",
        "pricing_constraints": prefs.get("pricing_constraints") or "TBD",
        "preferred_types": ", ".join(prefs.get("preferred_types") or []) or "TBD",
    }


def has_past_performance(profile: dict) -> bool:
    refs = profile.get("reference_contracts") or []
    return any(bool(r.get("reference_available")) for r in refs)


def decision_suggestion(opportunity: dict) -> str:
    risk = (opportunity.get("risk_level") or "").lower()
    if risk == "low":
        return "bid"
    if risk == "medium":
        return "evaluate"
    if risk == "high":
        return "no-bid candidate"
    return "TBD (risk_level not yet scored)"


# ---------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------

def _check(label: str, present: bool) -> str:
    box = "[x]" if present else "[ ]"
    suffix = "" if present else " — TBD"
    return f"- {box} {label}{suffix}"


def render_draft(
    profile: dict,
    profile_path: Path,
    opportunity: dict,
    source_label: str,
    generated_date: str,
) -> str:
    vendor_name = (profile.get("vendor") or {}).get("legal_name") or "Vendor"
    title = opportunity.get("title") or "(untitled)"
    fit_score = opportunity.get("fit_score") or "—"
    risk_level = opportunity.get("risk_level") or "—"
    estimated_value = opportunity.get("estimated_value") or "—"
    est_value_display = f"${estimated_value}" if estimated_value and estimated_value != "—" else "—"

    compliance = compute_compliance_status(profile)
    product_fit = compute_product_fit(profile, opportunity)
    delivery_fit = compute_delivery_fit(profile, opportunity)
    pricing_fit = compute_pricing_fit(profile)
    setup_gaps = profile.get("setup_gaps") or []
    past_performance = has_past_performance(profile)

    # The draft is intended to be copied into bids/active/<id>.md, so
    # link to the vendor narrative .md sibling using the same relative
    # path convention as the existing committed bid markdown.
    profile_md_name = profile_path.name.replace(".profile.json", ".md")
    profile_md_rel = f"../../vendor-profiles/{profile_md_name}"

    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    profile_label = os.path.relpath(profile_path, REPO_ROOT).replace("\\", "/")
    lines.append(f"_Draft generated {generated_date} from `{profile_label}` and pipeline row "
                 f"`{opportunity.get('opportunity_id', '')}` ({source_label})._")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Status | {opportunity.get('status') or 'watching'} |")
    lines.append(f"| Buyer | {opportunity.get('buyer') or '—'} |")
    lines.append(f"| Solicitation # | {opportunity.get('solicitation_number') or '—'} |")
    lines.append(f"| Portal | {opportunity.get('source') or '—'} |")
    lines.append(f"| Posted | {opportunity.get('posted_date') or '—'} |")
    lines.append(f"| Q&A deadline | {opportunity.get('question_deadline') or '—'} |")
    lines.append(f"| Response due | {opportunity.get('due_date') or '—'} |")
    lines.append(f"| Vendor | [{vendor_name}]({profile_md_rel}) |")
    lines.append(f"| Owner | {opportunity.get('owner') or '—'} |")
    lines.append(f"| Fit score | {fit_score} ({risk_level}) |")
    lines.append(f"| Estimated value | {est_value_display} |")
    lines.append("")

    lines.append("## 1. Scope summary")
    lines.append("")
    notes = (opportunity.get("notes") or "").strip()
    if notes:
        lines.append(notes)
    else:
        lines.append("_Operator: summarize product categories, sizes, quantities, "
                     "delivery scope, contract type, and term length from the "
                     "solicitation document._")
    lines.append("")

    lines.append("## 2. Commodity / NIGP codes")
    lines.append("")
    commodity_terms = _split_semis(opportunity.get("commodity_terms"))
    if commodity_terms:
        for term in commodity_terms:
            lines.append(f"- {term}")
    else:
        lines.append("_Operator: list the codes the solicitation is posted under "
                     "and cross-check against `portal-checklists/<vendor>_portal_setup.md`._")
    lines.append("")

    lines.append("## 3. Fit assessment")
    lines.append("")
    lines.append("**Product fit**")
    lines.append("")
    if product_fit:
        for slug in product_fit:
            lines.append(f"- {_humanize_slug(slug)} (vendor: yes)")
    else:
        lines.append("- No matches between `vendor.products` (`yes`) and the "
                     "opportunity's primary products / commodity terms. Review "
                     "manually.")
    lines.append("")
    lines.append("**Compliance fit**")
    lines.append("")
    for key, status in compliance.items():
        lines.append(f"- {key.replace('_', ' ')}: {status}")
    lines.append("")
    lines.append("**Delivery fit**")
    lines.append("")
    lines.append(f"- Method: {delivery_fit['method']}")
    lines.append(f"- Services: {delivery_fit['services']}")
    lines.append(f"- Coverage: {delivery_fit['coverage']}")
    lines.append("")
    lines.append("**Pricing fit**")
    lines.append("")
    lines.append(f"- Fixed-price comfort: {pricing_fit['fixed_price_comfort']}")
    lines.append(f"- Pricing constraints: {pricing_fit['pricing_constraints']}")
    lines.append(f"- Preferred contract types: {pricing_fit['preferred_types']}")
    lines.append("")

    lines.append("## 4. Required documents")
    lines.append("")
    lines.append(_check("Capability statement", False))
    lines.append(_check("Product specification sheets", compliance["spec_sheets"] == "available"))
    lines.append(_check("Fire-safety / compliance certifications", compliance["fire_safety"] == "available"))
    lines.append(_check("Warranty statement", compliance["warranty_terms"] == "available"))
    lines.append(_check("Insurance certificates (GL, auto, WC, umbrella)", compliance["insurance"] == "available"))
    lines.append(_check("W-9", False))
    lines.append(_check("Conflict-of-interest / vendor forms", False))
    lines.append(_check("Past-performance references", past_performance))
    lines.append(_check("HUB / MBE / WBE / DBE certifications (if applicable)", compliance["certifications"] == "available"))
    lines.append("")

    lines.append("## 5. Open questions for the buyer")
    lines.append("")
    if setup_gaps:
        for i, gap in enumerate(setup_gaps, 1):
            lines.append(f"{i}. {gap}")
    else:
        lines.append("_No outstanding gaps in `vendor.setup_gaps`._")
    lines.append("")

    lines.append("## 6. Pricing approach")
    lines.append("")
    lines.append(f"- Fixed-price comfort: {pricing_fit['fixed_price_comfort']}")
    lines.append(f"- Pricing constraints: {pricing_fit['pricing_constraints']}")
    lines.append("- _Operator: build line-item schedule, escalation language, "
                 "and delivery handling. Do not commit pricing numbers._")
    lines.append("")

    lines.append("## 7. Decision")
    lines.append("")
    lines.append(f"- **Suggested:** {decision_suggestion(opportunity)} "
                 f"(based on risk_level = {risk_level or '—'})")
    lines.append("- **Reason:** _Operator: fill in._")
    lines.append("- **Next action:** _Operator: owner — task — due date._")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------

def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.stem + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _parse_iso_date(value: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"--generated-date must be YYYY-MM-DD ({exc})"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("opportunity_id", help="Pipeline row id to draft against.")
    parser.add_argument("--vendor", required=True, help="Path to vendor-profiles/<vendor>.profile.json.")
    parser.add_argument("--active", default=str(DEFAULT_ACTIVE), help="Active pipeline CSV (default: %(default)s)")
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE), help="Archive pipeline CSV (default: %(default)s)")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA), help="Vendor profile JSON Schema (default: %(default)s)")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT), help="Output directory (default: %(default)s)")
    parser.add_argument("--generated-date", type=_parse_iso_date, default=None,
                        help="ISO date stamped on the draft (default: today). Pin for deterministic output.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing draft file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        opportunity, source_label = find_opportunity(
            args.opportunity_id, Path(args.active), Path(args.archive)
        )
    except LookupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    vendor_path = Path(args.vendor)
    if not vendor_path.is_file():
        print(f"error: vendor profile {vendor_path} not found", file=sys.stderr)
        return 1
    try:
        profile = load_vendor_profile(vendor_path, Path(args.schema))
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    out_path = Path(args.output_dir) / f"{args.opportunity_id}_draft.md"
    if out_path.exists() and not args.force:
        print(
            f"error: {out_path} already exists. Pass --force to overwrite.",
            file=sys.stderr,
        )
        return 1

    generated_date = args.generated_date or date.today().isoformat()
    rendered = render_draft(profile, vendor_path, opportunity, source_label, generated_date)
    _atomic_write(out_path, rendered)

    print(f"opportunity: {args.opportunity_id} ({source_label})")
    print(f"vendor:      {(profile.get('vendor') or {}).get('legal_name')}")
    print(f"date:        {generated_date}")
    print(f"wrote:       {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
