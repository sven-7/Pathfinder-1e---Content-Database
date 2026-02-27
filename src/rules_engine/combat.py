"""Combat derived statistics: AC, attack bonus, CMB, CMD, initiative."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .bonuses import Bonus, BonusStack

if TYPE_CHECKING:
    from .character import Character
    from .db import RulesDB


# ------------------------------------------------------------------ #
# Size modifiers (PF1e Table 8-1)                                     #
# ------------------------------------------------------------------ #

_SIZE_MODS = {
    "fine":        8,
    "diminutive":  4,
    "tiny":        2,
    "small":       1,
    "medium":      0,
    "large":      -1,
    "huge":       -2,
    "gargantuan": -4,
    "colossal":   -8,
}


def _size_mod(char: "Character", db: "RulesDB | None" = None) -> int:
    """AC/CMD size modifier from character's race size (default medium)."""
    # Look up size from DB races table when available
    if db is not None:
        row = db.get_race(char.race)
        if row and row.get("size"):
            size_str = row["size"].lower()
            if size_str in _SIZE_MODS:
                return _SIZE_MODS[size_str]
    # Fallback: infer from race name string
    race_lower = char.race.lower()
    for size, mod in _SIZE_MODS.items():
        if size in race_lower:
            return mod
    return 0   # medium default


# ------------------------------------------------------------------ #
# AC breakdown                                                         #
# ------------------------------------------------------------------ #

@dataclass
class ACBreakdown:
    total: int
    touch: int
    flat_footed: int
    components: list[dict] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"AC(total={self.total}, touch={self.touch}, ff={self.flat_footed})"


def ac(char: "Character", db: "RulesDB") -> ACBreakdown:
    """Compute AC breakdown for a character.

    Only considers ability scores and size; equipment bonuses (armor/shield)
    would require a full equipment-slot system not yet implemented.
    """
    dex_mod  = char.ability_mod("dex")
    size_mod = _size_mod(char, db)

    stack = BonusStack()

    # Base: always 10
    base = 10

    # Dex to AC (untyped for now; stored as dodge for touch calculation)
    stack.add(Bonus(dex_mod, "dex", "Dexterity"))

    # Size
    if size_mod:
        stack.add(Bonus(size_mod, "size", "Size"))

    total      = base + stack.total()
    touch      = base + dex_mod + size_mod          # excludes armor/shield/natural
    flat_footed = base + size_mod                   # excludes dex, dodge

    return ACBreakdown(
        total=total,
        touch=touch,
        flat_footed=flat_footed,
        components=stack.breakdown(),
    )


# ------------------------------------------------------------------ #
# Attack bonus                                                         #
# ------------------------------------------------------------------ #

def attack_bonus(char: "Character", weapon_type: str = "melee", db: "RulesDB" | None = None) -> int:
    """Return primary attack bonus.

    weapon_type: 'melee' uses STR, 'ranged' uses DEX.
    Enhancement bonuses from equipment are not included (no equipment slot system).
    """
    bab = char.bab(db) if db else 0
    if weapon_type == "ranged":
        ability_mod = char.ability_mod("dex")
    else:
        ability_mod = char.ability_mod("str")
    size_mod = _size_mod(char, db)
    return bab + ability_mod + size_mod


# ------------------------------------------------------------------ #
# CMB / CMD                                                            #
# ------------------------------------------------------------------ #

def cmb(char: "Character", db: "RulesDB") -> int:
    """Combat Maneuver Bonus = BAB + STR mod + size mod."""
    return char.bab(db) + char.ability_mod("str") + _size_mod(char, db)


def cmd(char: "Character", db: "RulesDB") -> int:
    """Combat Maneuver Defense = 10 + BAB + STR mod + DEX mod + size mod."""
    return 10 + char.bab(db) + char.ability_mod("str") + char.ability_mod("dex") + _size_mod(char, db)


# ------------------------------------------------------------------ #
# Initiative                                                           #
# ------------------------------------------------------------------ #

def initiative(char: "Character", db: "RulesDB" | None = None) -> int:
    """Initiative modifier = DEX mod + misc (traits/feats not yet implemented)."""
    return char.ability_mod("dex")
