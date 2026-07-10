"""Small, versioned IATA dangerous-goods validation toolkit."""

from .declarations import DeclarationData, DeclarationLine, build_declaration
from .models import (
    AircraftType,
    HazardClass,
    InnerReceptacle,
    LithiumIonBattery,
    Package,
    PackingGroup,
    PackingInstructionSection,
    Party,
    Shipment,
    TransportMode,
    UnitOfMeasurement,
)
from .packagings import (
    BOTTLE_OR_CARTRIDGE_IN_ABSORBENT_MAT_AND_BAG,
    EQUIPMENT_IN_HARD_SHELL_CASE_WITH_FOAM,
    PACKAGING_DEFINITIONS,
    PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE,
    PackagingDefinition,
    get_packaging,
)
from .regulations import (
    DangerousGoodsDefinition,
    RegulatoryEdition,
    RuleAvailability,
    SectionDeterminationMethod,
    TransportRule,
)
from .validation import (
    Severity,
    ValidationIssue,
    ValidationReport,
    validate_shipment,
)

__all__ = [
    "AircraftType",
    "BOTTLE_OR_CARTRIDGE_IN_ABSORBENT_MAT_AND_BAG",
    "DangerousGoodsDefinition",
    "DeclarationData",
    "DeclarationLine",
    "HazardClass",
    "InnerReceptacle",
    "LithiumIonBattery",
    "EQUIPMENT_IN_HARD_SHELL_CASE_WITH_FOAM",
    "Package",
    "PACKAGING_DEFINITIONS",
    "PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE",
    "PackagingDefinition",
    "PackingGroup",
    "PackingInstructionSection",
    "Party",
    "RegulatoryEdition",
    "RuleAvailability",
    "SectionDeterminationMethod",
    "Severity",
    "Shipment",
    "TransportMode",
    "TransportRule",
    "UnitOfMeasurement",
    "ValidationIssue",
    "ValidationReport",
    "build_declaration",
    "get_packaging",
    "validate_shipment",
]
