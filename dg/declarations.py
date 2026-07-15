"""Build structured Shipper's Declaration data from a valid report.

PDF rendering is intentionally separate so an invalid shipment cannot produce
an apparently complete declaration.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import AircraftType, Party
from .validation import ValidationReport


@dataclass(frozen=True)
class DeclarationLine:
    un_number: str
    proper_shipping_name: str
    class_or_division: str
    subsidiary_hazards: tuple[str, ...]
    packing_group: str | None
    quantity_and_type_of_packing: str
    packing_instruction: str
    authorization: str = ""


@dataclass(frozen=True)
class DeclarationData:
    shipper: Party
    consignee: Party
    air_waybill_number: str | None
    aircraft_limitation: str
    departure_airport: str | None
    destination_airport: str | None
    lines: tuple[DeclarationLine, ...]
    additional_handling_information: str


def build_declaration(report: ValidationReport) -> DeclarationData:
    """Build declaration fields, rejecting invalid or exempt shipments."""

    if not report.is_valid or report.definition is None or report.selected_rule is None:
        raise ValueError("A declaration can only be built from a valid report")
    if not report.declaration_required:
        raise ValueError("The selected transport rule does not require a declaration")

    shipment = report.shipment
    if shipment.shipper is None or shipment.consignee is None:
        raise ValueError("Shipper and consignee are required for a declaration")
    if not report.selected_rule.packing_instruction:
        raise ValueError("A packing instruction is required for a declaration")

    definition = report.definition
    package_descriptions = []
    for package in shipment.packages:
        description = package.packaging.dgd_packaging_description
        if description is None:
            raise ValueError(
                f"Packaging '{package.packaging.display_name}' does not have "
                "verified DGD wording"
            )
        package_descriptions.append(
            f"1 {description}, {package.net_quantity} {definition.unit.value}"
        )

    line = DeclarationLine(
        un_number=f"UN{definition.un_number:04d}",
        proper_shipping_name=definition.format_proper_shipping_name(
            shipment.technical_names
        ),
        class_or_division=definition.primary_hazard.value,
        subsidiary_hazards=tuple(
            hazard.value for hazard in definition.subsidiary_hazards
        ),
        packing_group=(
            definition.packing_group.value if definition.packing_group else None
        ),
        quantity_and_type_of_packing="; ".join(package_descriptions),
        packing_instruction=report.selected_rule.packing_instruction,
    )

    report_aircraft_limitation = report.aircraft_limitation
    if report_aircraft_limitation is None:
        raise ValueError("A declaration requires an aircraft limitation")
    aircraft_limitation = (
        "PASSENGER AND CARGO AIRCRAFT"
        if report_aircraft_limitation is AircraftType.PASSENGER_AND_CARGO
        else "CARGO AIRCRAFT ONLY"
    )
    return DeclarationData(
        shipper=shipment.shipper,
        consignee=shipment.consignee,
        air_waybill_number=shipment.air_waybill_number,
        aircraft_limitation=aircraft_limitation,
        departure_airport=shipment.departure_airport,
        destination_airport=shipment.destination_airport,
        lines=(line,),
        additional_handling_information=shipment.additional_handling_information,
    )
