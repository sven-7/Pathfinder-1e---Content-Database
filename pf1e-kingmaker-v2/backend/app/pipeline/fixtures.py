"""Built-in Kairon slice fixture records for deterministic bootstrap."""

from __future__ import annotations


def kairon_slice_records(source_name: str) -> list[dict]:
    src = "Core Rulebook"
    if source_name == "d20":
        src = "d20pfsrd curated"

    return [
        {
            "content_type": "class",
            "source_url": "https://www.d20pfsrd.com/classes/hybrid-classes/investigator/",
            "source_book": "Advanced Class Guide",
            "license_tag": "OGL",
            "payload": {
                "name": "Investigator",
                "class_type": "hybrid",
                "hit_die": "d8",
                "skill_ranks_per_level": 6,
                "bab_progression": "three_quarter",
                "fort_progression": "poor",
                "ref_progression": "good",
                "will_progression": "good",
            },
        },
        {
            "content_type": "class_progression",
            "source_url": "https://www.d20pfsrd.com/classes/hybrid-classes/investigator/",
            "source_book": "Advanced Class Guide",
            "license_tag": "OGL",
            "payload": {
                "class_name": "Investigator",
                "level": 9,
                "bab": 6,
                "fort_save": 3,
                "ref_save": 6,
                "will_save": 6,
                "special": "trapfinding, inspiration, studied combat",
                "spells_per_day": {"1": 5, "2": 4, "3": 3},
            },
        },
        {
            "content_type": "race",
            "source_url": "https://www.d20pfsrd.com/races/other-races/featured-races/arg/tiefling/",
            "source_book": src,
            "license_tag": "OGL",
            "payload": {
                "name": "Tiefling",
                "race_type": "featured",
                "size": "Medium",
                "base_speed": 30,
            },
        },
        {
            "content_type": "racial_trait",
            "source_url": "https://www.d20pfsrd.com/races/other-races/featured-races/arg/tiefling/",
            "source_book": src,
            "license_tag": "OGL",
            "payload": {
                "race_name": "Tiefling",
                "name": "Darkvision",
                "trait_type": "senses",
                "description": "Tieflings can see perfectly in darkness of any kind up to 60 feet.",
                "replaces": "",
            },
        },
        {
            "content_type": "feat",
            "source_url": "https://www.d20pfsrd.com/feats/combat-feats/weapon-finesse-combat/",
            "source_book": src,
            "license_tag": "OGL",
            "payload": {
                "name": "Weapon Finesse",
                "feat_type": "combat",
                "prerequisites": "Base attack bonus +1",
                "benefit": "Use Dexterity instead of Strength on light weapon attack rolls.",
            },
        },
        {
            "content_type": "feat",
            "source_url": "https://www.d20pfsrd.com/feats/combat-feats/weapon-focus-combat/",
            "source_book": src,
            "license_tag": "OGL",
            "payload": {
                "name": "Weapon Focus",
                "feat_type": "combat",
                "prerequisites": "Proficiency with selected weapon, base attack bonus +1",
                "benefit": "Gain +1 bonus on attack rolls with chosen weapon.",
            },
        },
        {
            "content_type": "feat",
            "source_url": "https://www.d20pfsrd.com/feats/combat-feats/rapid-shot-combat/",
            "source_book": src,
            "license_tag": "OGL",
            "payload": {
                "name": "Rapid Shot",
                "feat_type": "combat",
                "prerequisites": "Dex 13, Point-Blank Shot",
                "benefit": "One extra ranged attack at highest bonus with a -2 penalty.",
            },
        },
        {
            "content_type": "trait",
            "source_url": "https://www.d20pfsrd.com/traits/combat-traits/reactionary/",
            "source_book": "Ultimate Campaign",
            "license_tag": "OGL",
            "payload": {
                "name": "Reactionary",
                "trait_type": "Combat",
                "benefit": "+2 trait bonus on initiative checks.",
                "description": "You were bullied often as a child, and never learned to trust others.",
            },
        },
        {
            "content_type": "spell",
            "source_url": "https://www.d20pfsrd.com/magic/all-spells/h/haste/",
            "source_book": src,
            "license_tag": "OGL",
            "payload": {
                "name": "Haste",
                "school": "transmutation",
                "description": "One creature per level moves and acts more quickly than normal.",
            },
        },
        {
            "content_type": "spell_class_level",
            "source_url": "https://www.d20pfsrd.com/magic/all-spells/h/haste/",
            "source_book": src,
            "license_tag": "OGL",
            "payload": {
                "spell_name": "Haste",
                "class_name": "Investigator",
                "level": 3,
            },
        },
        {
            "content_type": "equipment",
            "source_url": "https://www.d20pfsrd.com/equipment/weapons/weapon-descriptions/rapier/",
            "source_book": src,
            "license_tag": "OGL",
            "payload": {
                "name": "Rapier",
                "equipment_type": "weapon",
                "cost": "20 gp",
                "weight": 2,
                "description": "A rapier is a light thrusting weapon.",
            },
        },
        {
            "content_type": "weapon",
            "source_url": "https://www.d20pfsrd.com/equipment/weapons/weapon-descriptions/rapier/",
            "source_book": src,
            "license_tag": "OGL",
            "payload": {
                "equipment_name": "Rapier",
                "proficiency": "martial",
                "weapon_type": "melee",
                "handedness": "one-handed",
                "damage_medium": "1d6",
                "critical": "18-20/x2",
            },
        },
        {
            "content_type": "equipment",
            "source_url": "https://www.d20pfsrd.com/equipment/armor/studded-leather/",
            "source_book": src,
            "license_tag": "OGL",
            "payload": {
                "name": "Studded Leather",
                "equipment_type": "armor",
                "cost": "25 gp",
                "weight": 20,
                "description": "This armor is made from tough but flexible leather.",
            },
        },
        {
            "content_type": "armor",
            "source_url": "https://www.d20pfsrd.com/equipment/armor/studded-leather/",
            "source_book": src,
            "license_tag": "OGL",
            "payload": {
                "equipment_name": "Studded Leather",
                "armor_type": "light",
                "armor_bonus": 3,
                "max_dex": 5,
                "armor_check_penalty": -1,
                "arcane_spell_failure": 15,
            },
        },
    ]
