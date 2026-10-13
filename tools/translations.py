#!/usr/bin/env python3
"""Keep research/translations/<lang>.json in step with the English client texts.

  python3 tools/translations.py delta   # write state/translate_delta.json and state/translate_details_delta.json
  python3 tools/translations.py commit  # after translating the delta into every language: record the
                                        # new English as the translation baseline (state/translate_source.json)

The build only uses a translation while its English baseline matches the current English, and the website
never shows untranslated text on a non-English page. Publish only after
`python3 tools/build_countries.py --strict-translations` succeeds (every entry translated in every language).
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATASET = ROOT / "countries.json"
TRANSLATIONS = ROOT / "research" / "translations"
# Two sets of client texts: short texts (translations/<lang>.json) and full official details (translations/details/<lang>.json).
SETS = {
    "short": {
        "keys": ("summary", "at_a_glance", "steps", "key_points", "export_points", "private_jet_note"),
        "snapshot": ROOT / "state" / "translate_source.json",
        "delta": ROOT / "state" / "translate_delta.json",
        "dir": TRANSLATIONS,
        "include": lambda c, texts: c["status"] != "unknown" or bool(texts.get("export_points")),
    },
    "details": {
        "keys": ("microchip", "vaccinations", "rabies_titer", "parasite_treatment", "documents", "import_permit",
                 "quarantine", "timeline", "restricted_breeds", "private_aviation", "export", "authority"),
        "snapshot": ROOT / "state" / "translate_details_source.json",
        "delta": ROOT / "state" / "translate_details_delta.json",
        "dir": TRANSLATIONS / "details",
        "include": lambda c, texts: c["status"] != "unknown" or bool(texts.get("export")),
    },
}


def current_english(conf):
    data = json.loads(DATASET.read_text(encoding="utf-8"))["countries"]
    out = {}
    for c in data:
        texts = {k: c[k] for k in conf["keys"] if c.get(k)}
        if texts and conf["include"](c, texts):
            out[c["cc"]] = texts
    return out


def delta():
    for name, conf in SETS.items():
        snapshot = json.loads(conf["snapshot"].read_text(encoding="utf-8")) if conf["snapshot"].exists() else {}
        changed = {cc: texts for cc, texts in current_english(conf).items() if snapshot.get(cc) != texts}
        conf["delta"].write_text(json.dumps(changed, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{name}: {len(changed)} entries need translation ({conf['delta'].relative_to(ROOT)}): {' '.join(sorted(changed))}")


def commit():
    problems = []
    for name, conf in SETS.items():
        if not conf["delta"].exists():
            continue
        changed = json.loads(conf["delta"].read_text(encoding="utf-8"))
        langs = sorted(p.stem for p in conf["dir"].glob("*.json"))
        for lang in langs:
            data = json.loads((conf["dir"] / f"{lang}.json").read_text(encoding="utf-8"))
            for cc, texts in changed.items():
                block = data.get(cc) or {}
                if set(k for k in conf["keys"] if block.get(k)) != set(texts):
                    problems.append(f"{name}/{lang}:{cc}")
    if problems:
        sys.exit(f"Not committed, translations missing or incomplete: {' '.join(problems[:40])}")
    for name, conf in SETS.items():
        if not conf["delta"].exists():
            continue
        changed = json.loads(conf["delta"].read_text(encoding="utf-8"))
        snapshot = json.loads(conf["snapshot"].read_text(encoding="utf-8")) if conf["snapshot"].exists() else {}
        snapshot.update(changed)
        conf["snapshot"].write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
        conf["delta"].unlink()
        print(f"{name}: baseline updated for {len(changed)} entries.")


if __name__ == "__main__":
    {"delta": delta, "commit": commit}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
