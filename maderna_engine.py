"""
maderna_engine.py — computational engine for the Maderna Machine (Magic Squares).

Formalizes Bruno Maderna's "shifting technique" / "squares technique" (c. 1951),
the serial machine behind *Improvvisazione n. 1*, after Veniero Rizzardi,
"The Tone Row, Squared" (in M. Delaere ed., *Rewriting Recent Music History*,
Peeters 2011, pp. 45-65).

PURE PYTHON, STANDARD LIBRARY ONLY. All MusicXML is written by hand with
xml.etree.ElementTree. Designed to run inside Pyodide; every api_*() function
returns a JSON string and never raises across the boundary.

(c) 2026 Paulo de Assis — part of the compositional-machines series.
"""

import json
import math
import random
import re
import traceback
from xml.etree.ElementTree import Element, SubElement, tostring

# --------------------------------------------------------------------------
# Constants — Maderna's pitch coding: 1=A, 2=Bb, 3=B, 4=C, 5=C#, 6=D,
# 7=Eb, 8=E, 9=F, 10=F#, 11=G, 12=Ab (chromatic from A).
# --------------------------------------------------------------------------

PITCH_NAMES = ["A", "Bb", "B", "C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab"]

# code 1..12 -> (step, alter, octave), fixed register around middle C (A3..Ab4)
PITCH_SPELL = {
    1: ("A", 0, 3), 2: ("B", -1, 3), 3: ("B", 0, 3), 4: ("C", 0, 4),
    5: ("C", 1, 4), 6: ("D", 0, 4), 7: ("E", -1, 4), 8: ("E", 0, 4),
    9: ("F", 0, 4), 10: ("F", 1, 4), 11: ("G", 0, 4), 12: ("A", -1, 4),
}

DEFAULT_FACTORS = [14, 14, 5, 11, 25, 10, 6, 9, 8, 13, 5, 12]  # sum = 132
IMPROVVISAZIONE_ROW = [2, 1, 6, 10, 5, 4, 9, 8, 3, 7, 12, 11]

PROPORTION_LETTERS = "ABCDEFGHIJKL"

DIVISIONS = 4  # quarter = 4, eighth = 2, sixteenth = 1

DANCES = [
    {"name": "Waltz", "beats": 3, "beat_type": 4,
     "pattern": [(4, "quarter"), (4, "quarter"), (4, "quarter")]},
    {"name": "Polka", "beats": 2, "beat_type": 4,
     "pattern": [(2, "eighth"), (2, "eighth"), (4, "quarter")]},
    {"name": "Cancan", "beats": 2, "beat_type": 4,
     "pattern": [(2, "eighth"), (1, "16th"), (1, "16th"), (2, "eighth"), (2, "eighth")]},
]
SINGLE_METER = {"name": "Single meter", "beats": 4, "beat_type": 4,
                "pattern": [(4, "quarter")] * 4}


def code_to_midi(code):
    return 56 + code  # 1 -> 57 (A3) ... 12 -> 68 (Ab4)


# --------------------------------------------------------------------------
# Input parsing
# --------------------------------------------------------------------------

_NAME_MAP = {
    "a": 1, "a#": 2, "bb": 2, "b": 3, "c": 4, "c#": 5, "db": 5, "d": 6,
    "d#": 7, "eb": 7, "e": 8, "f": 9, "f#": 10, "gb": 10, "g": 11,
    "g#": 12, "ab": 12,
}


