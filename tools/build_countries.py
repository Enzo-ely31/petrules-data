#!/usr/bin/env python3
"""Merge research/*.json into countries.json (the PetRules country dataset).

Usage: python3 tools/build_countries.py [--generated YYYY-MM-DD]

- validates every entry against the schema (status, required keys)
- keeps `lead_days` (minimum preparation time) only when set explicitly, flags private-jet constraints
- reports duplicates, missing countries (vs. the airport dataset) and unknown / low-confidence entries
"""
import argparse
import datetime
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESEARCH = ROOT / "research"
OUT = ROOT / "countries.json"
AIRPORTS = ROOT / "state" / "airport_countries.json"
# When this repo sits next to the WordPress plugin, also refresh the copy bundled with it.
PLUGIN_COPY = ROOT.parent / "petrules" / "assets" / "countries.json"

STATUSES = {"requirements", "no_restrictions", "unknown", "prohibited"}
TEXT_FIELDS = ["name", "summary", "microchip", "rabies_titer", "parasite_treatment", "import_permit", "quarantine",
               "timeline", "restricted_breeds", "private_aviation", "export", "authority", "last_checked"]
LIST_FIELDS = ["vaccinations", "documents", "sources"]
# Private-aviation notes that block or constrain a pet arriving on a private jet.
PRIVATE_JET_ALERT = re.compile(
    r"manifest(ed)? cargo|as cargo|cannot|not (be )?(permitted|allowed|accepted)|prohibited|"
    r"approved (route|charter|carrier|operator)|written approval",
    re.I)


def lead_days(entry):
    """Minimum preparation time in days, only when the research set it explicitly."""
    value = entry.get("lead_days")
    return value if isinstance(value, int) and 0 < value <= 400 else None


def clean(entry, source):
    errors = []
    cc = str(entry.get("cc", "")).upper()
    if not re.fullmatch(r"[A-Z]{2}", cc):
        errors.append("bad cc")
    if entry.get("status") not in STATUSES:
        errors.append(f"bad status {entry.get('status')!r}")
    out = {"cc": cc, "status": entry.get("status")}
    for key in TEXT_FIELDS:
        value = entry.get(key)
        out[key] = value.strip() if isinstance(value, str) and value.strip() else None
    for key in LIST_FIELDS:
        value = entry.get(key) or []
        if isinstance(value, str):
            value = [value]
        out[key] = [str(v).strip() for v in value if str(v).strip()]
    species = entry.get("prohibited_species") or []
    out["prohibited_species"] = sorted({str(x).lower() for x in species if str(x).lower() in ("dog", "cat")})
    out["private_jet_alert"] = bool(entry.get("private_jet_alert")) or bool(
        out["private_aviation"] and PRIVATE_JET_ALERT.search(out["private_aviation"]))
    out["confidence"] = entry.get("confidence") if entry.get("confidence") in ("high", "medium", "low") else "low"
    out["lead_days"] = lead_days(entry) if out["status"] == "requirements" else None
    out["region_file"] = source
    if out["status"] != "unknown" and not out["sources"]:
        errors.append("no sources")
    return out, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated", default=datetime.date.today().isoformat())
    args = parser.parse_args()

    countries, problems, overrides = {}, [], []
    # research/*.json are the base files; research/updates/*.json (re-verifications) replace entries by code.
    paths = [(p, False) for p in sorted(RESEARCH.glob("*.json"))] + [(p, True) for p in sorted((RESEARCH / "updates").glob("*.json"))]
    for path, is_update in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{path.name}: invalid JSON ({exc})")
            continue
        for entry in data if isinstance(data, list) else data.get("countries", []):
            item, errors = clean(entry, path.stem)
            if errors:
                problems.append(f"{path.name} {item['cc'] or '?'}: {', '.join(errors)}")
            if is_update and item["cc"] in countries and item["status"] in STATUSES:
                overrides.append(f"{item['cc']} ({path.stem})")
                countries[item["cc"]] = item
                continue
            if item["cc"] in countries:
                problems.append(f"duplicate {item['cc']} in {path.name} (kept {countries[item['cc']]['region_file']})")
                continue
            if item["cc"] and item["status"] in STATUSES:
                countries[item["cc"]] = item

    for item in countries.values():
        item.pop("region_file", None)

    dataset = {
        "meta": {"schema": 1, "generated": args.generated, "count": len(countries)},
        "countries": [countries[cc] for cc in sorted(countries)],
    }
    payload = json.dumps(dataset, ensure_ascii=False, separators=(",", ":"))
    OUT.write_text(payload, encoding="utf-8")
    if PLUGIN_COPY.parent.is_dir():
        PLUGIN_COPY.write_text(payload, encoding="utf-8")

    airport_ccs = set(json.loads(AIRPORTS.read_text(encoding="utf-8"))) if AIRPORTS.exists() else set()
    missing = sorted(airport_ccs - set(countries))
    unknown = sorted(cc for cc, c in countries.items() if c["status"] == "unknown")
    low = sorted(cc for cc, c in countries.items() if c["confidence"] == "low" and c["status"] != "unknown")

    print(f"Wrote {OUT.relative_to(ROOT)}: {len(countries)} countries, {OUT.stat().st_size // 1024} KB")
    print(f"Status: " + ", ".join(f"{s}={sum(c['status'] == s for c in countries.values())}" for s in sorted(STATUSES)))
    print(f"Unknown ({len(unknown)}): {' '.join(unknown)}")
    print(f"Low confidence ({len(low)}): {' '.join(low)}")
    print(f"Countries with airports but no entry ({len(missing)}): {' '.join(missing)}")
    if overrides:
        print(f"Updated by research/updates ({len(overrides)}): {' '.join(overrides)}")
    if problems:
        print("Problems:")
        for p in problems:
            print("  -", p)
    return 1 if any("invalid JSON" in p for p in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
