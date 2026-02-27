"""Bonus type system with PF1e stacking rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict

# Bonus types that stack with themselves (all instances count).
# Everything else: only the highest value applies.
STACKABLE_TYPES: frozenset[str] = frozenset({"dodge", "racial", "untyped", "penalty", "circumstance"})

# All PF1e named bonus types (circumstance is stackable per RAW).
ALL_BONUS_TYPES = {
    "alchemical", "armor", "circumstance", "competence", "deflection",
    "dodge", "enhancement", "insight", "luck", "morale",
    "natural armor", "profane", "racial", "resistance", "sacred",
    "shield", "size", "trait", "untyped", "penalty",
}


@dataclass
class Bonus:
    value: int
    bonus_type: str     # e.g. "armor", "dodge", "untyped"
    source: str = ""    # human-readable label, e.g. "Chainmail +1"

    def __post_init__(self):
        self.bonus_type = self.bonus_type.lower()


class BonusStack:
    """Accumulates Bonus objects and applies PF1e stacking rules in total()."""

    def __init__(self):
        self._bonuses: list[Bonus] = []

    def add(self, bonus: Bonus) -> None:
        self._bonuses.append(bonus)

    def add_many(self, bonuses: list[Bonus]) -> None:
        self._bonuses.extend(bonuses)

    def total(self) -> int:
        """Sum bonuses, applying stacking rules per bonus type."""
        by_type: dict[str, list[int]] = defaultdict(list)
        for b in self._bonuses:
            by_type[b.bonus_type].append(b.value)

        result = 0
        for btype, values in by_type.items():
            if btype in STACKABLE_TYPES:
                result += sum(values)
            else:
                result += max(values)
        return result

    def breakdown(self) -> list[dict]:
        """Return a list of {type, effective_value, sources} for display."""
        by_type: dict[str, list[Bonus]] = defaultdict(list)
        for b in self._bonuses:
            by_type[b.bonus_type].append(b)

        rows = []
        for btype, bonuses in sorted(by_type.items()):
            if btype in STACKABLE_TYPES:
                effective = sum(b.value for b in bonuses)
            else:
                effective = max(b.value for b in bonuses)
            rows.append({
                "type": btype,
                "effective_value": effective,
                "sources": [{"source": b.source, "value": b.value} for b in bonuses],
            })
        return rows

    def __repr__(self) -> str:
        return f"BonusStack(total={self.total()}, bonuses={self._bonuses!r})"