def parse_row(text):
    """Parse a tone row given as 1-12, 0-11, or note names.
    Returns (codes, warnings). codes is a list of 12 ints in 1..12."""
    warnings = []
    if isinstance(text, (list, tuple)):
        tokens = [str(t).strip() for t in text if str(t).strip()]
    else:
        s = str(text).strip().lower()
        s = s.replace("♭", "b").replace("♯", "#")
        tokens = [t for t in re.split(r"[,;|\s]+", s) if t]
    if len(tokens) != 12:
        raise ValueError("A twelve-tone row needs exactly 12 entries, got %d." % len(tokens))

    if all(re.fullmatch(r"-?\d+", t) for t in tokens):
        nums = [int(t) for t in tokens]
        if any(n < 0 or n > 12 for n in nums):
            warnings.append("Numbers outside 0-12 were wrapped modulo 12.")
            nums = [((n - 1) % 12) + 1 for n in nums]
            codes = nums
        elif 0 in nums:
            codes = [n + 1 for n in nums]
            warnings.append("Row read as 0-11 coding (0=A ... 11=Ab).")
        else:
            codes = nums
    else:
        german = "h" in tokens
        codes = []
        for t in tokens:
            if german and t == "h":
                codes.append(3)   # German H = B natural
            elif german and t == "b":
                codes.append(2)   # German B = B flat
            elif t in _NAME_MAP:
                codes.append(_NAME_MAP[t])
            else:
                raise ValueError("Unrecognized pitch token: %r" % t)
        if german:
            warnings.append("German naming detected (H=B, B=Bb).")

    if sorted(codes) != list(range(1, 13)):
        warnings.append("Row is not a strict permutation of the 12 pitches — proceeding anyway.")
    return codes, warnings


def parse_factors(value):
    """Parse the 12-integer shifting-factor key."""
    if isinstance(value, (list, tuple)):
        nums = [int(v) for v in value]
    else:
        tokens = [t for t in re.split(r"[,;|\s]+", str(value).strip()) if t]
        nums = [int(t) for t in tokens]
    if len(nums) != 12:
        raise ValueError("The shifting-factor key needs exactly 12 integers, got %d." % len(nums))
    if any(n < 1 for n in nums):
        raise ValueError("Shift factors must be positive integers.")
    return nums


# --------------------------------------------------------------------------
# Magic squares (12x12 Latin squares of the symbols 1..12)
# --------------------------------------------------------------------------

def historical_magic():
    """Schematic reconstruction: a 12x12 Latin square with a constant main
    diagonal, evoking the graphic regularity of Maderna's sketch squares.
    L[i][j] = (5i + 7j) mod 12 + 1 — each symbol once per row and column."""
    return [[((5 * i + 7 * j) % 12) + 1 for j in range(12)] for i in range(12)]


def magic_from_seed(seed):
    """Deterministic Latin square: permute rows, columns and symbols of the
    base square with a seeded PRNG. Latin-ness is preserved."""
    rng = random.Random(int(seed))
    base = historical_magic()
    rows = list(range(12))
    cols = list(range(12))
    syms = list(range(1, 13))
    rng.shuffle(rows)
    rng.shuffle(cols)
    rng.shuffle(syms)
    return [[syms[base[r][c] - 1] for c in cols] for r in rows]


def magic_from_row(codes):
    """Cyclic Latin square built from the row itself: L[i][j] = row[(i+j) mod 12]."""
    return [[codes[(i + j) % 12] for j in range(12)] for i in range(12)]


def derived_key_from_row(codes):
    """Factors from the row itself: key[s] = row[s-1] + row[s mod 12]
    (sums of consecutive row entries). For a true permutation the total is
    2 x 78 = 156 = 13 x 12, i.e. 13 derived squares per proportion."""
    return [codes[s] + codes[(s + 1) % 12] for s in range(12)]


def parse_custom_magic(text):
    tokens = [t for t in re.split(r"[,;|\s]+", str(text).strip()) if t]
    if len(tokens) != 144:
        raise ValueError("A custom magic square needs 144 numbers (12 rows x 12), got %d." % len(tokens))
    nums = [int(t) for t in tokens]
    if any(n < 1 or n > 12 for n in nums):
        raise ValueError("Magic-square symbols must be integers 1-12.")
    return [nums[i * 12:(i + 1) * 12] for i in range(12)]


def is_latin(grid):
    target = set(range(1, 13))
    for i in range(12):
        if set(grid[i]) != target:
            return False
        if set(grid[r][i] for r in range(12)) != target:
            return False
    return True


# --------------------------------------------------------------------------
# The machine: basic square, strip derivation, classification
# --------------------------------------------------------------------------

