# Maderna Machine — Magic Squares · Build Prompt for Fable 5

> **Provenance.** Prompt to build a browser-based algorithmic-composition web app that
> formalizes **Bruno Maderna's "shifting technique" / "squares technique"** (c. 1951),
> the serial machine behind *Improvvisazione n. 1*. Reconstructed from Veniero Rizzardi,
> "The Tone Row, Squared: Bruno Maderna and the Birth of Serial Music in Italy," in
> M. Delaere (ed.), *Rewriting Recent Music History* (Peeters, 2011), pp. 45–65.
> Part of Paulo de Assis's compositional-machines series (after the Lachenmann-machine
> and the Zeitnetz generators). Deploy target: **Netlify, static, zero-backend.**
> Author: Paulo de Assis, 2026.

Paste this whole file into Fable 5.

---

## 0 · One-line goal

A single-page web app in which the user types **one twelve-tone row** and immediately
sees it as a **square** and as **rhythmless note-heads**; then, on a second stage, unfolds
the full **Maderna machine** (magic square + shifting factors → derived squares → 108
sets → rhythmic realization), and downloads **MusicXML** at every stage. Runs entirely in
the browser via Pyodide. No server.

---

## 1 · Architecture (replicate exactly — this mirrors an existing, working app family)

Produce exactly **three files**, ready to deploy to Netlify with `publish = "."`, no build
step:

1. **`index.html`** — fully self-contained: inline `<style>` and inline `<script>`. No
   bundler, no external CSS/JS except Pyodide from CDN.
2. **`maderna_engine.py`** — the computational engine. **PURE PYTHON, standard library
   ONLY** (`random, json, math, fractions, xml.etree.ElementTree`). **NO music21, NO
   numpy, NO micropip, NO pip installs, NO third-party packages.** All MusicXML is written
   by hand with `xml.etree.ElementTree`.
3. **`netlify.toml`** — exactly:

   ```
   [build]
     publish = "."

   [[headers]]
     for = "/*"
     [headers.values]
       Cross-Origin-Embedder-Policy = "require-corp"
       Cross-Origin-Opener-Policy = "same-origin"
   ```

### Runtime model

- Everything runs **in the browser** via Pyodide. No backend, no network calls except
  loading Pyodide itself.
- Load Pyodide from `https://cdn.jsdelivr.net/pyodide/v0.27.0/full/pyodide.js`.
- On page load: show a full-screen loading overlay ("Loading Python runtime ~20 MB…"),
  then `pyodide = await loadPyodide()`, then `fetch('maderna_engine.py')` → text →
  `await pyodide.runPythonAsync(engineCode)`, then hide overlay and enable the UI.
- All computation happens by calling Python `api_*()` functions via `runPythonAsync`,
  passing inputs as `JSON.stringify`'d string arguments.
- **Every `api_*()` returns a JSON STRING** that JS parses to:
  `{ log, files, error, squares, notation, summary }` — see §6.
- JS renders `log` into a scrolling monospace panel with a status pill
  (idle / loading / running / done / error); turns each entry of `files` into a Blob
  download link (`application/xml`); renders `squares` as SVG grids; renders `notation`
  as note-heads (see §5).
- Wrap all Python in `try/except`; never throw across the Pyodide boundary.

### Design language (dark, technical, elegant — the family look)

CSS variables:
`--bg:#1a1a2e; --surface:#16213e; --surface2:#0f3460; --accent:#e94560; --accent2:#533483;
--accent3:#0891b2; --text:#eee; --text2:#aab; --input-bg:#0d1b3e; --border:#2a3a5e;
--success:#4ade80;` monospace (`'SF Mono',Menlo,Consolas`) for inputs/log/grids, system
sans for body. Centered column, max-width ~900px, rounded cards (10px), uppercase
letter-spaced section headers in the accent colour. **You may shift the primary accent to
a warmer Venetian gold/ochre** to distinguish this app from its siblings, keeping the same
dark gridded feel. Fully responsive; the SVG squares must scroll horizontally **inside
their own container** — the page body must never scroll sideways.

---

## 2 · The domain (what the technique is)

Maderna turns a single twelve-tone row into a large field of derived material by graphic
manipulation on squared paper:

- **The basic square (A1).** A 12×12 grid: the 12 **rows** are the 12 chromatic pitches;
  the 12 **columns** are the 12 time-positions. One dot per column marks which pitch
  sounds when. Pitch classes use Maderna's coding **1=A, 2=B♭, 3=B, 4=C, 5=C♯, 6=D,
  7=E♭, 8=E, 9=F, 10=F♯, 11=G, 12=A♭** (chromatic from A). Top grid-row = A (=1), bottom
  grid-row = A♭ (=12). A1 is just a permutation matrix — a picture of the row.
- **The magic square.** A *separate* 12×12 Latin square of 12 symbols (each symbol once
  per row and once per column). Each symbol maps, via a **key**, to an integer **shifting
  factor**. The 12 shifting factors sum to a multiple of 12 (in *Improvvisazione n. 1* the
  sum is **132 = 11×12**: 11 derived squares + 1 basic = 12 squares per "proportion").
- **The shift.** Reading the magic square's rows/columns gives sequences of shift factors.
  Applied note-by-note, each factor says "how far to the right the next dot is drawn,"
  advancing across the strip of successive 12×12 charts. This derives A2 from A1, A3 from
  A2, … until the pattern returns to the start.
- **Mutation.** The derived squares (unlike A1) contain: **repeated dots in a row**,
  **two or more dots in the same column** (vertical **aggregates** / chords), and
  **entirely empty columns** (treated as **rests**). Retranslated into notation, each
  square is now a "series" of heterogeneous material — single notes, aggregates, rests.
  The row has *mutated* (Maderna's term **mutazione**) from a theme into a generative
  distribution. Aggregates were called **"harmonic projection."**
- **Proportions.** Successive "proportions" (nine series of squares, **A through I**) yield
  **9×12 = 108 sets**.
- **Rhythm.** In *Improvvisazione n. 1* the 108 sets are ordered rhythmically via three
  dance patterns — **waltz (3/4), polka (2/4), cancan (2/4)** — in an isorhythmic-motet
  logic (sets = *color*, dance rhythms = *talea*); repeated sounds become held "pedal"
  notes / tremolos.

> **Honesty requirement (state this in the app's "Method / About" note).** The exact
> arithmetic of wrapping, of how empty boxes vs. aggregates arise, and of the reading
> order is *reconstructed* from Rizzardi's description of Maderna's sketches — it is **not**
> a fully specified historical algorithm. This app implements a **clean, self-consistent,
> parameterized model** that faithfully reproduces the documented *behavior* (heterogeneous
> sets of notes/aggregates/rests, 108 squares across 9 proportions, mutation of the row, a
> classification chart) and **exposes the parameters** so the user can experiment. It is a
> computational reconstruction, not a box-for-box reproduction of the sketches. Note also
> that Maderna's magic square and shift-factor key were themselves **compositional choices,
> independent of the row** — the app defaults them so a single row runs the whole machine,
> but exposes them because the *apparatus*, not the row alone, is what generates the music.

---

## 3 · Two-phase flow (the core UX)

The app is organized as **two progressive phases**. Phase 2 is revealed after Phase 1.

### Phase 1 — "The Row & the Square" (input = the tone row ONLY)

The only required input in the whole app. The user types **one twelve-tone row** and
clicks **Generate Square**. The app then shows:

1. **The basic square A1** as an SVG 12×12 grid of dots (pitch names down the left,
   positions 1–12 across the top; one dot per column).
2. **The row as musical notation with abstract, rhythmless note-heads** — the 12 pitches
   as a succession of equal, **stemless** note-heads (no time signature, no bar rhythm, no
   durations); a pure pitch map, not a rhythmic reading.
3. A **MusicXML download** of this Phase-1 realization (the row as stemless, equal-value
   note-heads — see §5 for how to notate "no rhythm").

Phase 1 must work with the row as the sole input; nothing else is needed to see the square
and the note-heads.

### Phase 2 — "The Machine" (row + magic square + shift factors + proportions + rhythm)

Below Phase 1, a section **"The Machine"** (may start collapsed with a "▸ Unfold the
machine" toggle) exposes the generative parameters, **pre-filled with working defaults** so
they never *have* to be edited:

- **Magic square** — radio: *Historical reconstruction* (default) / *Auto from seed* /
  *Custom paste*. (Auto = a deterministic Latin square from a seed/step; Custom = paste a
  12×12 grid, validate Latin-ness.)
- **Shifting-factor key** — 12 integers, default `14 14 5 11 25 10 6 9 8 13 5 12`. Show a
  live readout: **sum = … · sum ÷ 12 = … derived squares per proportion.** The key must
  *follow what the technique allows*: the sum should be a multiple of 12 (warn, but still
  proceed, if not); `sum ÷ 12` is the number of derived squares generated per proportion.
- **Number of proportions** — default 9 (→ 108 sets); range 1–12.
- **Rhythm mapping** — radio: *Three dances (waltz 3/4 · polka 2/4 · cancan 2/4)* (default)
  / *Single meter (e.g. 4/4, equal values)*.
- Checkbox **"Derive the machine from this row"** — when ON, ignore the magic-square and
  shift-factor fields and build them deterministically **from the tone row itself**, so the
  row becomes the sole determinant of the output. When OFF (default), use the fields above.

A **Generate Full Realization** button then runs the whole machine and shows:

1. **The derived squares** — an SVG gallery with a **stepper / slider** to walk A1 → A12 →
   B1 … ; columns with ≥2 dots highlighted (aggregates), empty columns subtly marked
   (rests); plus a view of the **magic square** (symbols + factors).
2. **The classification chart** — all sets ordered by (full/void ratio) × (number of
   repeated sounds 0–4): Maderna's "structural key of the whole piece."
3. **MusicXML downloads** — the raw 108 sets and the full rhythmic realization (see §5).
4. A **log** with counts (n sets, n aggregates, n rests, n classes, sum check, warnings).

### The single built-in example

Provide **one** worked example — as *Mouvement* seeded the Lachenmann machine — via a
button **"Load *Improvvisazione n. 1*"** that fills BOTH the row and the whole machine with
the authentic values:

- **Row:** B♭ A D F♯ C♯ C F E B E♭ G♯ G = `2 1 6 10 5 4 9 8 3 7 12 11`
- **Shift factors:** `14 14 5 11 25 10 6 9 8 13 5 12` (sum 132)
- **Proportions:** 9 · **Rhythm:** three dances.

Also give a **"Reset to defaults"** button (which resets to the *Improvvisazione n. 1*
example) and let the app open pre-loaded with this example so the user sees a full result
on first visit.

---

## 4 · The formal model to implement (precise, deterministic)

Normalize the row internally to Maderna coding 1–12 (accept 1–12, 0–11, or note names:
`a a#/bb b c c#/db d d#/eb e f f#/gb g g#/ab`, German `h`=B and `b`=B♭ tolerated). Validate
it is a permutation of the 12 pitches (warn but allow otherwise).

1. **Build A1** — the 12×12 permutation grid: one dot per column at row = the pitch
   sounding at that position.
2. **Lay the charts as a strip** — for N proportions, treat the successive 12×12 charts as
   one horizontal strip (12 pitch-rows × 12·(squares-per-proportion) boxes per proportion).
3. **Derive A_k → A_{k+1}** — for each derivation step, assign each pitch a shift factor by
   reading that step's row (or column) of the magic square through the key, then advance
   that pitch's dot rightward by that many boxes across the strip (wrap within the strip).
   Record each resulting square. Repeat for the 12 squares of a proportion; the residual
   pattern at the cycle's end seeds the next proportion (*prima proporzione* → B1, …).
   Produce 12·N squares.
4. **Classify** — for each derived square compute (filled vs. empty columns = full/void
   ratio) and (number of repeated sounds, 0–4); assemble the classification chart ordering
   all sets by these two axes.
5. **Retranslate to notation** — each column = a time-slot; one dot = a note (pitch from
   its grid-row, placed in a fixed register, e.g. within ±1 octave of middle C); ≥2 dots in
   a column = a chord/aggregate; an empty column = a rest; a pitch repeated across adjacent
   columns in the same row = a held / tremolo "pedal" note.
6. **Rhythm layer** — walk the sets in Maderna's reading order (down the classification
   chart's columns, alternating upward/downward, reading each set alternately in **prime**
   and **retrograde**), applying the selected dance pattern per section (color = sets,
   talea = dance rhythm). For "single meter," lay each set as equal note-values.

Keep the whole pipeline **deterministic** given the inputs (any randomness only via an
explicit seed), so results are reproducible.

---

## 5 · Outputs — MusicXML (hand-written, Sibelius-compatible)

Valid partwise MusicXML (3.1/4.0) written with `xml.etree`, importing cleanly into
Sibelius / MuseScore. Include a clear title and the input row in the score metadata.

- **`maderna_row_abstract.musicxml`** (Phase 1) — the row as **rhythmless note-heads**:
  equal, **stemless** notes (use `<stem>none</stem>`, a single neutral note `<type>`, no
  beams, no dynamics, no meaningful time signature). A pitch succession, not a rhythm.
- **`maderna_squares_raw.musicxml`** (Phase 2) — the N×12 sets laid out literally: one
  measure/segment per square, notes / aggregates / rests as derived, before rhythmic
  shaping (also as stemless note-heads so the raw sets read as pitch/aggregate maps).
- **`maderna_improvvisazione.musicxml`** (Phase 2) — the full realization with the reading
  order and the dance-rhythm (or single-meter) layer applied; pedal/held notes for repeated
  sounds.

Optionally also `maderna_classification.txt` (or a small MusicXML) of the structural-key
chart.

---

## 6 · Python API contract (mirror the reference family)

Expose these top-level functions in `maderna_engine.py`, each returning `json.dumps({...})`:

- **`api_phase1(row_json)`** → `{ log, files, notation, squares, error }`
  - `files`: `{ "maderna_row_abstract.musicxml": "<xml>" }`
  - `notation`: the ordered pitches for the note-head renderer (list of {name, midi/step}).
  - `squares`: `{ "A1": <12×12 grid of 0/1 or dot lists> }` for the SVG renderer.
- **`api_generate(row_json, machine_json)`** → `{ log, files, squares, chart, summary, error }`
  - `machine_json`: `{ magic_mode, magic_seed, magic_custom, factors, n_proportions,
    rhythm_mode, derive_from_row }`.
  - `files`: the raw + full MusicXML.
  - `squares`: all derived grids (+ the magic square) as plain nested lists for SVG.
  - `chart`: the classification chart as plain nested lists.
  - `summary`: `{ n_squares, n_sets, n_aggregates, n_rests, n_classes, factor_sum,
    derived_per_proportion }`.
- **`api_validate(row_json, machine_json)`** → `{ log, error }`.

On any failure return `{ log: "<traceback>", files: {}, error: true }`.

---

## 7 · UI layout (top to bottom)

- **Header** — title "Maderna Machine — Magic Squares", subtitle "Bruno Maderna's shifting
  technique (1951), reconstructed", short description, a **"Method / About"** toggle (with
  the honesty note from §2), and a **"Load *Improvvisazione n. 1*"** button.
- **Phase 1 — The Row & the Square** — the Tone Row input (+ format hint), a **Generate
  Square** button; then the A1 SVG grid, the rhythmless note-heads, and the Phase-1
  download.
- **Phase 2 — The Machine** (collapsible) — the machine parameters (§3), a **Generate Full
  Realization** button; then the derived-squares gallery (stepper/slider), the magic-square
  view, the classification chart, and the downloads.
- **Log** — scrolling monospace panel + status pill.
- **Downloads** — Blob links (hidden until a run succeeds).
- **Footer** — "© 2026 Paulo de Assis · Runs entirely in your browser (Pyodide) — no server."

---

## 8 · Deliverables

Output the **three complete files** (`index.html`, `maderna_engine.py`, `netlify.toml`),
ready to drop into a folder and deploy to Netlify (`netlify deploy`, publish `.`). No other
files, no build step. Make it work first-try in a modern browser. Priorities, in order:

1. The **two-phase flow** — Phase 1 (row → square + rhythmless note-heads) working before
   Phase 2.
2. The **Pyodide bootstrap** and the **JSON `api_*` contract** exactly as specified.
3. The **pure-Python (no-music21) engine** and **valid MusicXML**.
4. The **SVG squares** visualization (basic square, derived-square stepper, magic square,
   classification chart).
5. The **dark, elegant, responsive UI** and the *Improvvisazione n. 1* example.

*(This is a first build. Expect to iterate on the exact shifting arithmetic, the reading
order, and the notation once the app is running and can be inspected against the source.)*
```

