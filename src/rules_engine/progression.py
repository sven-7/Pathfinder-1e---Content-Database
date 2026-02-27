"""Class progression: BAB, saves, HP, spell slots."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .character import ClassLevel
    from .db import RulesDB


# ------------------------------------------------------------------ #
# PF1e progression formulas (fallback when DB table is empty)         #
# ------------------------------------------------------------------ #

# BAB per level by progression type
_BAB_PER_LEVEL = {
    "full":          lambda lvl: lvl,
    "three_quarter": lambda lvl: (lvl * 3) // 4,
    "half":          lambda lvl: lvl // 2,
}

# Save bonus by progression type and level
# Good: +2 base at 1st, +1 every 2 levels thereafter  →  (level//2)+2
# Poor: +1 every 3 levels                             →  level//3
_SAVE_BASE = {
    "good": lambda lvl: (lvl // 2) + 2,
    "poor": lambda lvl: lvl // 3,
}

# Hit die average (round up per PF1e: take average + 0.5 → use ceil-half)
_HIT_DIE_AVG = {
    "d6":  4,
    "d8":  5,
    "d10": 6,
    "d12": 7,
}


# ------------------------------------------------------------------ #
# HTML table parser for PSRD progression tables                        #
# ------------------------------------------------------------------ #

@dataclass
class LevelRow:
    level: int
    bab: int
    fort_save: int
    ref_save: int
    will_save: int
    special: str = ""
    spells_per_day: dict[int, int] | None = None   # {spell_level: slots}


_ORDINAL_RE = re.compile(r"(\d+)(?:st|nd|rd|th)", re.IGNORECASE)
_SIGN_RE = re.compile(r"[+\-]?(\d+)")


def _ordinal_to_int(text: str) -> int | None:
    m = _ORDINAL_RE.search(text)
    return int(m.group(1)) if m else None


def _signed_to_int(text: str) -> int:
    text = text.strip().replace("&mdash;", "0").replace("—", "0").replace("–", "0")
    text = text.replace("\u2014", "0").replace("\u2013", "0")
    if not text or text == "—":
        return 0
    m = re.search(r"([+\-]?\d+)", text)
    return int(m.group(1)) if m else 0


def parse_class_progression_html(html: str) -> list[LevelRow]:
    """Parse a PF1e class progression HTML table into LevelRow objects.

    Handles tables with colspan headers (e.g. "Spells per Day" spanning columns).
    """
    try:
        from html.parser import HTMLParser
    except ImportError:
        return []

    class _TableParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.rows: list[list[str]] = []
            self._current_row: list[str] = []
            self._in_cell = False
            self._cell_buf = ""
            self._in_table = False
            self._header_rows: list[list[tuple[str, int]]] = []  # (text, colspan)
            self._in_thead = False
            self._in_th = False
            self._th_colspan = 1

        def handle_starttag(self, tag, attrs):
            attrs_d = dict(attrs)
            if tag == "table":
                self._in_table = True
            elif tag == "thead":
                self._in_thead = True
            elif tag == "tr":
                self._current_row = []
            elif tag in ("td", "th"):
                self._in_cell = True
                self._cell_buf = ""
                if tag == "th":
                    self._in_th = True
                    self._th_colspan = int(attrs_d.get("colspan", 1))

        def handle_endtag(self, tag):
            if tag == "thead":
                self._in_thead = False
            elif tag in ("td", "th"):
                text = re.sub(r"<[^>]+>", "", self._cell_buf).strip()
                if self._in_th:
                    # Store with colspan for later column mapping
                    self._current_row.append((text, self._th_colspan))
                    self._in_th = False
                else:
                    self._current_row.append(text)
                self._in_cell = False
            elif tag == "tr":
                if self._in_thead and self._current_row:
                    self._header_rows.append(list(self._current_row))
                elif not self._in_thead and any(
                    isinstance(c, str) and c for c in self._current_row
                ):
                    self.rows.append(list(self._current_row))
                self._current_row = []

        def handle_data(self, data):
            if self._in_cell:
                self._cell_buf += data

        def handle_entityref(self, name):
            if self._in_cell:
                _entities = {"mdash": "—", "ndash": "–", "amp": "&", "nbsp": " ", "times": "×"}
                self._cell_buf += _entities.get(name, "")

    parser = _TableParser()
    parser.feed(html)

    if not parser.rows:
        return []

    # Build column index from header rows
    # First header row tells us the column names
    col_names: list[str] = []
    if parser._header_rows:
        first_row = parser._header_rows[0]
        for item in first_row:
            if isinstance(item, tuple):
                text, colspan = item
                for _ in range(colspan):
                    col_names.append(text.lower())
            else:
                col_names.append(item.lower())

    def _col_idx(names: list[str]) -> int:
        for n in names:
            for i, col in enumerate(col_names):
                if n in col:
                    return i
        return -1

    level_col = _col_idx(["level"])
    bab_col   = _col_idx(["base attack", "attack bonus"])
    fort_col  = _col_idx(["fort"])
    ref_col   = _col_idx(["ref"])
    will_col  = _col_idx(["will"])
    spec_col  = _col_idx(["special"])

    # Spell column: look for 1st/2nd etc in second header row
    spell_cols: dict[int, int] = {}   # spell_level → col_index
    if len(parser._header_rows) > 1:
        second_row = parser._header_rows[1]
        offset = 0
        for item in second_row:
            text = item[0] if isinstance(item, tuple) else item
            lvl = _ordinal_to_int(text)
            if lvl is not None:
                # Find which column in col_names this maps to
                # The second header row only covers the spell columns
                # They start after "special" column
                if spec_col >= 0:
                    spell_cols[lvl] = spec_col + 1 + offset
                offset += 1

    level_rows: list[LevelRow] = []
    for row in parser.rows:
        if not row:
            continue

        def _get(idx: int) -> str:
            if 0 <= idx < len(row):
                return str(row[idx])
            return ""

        level_text = _get(level_col) if level_col >= 0 else _get(0)
        lvl = _ordinal_to_int(level_text)
        if lvl is None:
            # Try parsing as plain int
            try:
                lvl = int(level_text.strip())
            except ValueError:
                continue

        bab   = _signed_to_int(_get(bab_col))   if bab_col >= 0   else 0
        fort  = _signed_to_int(_get(fort_col))   if fort_col >= 0  else 0
        ref   = _signed_to_int(_get(ref_col))    if ref_col >= 0   else 0
        will  = _signed_to_int(_get(will_col))   if will_col >= 0  else 0
        # For multi-attack BAB strings like "+5/+0", take the first value
        bab_text = _get(bab_col) if bab_col >= 0 else ""
        bab_text = bab_text.split("/")[0]
        bab = _signed_to_int(bab_text)
        special = _get(spec_col) if spec_col >= 0 else ""

        spells: dict[int, int] | None = None
        if spell_cols:
            spells = {}
            for slvl, cidx in spell_cols.items():
                val_str = _get(cidx)
                val_str = val_str.replace("—", "").replace("–", "").replace("\u2014", "").strip()
                if val_str and val_str.isdigit():
                    spells[slvl] = int(val_str)

        level_rows.append(LevelRow(
            level=lvl,
            bab=bab,
            fort_save=fort,
            ref_save=ref,
            will_save=will,
            special=special,
            spells_per_day=spells if spells else None,
        ))

    level_rows.sort(key=lambda r: r.level)
    return level_rows


# ------------------------------------------------------------------ #
# Multi-class aggregation                                              #
# ------------------------------------------------------------------ #

def _class_bab(class_row: dict, level: int, progression: list[dict]) -> int:
    """Return BAB for a single class at a given level, using DB table if available."""
    if progression:
        for row in progression:
            if row["level"] == level:
                return row["bab"]
    # Fall back to formula
    prog_type = class_row.get("bab_progression") or "half"
    return _BAB_PER_LEVEL.get(prog_type, _BAB_PER_LEVEL["half"])(level)


def _class_save(class_row: dict, level: int, save_type: str, progression: list[dict]) -> int:
    """Return base save for a single class at a given level."""
    if progression:
        for row in progression:
            if row["level"] == level:
                return row[f"{save_type}_save"]
    # Fall back to formula
    prog_key = f"{save_type}_progression"
    prog_type = class_row.get(prog_key) or "poor"
    return _SAVE_BASE.get(prog_type, _SAVE_BASE["poor"])(level)


def get_bab(class_levels: list["ClassLevel"], db: "RulesDB") -> int:
    """Multi-class BAB: sum each class's BAB at its level."""
    total = 0
    for cl in class_levels:
        class_row = db.get_class(cl.class_name)
        if class_row is None:
            continue
        progression = db.get_class_progression(class_row["id"])
        total += _class_bab(class_row, cl.level, progression)
    return total