def basic_square(codes):
    """A1 — the 12x12 permutation grid: one dot per column; grid row r = pitch r+1
    (top row = A = 1, bottom row = Ab = 12)."""
    grid = [[0] * 12 for _ in range(12)]
    for col, code in enumerate(codes):
        grid[code - 1][col] += 1
    return grid


def run_machine(codes, magic, key, n_proportions):
    """Derive all squares. The 12x12 charts of one proportion form a horizontal
    strip; each of 12 derivation steps reads one row (even proportions) or one
    column (odd proportions) of the magic square through the key and advances
    each pitch's dot rightward by its factor, leaving a trail of dots that is
    then cut back into 12x12 squares. The residual pattern at the cycle's end
    (start + sum of all factors) seeds the next proportion.
    Returns (squares, meta); each square is {"label","prop","k","grid"}."""
    S = sum(key)
    derived_per = S // 12
    charts_per = -(-S // 12) + 1          # ceil(S/12) + 1; 132 -> 12 charts
    strip_len = 12 * charts_per
    squares = []
    seed_cols = list(range(12))           # trail i starts at column i (= A1)
    for P in range(n_proportions):
        grids = [[[0] * 12 for _ in range(12)] for _ in range(charts_per)]
        new_seeds = list(seed_cols)
        for i in range(12):
            pitch = codes[i]
            x = seed_cols[i]
            for step in range(12):
                pos = x % strip_len
                chart, col = divmod(pos, 12)
                grids[chart][pitch - 1][col] += 1
                read = (step + P) % 12
                if P % 2 == 0:
                    sym = magic[read][pitch - 1]      # read magic-square rows
                else:
                    sym = magic[pitch - 1][read]      # read magic-square columns
                x += key[sym - 1]
            new_seeds[i] = x % 12
        seed_cols = new_seeds
        for k in range(charts_per):
            squares.append({
                "label": PROPORTION_LETTERS[P % 12] + str(k + 1),
                "prop": P, "k": k, "grid": grids[k],
            })
    meta = {"factor_sum": S, "derived_per": derived_per,
            "charts_per": charts_per, "n_squares": len(squares)}
    return squares, meta


def square_stats(grid):
    col_counts = [sum(grid[r][c] for r in range(12)) for c in range(12)]
    filled = sum(1 for c in col_counts if c > 0)
    aggregates = sum(1 for c in col_counts if c >= 2)
    rests = 12 - filled
    repeats = sum(1 for r in range(12) if sum(grid[r]) >= 2)
    return {"filled": filled, "rests": rests, "aggregates": aggregates,
            "repeats": repeats, "dots": sum(col_counts)}


def classify(squares):
    """Maderna's 'structural key of the whole piece': order all sets on two
    axes — full/void ratio (number of empty columns) x number of repeated
    sounds. Returns (stats, chart, reading) where reading walks the chart's
    columns downward/upward alternately, each set alternately prime and
    retrograde."""
    stats = [square_stats(sq["grid"]) for sq in squares]
    rep_values = sorted(set(st["repeats"] for st in stats))
    void_values = sorted(set(st["rests"] for st in stats))
    cells = [[[] for _ in void_values] for _ in rep_values]
    for sq, st in zip(squares, stats):
        ri = rep_values.index(st["repeats"])
        vi = void_values.index(st["rests"])
        cells[ri][vi].append(sq["label"])
    reading = []
    for vi in range(len(void_values)):
        column = []
        for ri in range(len(rep_values)):
            column.extend(cells[ri][vi])
        if vi % 2 == 1:
            column.reverse()
        reading.extend(column)
    reading = [{"label": lab, "retro": i % 2 == 1} for i, lab in enumerate(reading)]
    n_classes = sum(1 for row in cells for cell in row if cell)
    chart = {"rep_values": rep_values, "void_values": void_values,
             "cells": cells, "n_classes": n_classes}
    return stats, chart, reading


def set_events(grid, retro=False):
    """Retranslate one square to notation: each column is a time-slot; one dot
    = a note, >=2 dots = an aggregate (chord), an empty column = a rest."""
    cols = range(11, -1, -1) if retro else range(12)
    events = []
    for c in cols:
        pitches = [r + 1 for r in range(12) if grid[r][c] > 0]
        if pitches:
            events.append({"type": "note", "pitches": pitches})
        else:
            events.append({"type": "rest"})
    return events


# --------------------------------------------------------------------------
# MusicXML (hand-written, partwise 3.1)
# --------------------------------------------------------------------------

def _score_skeleton(title, row_text, part_name="Realization"):
    root = Element("score-partwise", {"version": "3.1"})
    work = SubElement(root, "work")
    SubElement(work, "work-title").text = title
    ident = SubElement(root, "identification")
    SubElement(ident, "creator", {"type": "composer"}).text = "Paulo de Assis — Maderna Machine"
    enc = SubElement(ident, "encoding")
    SubElement(enc, "software").text = "Maderna Machine (Pyodide, hand-written MusicXML)"
    misc = SubElement(ident, "miscellaneous")
    SubElement(misc, "miscellaneous-field", {"name": "input-row"}).text = str(row_text)
    SubElement(misc, "miscellaneous-field", {"name": "technique"}).text = (
        "Bruno Maderna, shifting technique / magic squares (c. 1951), "
        "after V. Rizzardi, 'The Tone Row, Squared' (2011)")
    part_list = SubElement(root, "part-list")
    sp = SubElement(part_list, "score-part", {"id": "P1"})
    SubElement(sp, "part-name").text = part_name
    part = SubElement(root, "part", {"id": "P1"})
    return root, part


def _attributes(measure, divisions=None, time=None, time_visible=True):
    att = SubElement(measure, "attributes")
    if divisions is not None:
        SubElement(att, "divisions").text = str(divisions)
        key = SubElement(att, "key")
        SubElement(key, "fifths").text = "0"
    if time is not None:
        tel = SubElement(att, "time")
        if not time_visible:
            tel.set("print-object", "no")
        SubElement(tel, "beats").text = str(time[0])
        SubElement(tel, "beat-type").text = str(time[1])
    if divisions is not None:
        clef = SubElement(att, "clef")
        SubElement(clef, "sign").text = "G"
        SubElement(clef, "line").text = "2"
    return att


def _words(measure, text, italic=False):
    d = SubElement(measure, "direction", {"placement": "above"})
    dt = SubElement(d, "direction-type")
    w = SubElement(dt, "words")
    if italic:
        w.set("font-style", "italic")
    w.text = text


def _note(measure, code, duration, note_type, chord=False, stemless=False,
          tie_start=False, tie_stop=False):
    n = SubElement(measure, "note")
    if chord:
        SubElement(n, "chord")
    step, alter, octave = PITCH_SPELL[code]
    p = SubElement(n, "pitch")
    SubElement(p, "step").text = step
    if alter:
        SubElement(p, "alter").text = str(alter)
    SubElement(p, "octave").text = str(octave)
    SubElement(n, "duration").text = str(duration)
    if tie_stop:
        SubElement(n, "tie", {"type": "stop"})
    if tie_start:
        SubElement(n, "tie", {"type": "start"})
    SubElement(n, "voice").text = "1"
    SubElement(n, "type").text = note_type
    if alter == 1:
        SubElement(n, "accidental").text = "sharp"
    elif alter == -1:
        SubElement(n, "accidental").text = "flat"
    if stemless:
        SubElement(n, "stem").text = "none"
    if tie_start or tie_stop:
        nots = SubElement(n, "notations")
        if tie_stop:
            SubElement(nots, "tied", {"type": "stop"})
        if tie_start:
            SubElement(nots, "tied", {"type": "start"})
    return n


def _rest(measure, duration, note_type):
    n = SubElement(measure, "note")
    SubElement(n, "rest")
    SubElement(n, "duration").text = str(duration)
    SubElement(n, "voice").text = "1"
    SubElement(n, "type").text = note_type
    return n


def _xml_string(root):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 '
            'Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">\n'
            + tostring(root, encoding="unicode"))


