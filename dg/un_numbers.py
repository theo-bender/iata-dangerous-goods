"""The deliberately small, manually verified UN-number registry.

Add the three definitions here after transcribing and independently checking
the current IATA DGR table entries, packing instructions, and addenda.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from .models import (
    HazardClass,
    PackingGroup,
    TransportMode,
    UnitOfMeasurement,
    PackingInstructionSection
)
from .packagings import BOTTLE_OR_CARTRIDGE_IN_ABSORBENT_MAT_AND_BAG, PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE, EQUIPMENT_IN_HARD_SHELL_CASE_WITH_FOAM
from .regulations import (
    DangerousGoodsDefinition,
    RegulatoryEdition,
    RuleAvailability,
    TransportRule,
    SectionDeterminationMethod
)

#Register the edition of the IATA DGR the DG data was pulled from
DGR_66_2025 = RegulatoryEdition( #Previous year's DGR
    edition=66,
    effective_from=date(2025, 1, 1),
    effective_through=date(2025, 12, 31),
    addendum="Addendum 1",
    verified_on=date(2026, 7, 9),
    source_references=(
        "IATA DGR 66th ed., Table 4.2, UN____",
        "IATA DGR 66th ed., Packing Instruction ____",
    ),
)

DGR_67_2026 = RegulatoryEdition( #Current DGR
    edition=67,
    effective_from=date(2026, 1, 1),
    effective_through=date(2026, 12, 31),
    addendum="Addendum 1",
    verified_on=date(2026, 7, 9),
    source_references=(
        "IATA DGR 67th ed., Table 4.2, UN____",
        "IATA DGR 67th ed., Packing Instruction ____",
    ),
)

UN_3266 = DangerousGoodsDefinition(
    un_number=3266,
    proper_shipping_name="Corrosive liquid, basic, inorganic, n.o.s.",
    primary_hazard=HazardClass.CLASS_8,
    subsidiary_hazards=(),
    packing_group=PackingGroup.III,
    unit=UnitOfMeasurement.LITER,
    edition=DGR_67_2026,
    technical_name_required=True,
    special_provisions=("A3","A803"),
    rules=(
        TransportRule(
            mode=TransportMode.DE_MINIMIS,
            availability=RuleAvailability.PERMITTED,
            max_inner_quantity=Decimal("0.001"),
            max_package_quantity=Decimal("0.1"),
            permitted_packagings=(BOTTLE_OR_CARTRIDGE_IN_ABSORBENT_MAT_AND_BAG,),
            declaration_required=False,
        ),
        TransportRule(
            mode=TransportMode.EXCEPTED_QUANTITY,
            availability=RuleAvailability.PERMITTED,
            excepted_quantity_code="E1",
            max_inner_quantity=Decimal("0.03"),
            max_package_quantity=Decimal("1"),
            permitted_packagings=(BOTTLE_OR_CARTRIDGE_IN_ABSORBENT_MAT_AND_BAG,),
            declaration_required=False,
        ),
        TransportRule(
            mode=TransportMode.LIMITED_QUANTITY,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="Y841",
            max_inner_quantity=Decimal("0.5"),
            max_package_quantity=Decimal("1"),
            permitted_packagings=(BOTTLE_OR_CARTRIDGE_IN_ABSORBENT_MAT_AND_BAG,),
            declaration_required=True,
        ),
        TransportRule(
            mode=TransportMode.PASSENGER_AND_CARGO,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="852",
            max_inner_quantity=Decimal("2.5"),
            max_package_quantity=Decimal("5"),
            permitted_packagings=(PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE,),
            declaration_required=True,
        ),
        TransportRule(
            mode=TransportMode.CARGO_AIRCRAFT_ONLY,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="856",
            max_inner_quantity=Decimal("5"),
            max_package_quantity=Decimal("60"),
            permitted_packagings=(PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE,),
            declaration_required=True,
        ),
    ),
)

UN_3316 = DangerousGoodsDefinition(
    un_number=3316,
    proper_shipping_name="Chemical kit",
    primary_hazard=HazardClass.CLASS_9,
    subsidiary_hazards=(),
    packing_group=PackingGroup.II,
    unit=UnitOfMeasurement.KILOGRAM,
    edition=DGR_67_2026,
    technical_name_required=False,
    special_provisions=("A44","A163"),
    rules=(
        TransportRule(
            mode=TransportMode.DE_MINIMIS,
            availability=RuleAvailability.FORBIDDEN,
        ),
        TransportRule(
            mode=TransportMode.EXCEPTED_QUANTITY,
            availability=RuleAvailability.PERMITTED,
            excepted_quantity_code="E2",
            max_inner_quantity=Decimal("0.03"),
            max_package_quantity=Decimal("1"),
            permitted_packagings=(BOTTLE_OR_CARTRIDGE_IN_ABSORBENT_MAT_AND_BAG,),
            declaration_required=False,
        ),
        TransportRule(
            mode=TransportMode.LIMITED_QUANTITY,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="Y960",
            max_inner_quantity=Decimal("0.1"),
            max_package_quantity=Decimal("1"),
            permitted_packagings=(BOTTLE_OR_CARTRIDGE_IN_ABSORBENT_MAT_AND_BAG,),
            declaration_required=True,
        ),
        TransportRule(
            mode=TransportMode.PASSENGER_AND_CARGO,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="960",
            max_inner_quantity=Decimal("0.25"),
            max_package_quantity=Decimal("10"),
            permitted_packagings=(PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE,),
            declaration_required=True,
        ),
        TransportRule(
            mode=TransportMode.CARGO_AIRCRAFT_ONLY,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="960",
            max_inner_quantity=Decimal("0.25"),
            max_package_quantity=Decimal("10"),
            permitted_packagings=(PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE,),
            declaration_required=True,
        ),
    ),
)

UN_3481_CONTAINED_IN_EQUIPMENT = DangerousGoodsDefinition(
    un_number=3481,
    variant="contained_in_equipment",
    proper_shipping_name="Lithium ion batteries contained in equipment",
    primary_hazard=HazardClass.CLASS_9,
    subsidiary_hazards=(),
    packing_group=None,
    unit=UnitOfMeasurement.KILOGRAM,
    edition=DGR_67_2026,
    technical_name_required=False,
    section_determination=(
        SectionDeterminationMethod.LITHIUM_ION_BATTERY_WATT_HOURS
    ),
    special_provisions=(),

    rules=(
        # PI 967, Section I — passenger and cargo aircraft
        TransportRule(
            mode=TransportMode.PASSENGER_AND_CARGO,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="967",
            packing_instruction_section=(
                PackingInstructionSection.SECTION_I
            ),
            max_inner_quantity=None,
            max_package_quantity=Decimal("5"),
            permitted_packagings=(
                EQUIPMENT_IN_HARD_SHELL_CASE_WITH_FOAM,
            ),
            declaration_required=True,
        ),

        # PI 967, Section I — cargo aircraft only
        TransportRule(
            mode=TransportMode.CARGO_AIRCRAFT_ONLY,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="967",
            packing_instruction_section=(
                PackingInstructionSection.SECTION_I
            ),
            max_inner_quantity=None,
            max_package_quantity=Decimal("35"),
            permitted_packagings=(
                EQUIPMENT_IN_HARD_SHELL_CASE_WITH_FOAM,
            ),
            declaration_required=True,
        ),

        # PI 967, Section II — passenger and cargo aircraft
        TransportRule(
            mode=TransportMode.PASSENGER_AND_CARGO,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="967",
            packing_instruction_section=(
                PackingInstructionSection.SECTION_II
            ),
            max_inner_quantity=None,
            max_package_quantity=Decimal("5"),
            permitted_packagings=(
                EQUIPMENT_IN_HARD_SHELL_CASE_WITH_FOAM,
            ),
            declaration_required=False,
        ),

        # PI 967, Section II — cargo aircraft only
        TransportRule(
            mode=TransportMode.CARGO_AIRCRAFT_ONLY,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="967",
            packing_instruction_section=(
                PackingInstructionSection.SECTION_II
            ),
            max_inner_quantity=None,
            max_package_quantity=Decimal("5"),
            permitted_packagings=(
                EQUIPMENT_IN_HARD_SHELL_CASE_WITH_FOAM,
            ),
            declaration_required=False,
        ),
    ),
)


UN_3481_PACKED_WITH_EQUIPMENT = DangerousGoodsDefinition(
    un_number=3481,
    variant="paxked_with_equipment",
    proper_shipping_name="Lithium ion batteries packed with equipment",
    primary_hazard=HazardClass.CLASS_9,
    subsidiary_hazards=(),
    packing_group=None,
    unit=UnitOfMeasurement.KILOGRAM,
    edition=DGR_67_2026,
    technical_name_required=False,
    section_determination=(
        SectionDeterminationMethod.LITHIUM_ION_BATTERY_WATT_HOURS
    ),
    special_provisions=(),

    rules=(
        # PI 967, Section I — passenger and cargo aircraft
        TransportRule(
            mode=TransportMode.PASSENGER_AND_CARGO,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="966",
            packing_instruction_section=(
                PackingInstructionSection.SECTION_I
            ),
            max_inner_quantity=None,
            max_package_quantity=Decimal("5"),
            permitted_packagings=(
                EQUIPMENT_IN_HARD_SHELL_CASE_WITH_FOAM,
            ),
            declaration_required=True,
        ),

        # PI 967, Section I — cargo aircraft only
        TransportRule(
            mode=TransportMode.CARGO_AIRCRAFT_ONLY,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="966",
            packing_instruction_section=(
                PackingInstructionSection.SECTION_I
            ),
            max_inner_quantity=None,
            max_package_quantity=Decimal("35"),
            permitted_packagings=(
                EQUIPMENT_IN_HARD_SHELL_CASE_WITH_FOAM,
            ),
            declaration_required=True,
        ),

        # PI 967, Section II — passenger and cargo aircraft
        TransportRule(
            mode=TransportMode.PASSENGER_AND_CARGO,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="966",
            packing_instruction_section=(
                PackingInstructionSection.SECTION_II
            ),
            max_inner_quantity=None,
            max_package_quantity=Decimal("5"),
            permitted_packagings=(
                EQUIPMENT_IN_HARD_SHELL_CASE_WITH_FOAM,
            ),
            declaration_required=False,
        ),

        # PI 967, Section II — cargo aircraft only
        TransportRule(
            mode=TransportMode.CARGO_AIRCRAFT_ONLY,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="966",
            packing_instruction_section=(
                PackingInstructionSection.SECTION_II
            ),
            max_inner_quantity=None,
            max_package_quantity=Decimal("5"),
            permitted_packagings=(
                EQUIPMENT_IN_HARD_SHELL_CASE_WITH_FOAM,
            ),
            declaration_required=False,
        ),
    ),
)

DefinitionKey = tuple[int, str | None]


UN_DEFINITIONS: dict[DefinitionKey, DangerousGoodsDefinition] = {}


def register(definition: DangerousGoodsDefinition) -> None:
    """Register one definition while preventing accidental replacement."""

    key = (definition.un_number, definition.variant)
    if key in UN_DEFINITIONS:
        suffix = f"/{definition.variant}" if definition.variant else ""
        raise ValueError(
            f"UN{definition.un_number:04d}{suffix} is already registered"
        )
    UN_DEFINITIONS[key] = definition


def get_definition(
    un_number: int,
    variant: str | None = None,
) -> DangerousGoodsDefinition | None:
    return UN_DEFINITIONS.get((un_number, variant))


def get_definitions(un_number: int) -> tuple[DangerousGoodsDefinition, ...]:
    """Return every proper-shipping-name variant for one UN number."""

    return tuple(
        definition
        for (registered_un_number, _), definition in UN_DEFINITIONS.items()
        if registered_un_number == un_number
    )


register(UN_3266)
register(UN_3316)
register(UN_3481_PACKED_WITH_EQUIPMENT)
register(UN_3481_CONTAINED_IN_EQUIPMENT)