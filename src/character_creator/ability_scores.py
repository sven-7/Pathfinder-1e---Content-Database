"""Ability score generation methods for PF1e character creation."""

from __future__ import annotations

import random

ABILITIES = ("str", "dex", "con", "int", "wis", "cha")

STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

# PF1e point buy cost table (score → cost in points)
POINT_BUY_COSTS: dict[int, int] = {
    7: -4, 8: -2, 9: -1, 10: 0, 11: 1, 12: 2,
    13: 3, 14: 5, 15: 7, 16: 10, 17: 13, 18: 17,
}

POINT_BUY_BUDGET = 25
POINT_BUY_MIN = 7
POINT_BUY_MAX = 18


def standard_array() -> list[int]:
    """Return the standard ability score array [15,14,13,12,10,8]."""
    return list(STANDARD_ARRAY)


def point_buy_cost(score: int) -> int:
    """Return the point-buy cost for a single ability score."""
    return POINT_BUY_COSTS.get(max(7, min(18, score)), 0)


def validate_point_buy(assignments: dict[str, int]) -> dict:
    """Validate a point-buy assignment, returning cost info."""
    total_cost = sum(point_buy_cost(v) for v in assignments.values())
    in_range = all(POINT_BUY_MIN <= v <= POINT_BUY_MAX for v in assignments.values())
    return {
        "total_cost": total_cost,
        "budget": POINT_BUY_BUDGET,
        "remaining": POINT_BUY_BUDGET - total_cost,
        "valid": in_range and total_cost <= POINT_BUY_BUDGET,
    }


def roll_4d6() -> list[int]:
    """Roll 6 sets of 4d6-drop-lowest."""
    results = []
    for _ in range(6):
        dice = [random.randint(1, 6) for _ in range(4)]
        results.append(sum(sorted(dice)[1:]))  # drop lowest
    return results


def apply_racial_mods(
    scores: dict[str, int], ability_mods: dict[str, int]
) -> dict[str, int]:
    """Apply racial ability modifiers to a score dict. Returns a new dict."""
    result = dict(scores)
    for ability, mod in ability_mods.items():
        key = ability.lower()
        if key in result:
            result[key] = result[key] + mod
    return result


def ability_modifier(score: int) -> int:
    """PF1e ability modifier formula."""
    return (score - 10) // 2