def xml_row_abstract(codes, row_text):
    """Phase 1 — the row as rhythmless, stemless note-heads: a pitch map."""
    root, part = _score_skeleton("Maderna Machine — Tone Row (abstract note-heads)",
                                 row_text, "Tone Row")
    m = SubElement(part, "measure", {"number": "1"})
    _attributes(m, divisions=1, time=(12, 4), time_visible=False)
    _words(m, "The row as a pure pitch succession — no rhythm", italic=True)
    for code in codes:
        _note(m, code, 1, "quarter", stemless=True)
    return _xml_string(root)


def xml_squares_raw(squares, row_text):
    """Phase 2 — the raw sets laid out literally, one measure per square,
    stemless note-heads: pitch/aggregate/rest maps before rhythmic shaping."""
    root, part = _score_skeleton("Maderna Machine — Derived Squares (raw sets)",
                                 row_text, "Raw Sets")
    for idx, sq in enumerate(squares):
        m = SubElement(part, "measure", {"number": str(idx + 1)})
        if idx == 0:
            _attributes(m, divisions=1, time=(12, 4), time_visible=False)
        _words(m, sq["label"])
        for ev in set_events(sq["grid"]):
            if ev["type"] == "rest":
                _rest(m, 1, "quarter")
            else:
                for j, code in enumerate(ev["pitches"]):
                    _note(m, code, 1, "quarter", chord=j > 0, stemless=True)
    return _xml_string(root)


