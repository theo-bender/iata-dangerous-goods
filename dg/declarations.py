"""Build structured Shipper's Declaration data from a valid report.

PDF rendering is intentionally separate so an invalid shipment cannot produce
an apparently complete declaration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .models import AircraftType, Package, Party
from .regulations import DangerousGoodsDefinition, TransportRule
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
    shippers_reference: str | None
    aircraft_limitation: AircraftType
    is_radioactive: bool
    departure_airport: str | None
    destination_airport: str | None
    lines: tuple[DeclarationLine, ...]
    additional_handling_information: str
    signatory: str
    signatory_date: date


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
    lines: list[DeclarationLine] = []
    if shipment.packages:
        lines.append(
            _build_declaration_line(
                definition,
                report.selected_rule,
                shipment.technical_names,
                _format_packages(shipment.packages, definition),
            )
        )

    for overpack in shipment.overpacks:
        package_text = _format_packages(
            overpack.packages,
            definition,
            consolidate_identical=True,
        )
        parts = [package_text, "Overpack used"]
        if overpack.identifier is not None:
            parts.append(f"#{overpack.identifier}")
        total_quantity = sum(
            (package.net_quantity for package in overpack.packages),
            start=Decimal("0"),
        )
        parts.append(f"Net quantity {total_quantity} {definition.unit.value}")
        lines.append(
            _build_declaration_line(
                definition,
                report.selected_rule,
                shipment.technical_names,
                "\n".join(parts),
            )
        )

    aircraft_limitation = report.aircraft_limitation
    if aircraft_limitation is None:
        raise ValueError("A declaration requires an aircraft limitation")
    is_radioactive = report.is_radioactive

    return DeclarationData(
        shipper=shipment.shipper,
        consignee=shipment.consignee,
        air_waybill_number=shipment.air_waybill_number,
        shippers_reference=shipment.shippers_reference,
        aircraft_limitation=aircraft_limitation,
        is_radioactive=is_radioactive,
        departure_airport=shipment.departure_airport,
        destination_airport=shipment.destination_airport,
        lines=tuple(lines),
        additional_handling_information=shipment.additional_handling_information,
        signatory=shipment.signatory,
        signatory_date=shipment.ship_date,
    )


def _format_packages(
    packages: tuple[Package, ...],
    definition: DangerousGoodsDefinition,
    *,
    consolidate_identical: bool = False,
) -> str:
    package_details = []
    for package in packages:
        description = package.packaging.dgd_packaging_description
        if description is None:
            raise ValueError(
                f"Packaging '{package.packaging.display_name}' does not have "
                "verified DGD wording"
            )
        package_details.append((description, package.net_quantity))

    if not consolidate_identical:
        return "; ".join(
            f"1 {description} x {quantity} {definition.unit.value}"
            for description, quantity in package_details
        )

    grouped_packages: dict[tuple[str, Decimal], int] = {}
    for package_detail in package_details:
        grouped_packages[package_detail] = grouped_packages.get(package_detail, 0) + 1

    descriptions = []
    for (description, quantity), count in grouped_packages.items():
        packaging_description = (
            _pluralize_packaging_description(description)
            if count > 1
            else description
        )
        descriptions.append(
            f"{count} {packaging_description} x "
            f"{quantity} {definition.unit.value}"
        )
    return "\n".join(descriptions)


def _pluralize_packaging_description(description: str) -> str:
    """Pluralize the final word in a controlled DGD packaging description."""

    words = description.split()
    final_word = words[-1]
    lower_word = final_word.lower()
    if lower_word.endswith(("s", "x", "z", "ch", "sh")):
        plural = f"{final_word}es"
    elif (
        lower_word.endswith("y")
        and len(final_word) > 1
        and lower_word[-2] not in "aeiou"
    ):
        plural = f"{final_word[:-1]}ies"
    else:
        plural = f"{final_word}s"
    return " ".join((*words[:-1], plural))


def _build_declaration_line(
    definition: DangerousGoodsDefinition,
    rule: TransportRule,
    technical_names: tuple[str, ...],
    quantity_and_type_of_packing: str,
) -> DeclarationLine:
    return DeclarationLine(
        un_number=f"UN{definition.un_number:04d}",
        proper_shipping_name=definition.format_proper_shipping_name(
            technical_names
        ),
        class_or_division=definition.primary_hazard.value,
        subsidiary_hazards=tuple(
            hazard.value for hazard in definition.subsidiary_hazards
        ),
        packing_group=(
            definition.packing_group.value if definition.packing_group else None
        ),
        quantity_and_type_of_packing=quantity_and_type_of_packing,
        packing_instruction=rule.packing_instruction or "",
    )
