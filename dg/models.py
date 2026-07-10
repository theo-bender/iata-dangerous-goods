"""Core domain models for dangerous-goods shipment validation.

This module intentionally contains no IATA limit data.  Regulatory facts live
in :mod:`dg.regulations`; actual shipment facts live here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum

from .packagings import PackagingDefinition


class HazardClass(Enum):
    """Hazard classes and divisions used by the IATA DGR."""

    DIV_1_1 = "1.1"
    DIV_1_2 = "1.2"
    DIV_1_3 = "1.3"
    DIV_1_4 = "1.4"
    DIV_1_5 = "1.5"
    DIV_1_6 = "1.6"
    DIV_2_1 = "2.1"
    DIV_2_2 = "2.2"
    DIV_2_3 = "2.3"
    CLASS_3 = "3"
    DIV_4_1 = "4.1"
    DIV_4_2 = "4.2"
    DIV_4_3 = "4.3"
    DIV_5_1 = "5.1"
    DIV_5_2 = "5.2"
    DIV_6_1 = "6.1"
    DIV_6_2 = "6.2"
    CLASS_7 = "7"
    CLASS_8 = "8"
    CLASS_9 = "9"


class PackingGroup(Enum):
    I = "I"
    II = "II"
    III = "III"


class UnitOfMeasurement(Enum):
    KILOGRAM = "kg"
    LITER = "L"
    WATT_HOUR = "Wh"


class AircraftType(Enum):
    PASSENGER_AND_CARGO = "passenger_and_cargo"
    CARGO_ONLY = "cargo_only"


class TransportMode(Enum):
    """Transport regimes, ordered from most restrictive relief to standard."""

    DE_MINIMIS = "de_minimis"
    EXCEPTED_QUANTITY = "excepted_quantity"
    LIMITED_QUANTITY = "limited_quantity"
    PASSENGER_AND_CARGO = "passenger_and_cargo"
    CARGO_AIRCRAFT_ONLY = "cargo_aircraft_only"


class PackingInstructionSection(Enum):
    """Sections used by packing instructions, including lithium batteries."""

    SECTION_I = "I"
    SECTION_IA = "IA"
    SECTION_IB = "IB"
    SECTION_II = "II"


@dataclass(frozen=True)
class InnerReceptacle:
    """One inner receptacle inside a completed package."""

    quantity: Decimal
    description: str = ""

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("Inner receptacle quantity must be greater than zero")


@dataclass(frozen=True)
class LithiumIonBattery:
    """One or more identical lithium-ion batteries; cells are not accepted."""

    watt_hour_rating: Decimal
    quantity: int = 1

    def __post_init__(self) -> None:
        if self.watt_hour_rating <= 0:
            raise ValueError("Battery Watt-hour rating must be greater than zero")
        if self.quantity <= 0:
            raise ValueError("Battery quantity must be greater than zero")


@dataclass(frozen=True)
class Package:
    """One completed package offered for transport.

    The packaging object is selected from the application catalog. Its stable
    code remains available through :attr:`packaging_code` for serialization.
    """

    packaging: PackagingDefinition
    net_quantity: Decimal
    inner_receptacles: tuple[InnerReceptacle, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.packaging, PackagingDefinition):
            raise TypeError("Package packaging must be a PackagingDefinition")
        if self.net_quantity <= 0:
            raise ValueError("Package net quantity must be greater than zero")

    @property
    def packaging_code(self) -> str:
        return self.packaging.code


@dataclass(frozen=True)
class Party:
    name: str
    address: str

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.address.strip():
            raise ValueError("Party name and address are required")


@dataclass(frozen=True)
class Shipment:
    """Facts about a proposed shipment, independent of regulatory limits."""

    un_number: int
    packages: tuple[Package, ...]
    aircraft_type: AircraftType
    ship_date: date
    definition_variant: str | None = None
    requested_mode: TransportMode | None = None
    packing_instruction_section: PackingInstructionSection | None = None
    lithium_ion_batteries: tuple[LithiumIonBattery, ...] = ()
    technical_names: tuple[str, ...] = ()
    shipper: Party | None = None
    consignee: Party | None = None
    air_waybill_number: str | None = None
    departure_airport: str | None = None
    destination_airport: str | None = None
    additional_handling_information: str = ""
    metadata: dict[str, str] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if not 1 <= self.un_number <= 9999:
            raise ValueError("UN number must be between 0001 and 9999")
        if not self.packages:
            raise ValueError("Shipment must contain at least one package")
        if self.definition_variant is not None:
            variant = self.definition_variant.strip()
            if not variant:
                raise ValueError("Definition variant cannot be blank")
            object.__setattr__(self, "definition_variant", variant)
        if any(
            not isinstance(battery, LithiumIonBattery)
            for battery in self.lithium_ion_batteries
        ):
            raise TypeError(
                "Shipment lithium_ion_batteries must contain LithiumIonBattery objects"
            )
        if any(not name.strip() for name in self.technical_names):
            raise ValueError("Technical names cannot be blank")
        object.__setattr__(
            self,
            "technical_names",
            tuple(name.strip() for name in self.technical_names),
        )

    @property
    def formatted_un_number(self) -> str:
        return f"UN{self.un_number:04d}"