def build_realization_measures(squares_by_label, reading, rhythm_mode):
    """Walk the sets in reading order (color); apply the dance patterns as a
    talea. Returns a list of measures, each {"time":(b,bt)|None, "words":[...],
    "slots":[{dur,type,event,tie_start,tie_stop}]}."""
    measures = []
    current = None
    for idx, entry in enumerate(reading):
        sq = squares_by_label[entry["label"]]
        if rhythm_mode == "single":
            dance = SINGLE_METER
        else:
            dance = DANCES[idx % 3]
        events = set_events(sq["grid"], retro=entry["retro"])
        ei = 0
        first = True
        while ei < len(events):
            m = {"time": None, "words": [], "slots": []}
            if dance is not current:
                m["time"] = (dance["beats"], dance["beat_type"])
                if rhythm_mode != "single":
                    m["words"].append(dance["name"])
                current = dance
            if first:
                m["words"].append(entry["label"] + (" (retro)" if entry["retro"] else ""))
                first = False
            for dur, typ in dance["pattern"]:
                if ei < len(events):
                    ev = events[ei]
                    ei += 1
                else:
                    ev = {"type": "rest"}
                m["slots"].append({"dur": dur, "type": typ, "event": ev,
                                   "tie_start": False, "tie_stop": False})
            measures.append(m)
    # Pedal notes: tie adjacent slots holding identical (non-rest) pitch sets.
    prev = None
    for m in measures:
        for slot in m["slots"]:
            ev = slot["event"]
            if ev["type"] == "note" and prev is not None and \
               prev["event"]["type"] == "note" and \
               prev["event"]["pitches"] == ev["pitches"]:
                prev["tie_start"] = True
                slot["tie_stop"] = True
            prev = slot
    return measures


def xml_full_realization(squares_by_label, reading, rhythm_mode, row_text):
    root, part = _score_skeleton(
        "Maderna Machine — Full Realization (after Improvvisazione n. 1)",
        row_text, "Realization")
    measures = build_realization_measures(squares_by_label, reading, rhythm_mode)
    for mi, m in enumerate(measures):
        meas = SubElement(part, "measure", {"number": str(mi + 1)})
        if mi == 0:
            _attributes(meas, divisions=DIVISIONS, time=m["time"] or (4, 4))
        elif m["time"] is not None:
            _attributes(meas, time=m["time"])
        for w in m["words"]:
            _words(meas, w)
        for slot in m["slots"]:
            ev = slot["event"]
            if ev["type"] == "rest":
                _rest(meas, slot["dur"], slot["type"])
            else:
                for j, code in enumerate(ev["pitches"]):
                    _note(meas, code, slot["dur"], slot["type"], chord=j > 0,
                          tie_start=slot["tie_start"], tie_stop=slot["tie_stop"])
    return _xml_string(root)


