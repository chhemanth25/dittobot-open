from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Pokemon:
    id: int
    pokname: str
    hpiv: int
    atkiv: int
    defiv: int
    spatkiv: int
    spdefiv: int
    hpev: int
    atkev: int
    defev: int
    spatkev: int
    spdefev: int
    speedev: int
    pokelevel: int
    moves: list
    hitem: str
    exp: int
    nature: str
    expcap: int
    poknick: str
    shiny: bool
    radiant: bool
    market_enlist: bool
    price: int
    happiness: int
    ability_index: int
    name: str
    counter: int
    gender: str

    def gender_check(self, gender_id):
        if gender_id == 1:
            self.gender = "-f"
        elif gender_id == 2:
            self.gender = "-m"


@dataclass
class PFile:
    base_happiness: Any
    capture_rate: Any
    color_id: Any
    conquest_order: Any
    evolution_chain_id: Any
    evolves_from_species_id: Any
    forms_switchable: Any
    gender_rate: Any
    generation_id: Any
    growth_rate_id: Any
    habitat_id: Any
    has_gender_differences: Any
    hatch_counter: Any
    id: Any
    identifier: str
    is_baby: Any
    order: Any
    shape_id: Any


@dataclass
class EvoInfo:
    evolution_trigger_id: Any
    evolved_species_id: Any
    gender_id: Any
    id: Any
    minimum_happiness: Any
    minimum_level: Any
    known_move_id: Any
    trigger_item_id: Any
    info: Optional[PFile]


@dataclass
class FormInfo:
    id: int
    identifier: str
    form_identifier: str
    pokemon_id: int
    introduced_in_version_group_id: int
    is_default: int
    is_battle_only: int
    is_mega: int
    form_order: int
    order: int
    pfile: Optional[PFile]
    evoinfo: Optional[EvoInfo]
    evoline: Optional[list] = field(default_factory=list)

    def can_evolve(self):
        return any(
            self.pokemon_id == maybe_evolve_to["evolves_from_species_id"]
            for maybe_evolve_to in self.evoline
        )
