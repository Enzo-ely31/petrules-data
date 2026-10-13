#!/usr/bin/env python3
"""Keep research/translations/<lang>.json in step with the English client texts.

  python3 tools/translations.py delta   # write state/translate_delta.json: entries whose English changed
  python3 tools/translations.py commit  # after translating the delta into every language: record the
                                        # new English as the translation baseline (state/translate_source.json)

The build only uses a translation while its English baseline matches the current English, so a country
whose rules changed shows English until it is re-translated — never an outdated translation.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATASET = ROOT / "countries.json"
SNAPSHOT = ROOT / "state" / "translate_source.json"
DELTA = ROOT / "state" / "translate_delta.json"
TRANSLATIONS = ROOT / "research" / "translations"
KEYS = ("summary", "at_a_glance", "steps", "key_points", "export_points", "private_jet_note")


def current_english():
    data = json.loads(DATASET.read_text(encoding="utf-8"))["countries"]
    out = {}
    for c in data:
        texts = {k: c[k] for k in KEYS if c.get(k)}
        if texts and (c["status"] != "unknown" or texts.get("export_points")):
            out[c["cc"]] = texts
    return out


def delta():
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8")) if SNAPSHOT.exists() else {}
    changed = {cc: texts for cc, texts in current_english().items() if snapshot.get(cc) != texts}
    DELTA.write_text(json.dumps(changed, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(changed)} entries need translation: {' '.join(sorted(changed))}")


def commit():
    if not DELTA.exists():
        sys.exit("No state/translate_delta.json: run 'delta' first.")
    changed = json.loads(DELTA.read_text(encoding="utf-8"))
    langs = sorted(p.stem for p in TRANSLATIONS.glob("*.json"))
    missing = []
    for lang in langs:
        data = json.loads((TRANSLATIONS / f"{lang}.json").read_text(encoding="utf-8"))
        for cc, texts in changed.items():
            block = data.get(cc) or {}
            if set(k for k in KEYS if block.get(k)) != set(texts):
                missing.append(f"{lang}:{cc}")
    if missing:
        sys.exit(f"Not committed, translations missing or incomplete: {' '.join(missing[:40])}")
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8")) if SNAPSHOT.exists() else {}
    snapshot.update(changed)
    SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    DELTA.unlink()
    print(f"Baseline updated for {len(changed)} entries in {len(langs)} languages.")


if __name__ == "__main__":
    {"delta": delta, "commit": commit}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