def get_save(class_levels: list["ClassLevel"], save_type: str, db: "RulesDB") -> int:
    """Multi-class saves with the +2 'first good save' bonus per PF1e multiclass rules.

    For each save type, the character gets the sum of the base saves from all classes,
    but the first time a class contributes a 'good' progression for that save the formula
    already includes the +2 bonus (it starts at +2 at level 1).  When multiclassing, the
    +2 should only be counted once per save type.

    Simplification used here (matches most published guides):
      base_save = sum of each class's base save at its level.
    This is correct because the +2 bump is inherent in the good-progression formula.
    """
    total = 0
    for cl in class_levels:
        class_row = db.get_class(cl.class_name)
        if class_row is None:
            continue
        progression = db.get_class_progression(class_row["id"])
        total += _class_save(class_row, cl.level, save_type, progression)
    return total


def get_hp(
    class_levels: list["ClassLevel"],
    con_mod: int,
    favored_class_hp: int,
    db: "RulesDB",
) -> int:
    """Total HP: max at 1st level of first class, average+1 for every other level.

    Args:
        class_levels: Ordered list of ClassLevel objects.
        con_mod: Constitution modifier.
        favored_class_hp: Extra HP from favored class bonus.
    """
    if not class_levels:
        return 0

    total_hp = 0
    first = True
    for cl in class_levels:
        class_row = db.get_class(cl.class_name)
        hit_die = (class_row or {}).get("hit_die") or "d8"
        die_max = int(hit_die.lstrip("d"))
        die_avg = _HIT_DIE_AVG.get(hit_die, die_max // 2 + 1)

        for lvl_idx in range(cl.level):
            if first:
                hp_this = die_max
                first = False
            else:
                hp_this = die_avg
            total_hp += hp_this + con_mod

    total_hp += favored_class_hp
    return max(total_hp, char_total_level(class_levels))


def char_total_level(class_levels: list["ClassLevel"]) -> int:
    return sum(cl.level for cl in class_levels)


def get_spell_slots(
    class_name: str,
    class_level: int,
    db: "RulesDB",
) -> dict[int, int]:
    """Return spells-per-day dict {spell_level: slots} for a class at a given level.

    Reads from class_progression table if populated; returns empty dict otherwise.
    """
    class_row = db.get_class(class_name)
    if class_row is None:
        return {}
    progression = db.get_class_progression(class_row["id"])
    for row in progression:
        if row["level"] == class_level:
            spd_raw = row.get("spells_per_day")
            if spd_raw:
                try:
                    return {int(k): v for k, v in json.loads(spd_raw).items()}
                except (json.JSONDecodeError, TypeError):
                    pass
    return {}
