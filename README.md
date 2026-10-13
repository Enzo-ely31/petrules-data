# PetRules data

Dog and cat entry requirements per country, used by the Elysium Jet **PetRules** WordPress plugin.

- `countries.json` — the published dataset (the plugin reads it daily from `raw.githubusercontent.com`).
- `research/*.json` — source research by region; edit these, never `countries.json` directly.
- `research/updates/*.json` — re-verified full entries replacing base ones (alphabetical order, later wins; weekly runs use `w-YYYY-MM-DD.json`).
- `research/editorial/*.json` — short client-facing rewrites (`at_a_glance`, `steps`, `key_points`, `export_points`, `private_jet_note`) merged on top; no new facts.
- `research/translations/<lang>.json` — client texts in fr, es, it, de, ar, ru. Used only while the English they were
  translated from (`state/translate_source.json`) is unchanged; `tools/translations.py delta|commit` manages updates.
- Only information backed by official sources is shown; low-confidence entries display "check with Elysium Jet operations".
- `tools/build_countries.py` — validates `research/` and rebuilds `countries.json` (`python3 tools/build_countries.py`).
- `tools/watch_sources.py` — weekly GitHub Action: hashes every official page cited and opens a
  `[source-changed] CC` issue when one changes.
- A weekly research run re-verifies changed, stale and low-confidence countries, updates `research/`,
  rebuilds and closes the matching issues.

## Entry schema

| Field | Meaning |
| --- | --- |
| `cc`, `name` | ISO 3166-1 alpha-2 code and English name |
| `status` | `requirements`, `no_restrictions`, `unknown` (no reliable official info: check with Elysium Jet operations) or `prohibited` |
| `summary` | Essential path in one or two sentences |
| `microchip`, `vaccinations[]`, `rabies_titer`, `parasite_treatment` | Health requirements and timing |
| `documents[]`, `import_permit`, `quarantine` | Paperwork and quarantine |
| `timeline`, `lead_days` | Preparation sequence and minimum preparation time in days |
| `restricted_breeds`, `private_aviation`, `export` | Breed rules, private-jet specifics, leaving the country |
| `authority`, `sources[]`, `confidence`, `last_checked` | Provenance |

Information only: rules change often. Always confirm with the competent authorities before travel.