def classification_text(chart, stats_by_label=None):
    lines = []
    lines.append("MADERNA MACHINE — CLASSIFICATION CHART")
    lines.append("(the 'structural key of the whole piece')")
    lines.append("")
    lines.append("Rows: number of repeated sounds. Columns: empty columns (void).")
    lines.append("")
    header = "rep\\void |" + "".join(" %4d |" % v for v in chart["void_values"])
    lines.append(header)
    lines.append("-" * len(header))
    for ri, r in enumerate(chart["rep_values"]):
        cells = []
        for vi in range(len(chart["void_values"])):
            cells.append(" ".join(chart["cells"][ri][vi]) or "-")
        lines.append("%8d | " % r + " | ".join(cells))
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# API — every function returns a JSON string; never raises.
# --------------------------------------------------------------------------

def _load(arg):
    """Accept a JSON-encoded value or a bare string."""
    if isinstance(arg, (dict, list)):
        return arg
    try:
        return json.loads(arg)
    except Exception:
        return arg


def _row_text(payload):
    if isinstance(payload, dict):
        return payload.get("row", "")
    return payload


def api_phase1(row_json):
    log = []
    try:
        row_text = _row_text(_load(row_json))
        codes, warnings = parse_row(row_text)
        log.extend("WARNING: " + w for w in warnings)
        grid = basic_square(codes)
        notation = []
        for code in codes:
            step, alter, octave = PITCH_SPELL[code]
            notation.append({"code": code, "name": PITCH_NAMES[code - 1],
                             "step": step, "alter": alter, "octave": octave,
                             "midi": code_to_midi(code)})
        xml = xml_row_abstract(codes, row_text)
        log.append("Row parsed: " + " ".join(str(c) for c in codes) +
                   "  (" + " ".join(PITCH_NAMES[c - 1] for c in codes) + ")")
        log.append("Basic square A1 built (12x12 permutation grid, one dot per column).")
        log.append("Phase-1 MusicXML written: maderna_row_abstract.musicxml")
        return json.dumps({
            "log": "\n".join(log),
            "files": {"maderna_row_abstract.musicxml": xml},
            "notation": notation,
            "squares": {"A1": grid},
            "row_codes": codes,
            "error": False,
        })
    except Exception:
        return json.dumps({"log": traceback.format_exc(), "files": {},
                           "notation": [], "squares": {}, "error": True})


def _machine_setup(codes, machine, log):
    """Resolve magic square + factor key from the machine params."""
    derive = bool(machine.get("derive_from_row"))
    if derive:
        magic = magic_from_row(codes)
        key = derived_key_from_row(codes)
        log.append("Machine derived from the row: cyclic magic square "
                   "L[i][j]=row[(i+j) mod 12]; factors = sums of consecutive row entries.")
        if not is_latin(magic):
            log.append("WARNING: row is not a permutation, so the derived square is not Latin.")
        return magic, key
    mode = machine.get("magic_mode", "historical")
    if mode == "auto":
        seed = machine.get("magic_seed", 1951)
        try:
            seed = int(seed)
        except Exception:
            seed = 1951
        magic = magic_from_seed(seed)
        log.append("Magic square: deterministic Latin square from seed %d." % seed)
    elif mode == "custom":
        magic = parse_custom_magic(machine.get("magic_custom", ""))
        if is_latin(magic):
            log.append("Magic square: custom grid accepted (Latin square verified).")
        else:
            log.append("WARNING: custom grid is NOT a Latin square "
                       "(a symbol repeats within a row or column) — proceeding anyway; "
                       "the pattern may not return to its start.")
    else:
        magic = historical_magic()
        log.append("Magic square: historical reconstruction (schematic Latin square).")
    key = parse_factors(machine.get("factors", DEFAULT_FACTORS))
    return magic, key


