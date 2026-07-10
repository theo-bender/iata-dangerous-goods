"""Versioned regulatory definitions transcribed from an authorized DGR copy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from .models import (
    HazardClass,
    PackingGroup,
    PackingInstructionSection,
    TransportMode,
    UnitOfMeasurement,
)
from .packagings import PackagingDefinition


class RuleAvailability(Enum):
    PERMITTED = "permitted"
    FORBIDDEN = "forbidden"


class SectionDeterminationMethod(Enum):
    LITHIUM_ION_BATTERY_WATT_HOURS = "lithium_ion_battery_watt_hours"


@dataclass(frozen=True)
class RegulatoryEdition:
    edition: int
    effective_from: date
    effective_through: date
    addendum: str
    verified_on: date
    source_references: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.edition <= 0:
            raise ValueError("DGR edition must be positive")
        if self.effective_through < self.effective_from:
            raise ValueError("Regulatory effective date range is invalid")
        if not self.addendum.strip():
            raise ValueError("Record which addendum state was verified")
        if not self.source_references:
            raise ValueError("At least one DGR source reference is required")

    def is_effective_on(self, value: date) -> bool:
        return self.effective_from <= value <= self.effective_through


@dataclass(frozen=True)
class TransportRule:
    mode: TransportMode
    availability: RuleAvailability
    packing_instruction: str | None = None
    packing_instruction_section: PackingInstructionSection | None = None
    max_inner_quantity: Decimal | None = None
    max_package_quantity: Decimal | None = None
    permitted_packagings: tuple[PackagingDefinition, ...] = ()
    declaration_required: bool = False
    excepted_quantity_code: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if any(
            not isinstance(packaging, PackagingDefinition)
            for packaging in self.permitted_packagings
        ):
            raise TypeError(
                "TransportRule permitted_packagings must contain "
                "PackagingDefinition objects"
            )
        quantities = (self.max_inner_quantity, self.max_package_quantity)
        if any(value is not None and value <= 0 for value in quantities):
            raise ValueError("Regulatory quantity limits must be greater than zero")
        if self.availability is RuleAvailability.FORBIDDEN:
            if any(value is not None for value in quantities):
                raise ValueError("A forbidden rule must not carry quantity limits")
            if self.permitted_packagings:
                raise ValueError("A forbidden rule must not permit packaging")
        elif self.max_package_quantity is None:
            raise ValueError("A permitted rule requires a package quantity limit")
        packaging_codes = [packaging.code for packaging in self.permitted_packagings]
        if len(set(packaging_codes)) != len(packaging_codes):
            raise ValueError("A transport rule cannot contain duplicate packaging")
        if (
            self.mode is TransportMode.LIMITED_QUANTITY
            and self.packing_instruction
            and not self.packing_instruction.startswith("Y")
        ):
            raise ValueError("A limited-quantity packing instruction must start with Y")


@dataclass(frozen=True)
class DangerousGoodsDefinition:
    un_number: int
    proper_shipping_name: str
    primary_hazard: HazardClass
    unit: UnitOfMeasurement
    edition: RegulatoryEdition
    rules: tuple[TransportRule, ...]
    subsidiary_hazards: tuple[HazardClass, ...] = ()
    packing_group: PackingGroup | None = None
    variant: str | None = None
    section_determination: SectionDeterminationMethod | None = None
    technical_name_required: bool = False
    special_provisions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 1 <= self.un_number <= 9999:
            raise ValueError("UN number must be between 0001 and 9999")
        if not self.proper_shipping_name.strip():
            raise ValueError("Proper shipping name is required")
        if self.variant is not None and not self.variant.strip():
            raise ValueError("Definition variant cannot be blank")
        if not self.rules:
            raise ValueError("At least one transport rule is required")
        rule_keys = [
            (rule.mode, rule.packing_instruction_section) for rule in self.rules
        ]
        if len(set(rule_keys)) != len(rule_keys):
            raise ValueError(
                "A definition cannot contain duplicate transport mode/section rules"
            )
        if (
            self.section_determination
            is SectionDeterminationMethod.LITHIUM_ION_BATTERY_WATT_HOURS
        ):
            sections = {
                rule.packing_instruction_section for rule in self.rules
            }
            required_sections = {
                PackingInstructionSection.SECTION_I,
                PackingInstructionSection.SECTION_II,
            }
            if not required_sections.issubset(sections):
                raise ValueError(
                    "Battery Watt-hour section determination requires "
                    "Section I and Section II rules"
                )

    def rule_for(
        self,
        mode: TransportMode,
        section: PackingInstructionSection | None = None,
    ) -> TransportRule | None:
        return next(
            (
                rule
                for rule in self.rules
                if rule.mode is mode
                and rule.packing_instruction_section is section
            ),
            None,
        )

    def format_proper_shipping_name(self, technical_names: tuple[str, ...]) -> str:
        """Append shipment-specific technical names in DGD position."""

        if not technical_names:
            return self.proper_shipping_name
        return f"{self.proper_shipping_name} ({', '.join(technical_names)})"
