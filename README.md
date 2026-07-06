# Maderna Machine — Magic Squares

Browser-based algorithmic-composition app formalizing **Bruno Maderna's "shifting
technique" / "squares technique"** (c. 1951), the serial machine behind
*Improvvisazione n. 1* — reconstructed from Veniero Rizzardi, "The Tone Row, Squared:
Bruno Maderna and the Birth of Serial Music in Italy," in M. Delaere (ed.),
*Rewriting Recent Music History* (Peeters, 2011), pp. 45–65.

Part of Paulo de Assis's **compositional-machines series**, after the
[Lachenmann-machine](https://github.com/MetamusicX/Lachenmann-machine_zeitnetz-generator)
and the Zeitnetz generators.

## What it does

Type **one twelve-tone row** and immediately see it as a 12×12 **square** and as
**rhythmless note-heads** (Phase 1); then unfold the full **Maderna machine** —
magic square + shifting factors → derived squares → 108 sets → classification chart →
dance-rhythm realization (waltz · polka · cancan) — with **MusicXML downloads** at
every stage (Phase 2). Opens pre-loaded with the authentic *Improvvisazione n. 1*
values (row `2 1 6 10 5 4 9 8 3 7 12 11`, factors `14 14 5 11 25 10 6 9 8 13 5 12`,
9 proportions).

Runs **entirely in the browser** via [Pyodide](https://pyodide.org) — no server, no
build step. The engine is pure standard-library Python; all MusicXML is written by
hand with `xml.etree`.

## Files

| File | Role |
|---|---|
| `index.html` | Self-contained UI (inline CSS/JS, Pyodide bootstrap, SVG renderers) |
| `maderna_engine.py` | Computational engine — `api_phase1` / `api_generate` / `api_validate`, each returning JSON |
| `netlify.toml` | Netlify config (static publish, COOP/COEP headers for Pyodide) |
| `maderna-machine_fable-prompt.md` | Provenance: the build prompt for this app |

## Run locally

```
python3 -m http.server 8000
# then open http://localhost:8000
```

Deploy: `netlify deploy` (publish directory `.`).

## Honesty note

The exact arithmetic of Maderna's wrapping, of how empty boxes and aggregates arise,
and of the reading order is *reconstructed* from Rizzardi's description of the
sketches — not a fully specified historical algorithm. The app implements a clean,
self-consistent, parameterized model that reproduces the documented *behavior*
(mutation of the row into heterogeneous sets of notes, aggregates and rests; 108
squares across 9 proportions; the classification chart) and exposes all parameters.
See the in-app **Method / About** note.

---

© 2026 Paulo de Assis