def api_generate(row_json, machine_json):
    log = []
    try:
        row_text = _row_text(_load(row_json))
        machine = _load(machine_json)
        if not isinstance(machine, dict):
            machine = {}
        codes, warnings = parse_row(row_text)
        log.extend("WARNING: " + w for w in warnings)

        magic, key = _machine_setup(codes, machine, log)
        n_prop = machine.get("n_proportions", 9)
        try:
            n_prop = max(1, min(12, int(n_prop)))
        except Exception:
            n_prop = 9
        rhythm_mode = machine.get("rhythm_mode", "dances")

        S = sum(key)
        if S % 12 != 0:
            log.append("WARNING: factor sum %d is not a multiple of 12 — the pattern "
                       "will not return exactly to its start; seeds drift between "
                       "proportions. Proceeding." % S)
        log.append("Shifting-factor key: %s  (sum = %d, %d derived squares per proportion)"
                   % (" ".join(map(str, key)), S, S // 12))

        squares, meta = run_machine(codes, magic, key, n_prop)
        stats, chart, reading = classify(squares)

        squares_by_label = {sq["label"]: sq for sq in squares}
        raw_xml = xml_squares_raw(squares, row_text)
        full_xml = xml_full_realization(squares_by_label, reading, rhythm_mode, row_text)
        cls_txt = classification_text(chart)

        n_aggregates = sum(st["aggregates"] for st in stats)
        n_rests = sum(st["rests"] for st in stats)
        summary = {
            "n_squares": meta["n_squares"],
            "n_sets": meta["n_squares"],
            "n_aggregates": n_aggregates,
            "n_rests": n_rests,
            "n_classes": chart["n_classes"],
            "factor_sum": S,
            "derived_per_proportion": meta["derived_per"],
            "charts_per_proportion": meta["charts_per"],
            "n_proportions": n_prop,
            "rhythm_mode": rhythm_mode,
        }
        log.append("Derivation complete: %d proportions x %d squares = %d sets."
                   % (n_prop, meta["charts_per"], meta["n_squares"]))
        log.append("Mutation census: %d aggregate columns (harmonic projections), "
                   "%d empty columns (rests), %d classes in the classification chart."
                   % (n_aggregates, n_rests, chart["n_classes"]))
        log.append("Reading order: down the chart's columns, alternating up/down; "
                   "sets alternately prime and retrograde.")
        log.append("MusicXML written: maderna_squares_raw.musicxml, "
                   "maderna_improvvisazione.musicxml (+ classification chart as text).")

        return json.dumps({
            "log": "\n".join(log),
            "files": {
                "maderna_squares_raw.musicxml": raw_xml,
                "maderna_improvvisazione.musicxml": full_xml,
                "maderna_classification.txt": cls_txt,
            },
            "squares": {
                "labels": [sq["label"] for sq in squares],
                "grids": [sq["grid"] for sq in squares],
                "stats": stats,
                "magic": {"grid": magic, "key": key},
            },
            "chart": {
                "rep_values": chart["rep_values"],
                "void_values": chart["void_values"],
                "cells": chart["cells"],
                "reading": reading,
            },
            "summary": summary,
            "error": False,
        })
    except Exception:
        return json.dumps({"log": traceback.format_exc(), "files": {},
                           "squares": {}, "chart": {}, "summary": {}, "error": True})


def api_validate(row_json, machine_json):
    log = []
    try:
        row_text = _row_text(_load(row_json))
        machine = _load(machine_json)
        if not isinstance(machine, dict):
            machine = {}
        codes, warnings = parse_row(row_text)
        log.extend("WARNING: " + w for w in warnings)
        log.append("Row OK: " + " ".join(PITCH_NAMES[c - 1] for c in codes))
        magic, key = _machine_setup(codes, machine, log)
        S = sum(key)
        if S % 12 != 0:
            log.append("WARNING: factor sum %d is not a multiple of 12." % S)
        else:
            log.append("Factor sum %d = %d x 12: %d derived squares + 1 basic per proportion."
                       % (S, S // 12, S // 12))
        return json.dumps({"log": "\n".join(log), "error": False})
    except Exception:
        return json.dumps({"log": traceback.format_exc(), "error": True})
