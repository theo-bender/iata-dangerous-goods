from datetime import date
from dataclasses import replace
from decimal import Decimal
import unittest

from dg.declarations import build_declaration
from dg.models import (
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
from dg.packagings import PackagingDefinition
from dg.regulations import (
    DangerousGoodsDefinition,
    RegulatoryEdition,
    RuleAvailability,
    SectionDeterminationMethod,
    TransportRule,
)
from dg.validation import validate_shipment


EDITION = RegulatoryEdition(
    edition=999,
    effective_from=date(2026, 1, 1),
    effective_through=date(2026, 12, 31),
    addendum="test fixture only",
    verified_on=date(2026, 7, 9),
    source_references=("test fixture—not regulatory data",),
)

TEST_PACKAGING = PackagingDefinition(
    code="approved_box",
    display_name="Approved test box",
    outer_packaging="Test box",
    inner_packaging="Test receptacle",
    protective_materials=(),
    description="Fictional packaging used only by the test suite.",
    dgd_packaging_description="Fibreboard Box",
)

DEFINITION = DangerousGoodsDefinition(
    un_number=9999,
    proper_shipping_name="TEST MATERIAL",
    primary_hazard=HazardClass.CLASS_3,
    packing_group=PackingGroup.II,
    unit=UnitOfMeasurement.LITER,
    edition=EDITION,
    rules=(
        TransportRule(
            mode=TransportMode.LIMITED_QUANTITY,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="Y999",
            max_inner_quantity=Decimal("1"),
            max_package_quantity=Decimal("5"),
            permitted_packagings=(TEST_PACKAGING,),
            declaration_required=False,
        ),
        TransportRule(
            mode=TransportMode.PASSENGER_AND_CARGO,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="999",
            max_inner_quantity=Decimal("5"),
            max_package_quantity=Decimal("25"),
            permitted_packagings=(TEST_PACKAGING,),
            declaration_required=True,
        ),
        TransportRule(
            mode=TransportMode.CARGO_AIRCRAFT_ONLY,
            availability=RuleAvailability.FORBIDDEN,
        ),
    ),
)


def shipment(*, inner: str = "1", net: str = "4", **changes) -> Shipment:
    values = {
        "un_number": 9999,
        "packages": (
            Package(
                packaging=TEST_PACKAGING,
                description="fiberboard box",
                net_quantity=Decimal(net),
                inner_receptacles=(InnerReceptacle(Decimal(inner)),),
            ),
        ),
        "ship_date": date(2026, 7, 9),
    }
    values.update(changes)
    return Shipment(**values)


def battery_definition() -> DangerousGoodsDefinition:
    base_rule = DEFINITION.rule_for(TransportMode.PASSENGER_AND_CARGO)
    assert base_rule is not None
    return replace(
        DEFINITION,
        section_determination=(
            SectionDeterminationMethod.LITHIUM_ION_BATTERY_WATT_HOURS
        ),
        rules=(
            replace(
                base_rule,
                packing_instruction="966",
                packing_instruction_section=PackingInstructionSection.SECTION_I,
            ),
            replace(
                base_rule,
                packing_instruction="966",
                packing_instruction_section=PackingInstructionSection.SECTION_II,
                max_package_quantity=Decimal("5"),
                declaration_required=False,
            ),
        ),
    )


class ValidationTests(unittest.TestCase):
    def test_selects_first_valid_mode(self) -> None:
        report = validate_shipment(shipment(), {(9999, None): DEFINITION})

        self.assertTrue(report.is_valid)
        self.assertEqual(report.selected_rule.mode, TransportMode.LIMITED_QUANTITY)
        self.assertIs(
            report.aircraft_limitation,
            AircraftType.PASSENGER_AND_CARGO,
        )
        self.assertFalse(report.declaration_required)

    def test_package_exposes_stable_packaging_code(self) -> None:
        self.assertEqual(shipment().packages[0].packaging_code, "approved_box")

    def test_package_rejects_a_raw_packaging_code(self) -> None:
        with self.assertRaisesRegex(TypeError, "PackagingDefinition"):
            Package(
                packaging="approved_box",  # type: ignore[arg-type]
                net_quantity=Decimal("1"),
            )

    def test_falls_back_when_limited_quantity_is_exceeded(self) -> None:
        report = validate_shipment(shipment(net="6"), {(9999, None): DEFINITION})

        self.assertTrue(report.is_valid)
        self.assertEqual(report.selected_rule.mode, TransportMode.PASSENGER_AND_CARGO)
        self.assertIs(
            report.aircraft_limitation,
            AircraftType.PASSENGER_AND_CARGO,
        )
        self.assertTrue(report.declaration_required)

    def test_derives_cargo_aircraft_only_from_selected_rule(self) -> None:
        cargo_rule = TransportRule(
            mode=TransportMode.CARGO_AIRCRAFT_ONLY,
            availability=RuleAvailability.PERMITTED,
            packing_instruction="998",
            max_inner_quantity=Decimal("5"),
            max_package_quantity=Decimal("60"),
            permitted_packagings=(TEST_PACKAGING,),
            declaration_required=True,
        )
        definition = replace(
            DEFINITION,
            rules=DEFINITION.rules[:-1] + (cargo_rule,),
        )
        proposed = shipment(
            net="30",
            shipper=Party("Example Shipper", "1 Origin Way"),
            consignee=Party("Example Consignee", "2 Destination Road"),
        )

        report = validate_shipment(proposed, {(9999, None): definition})
        declaration = build_declaration(report)

        self.assertTrue(report.is_valid)
        self.assertEqual(
            report.selected_rule.mode,
            TransportMode.CARGO_AIRCRAFT_ONLY,
        )
        self.assertIs(report.aircraft_limitation, AircraftType.CARGO_ONLY)
        self.assertEqual(declaration.aircraft_limitation, "CARGO AIRCRAFT ONLY")

    def test_rejects_expired_regulatory_data(self) -> None:
        report = validate_shipment(
            shipment(ship_date=date(2027, 1, 1)),
            {(9999, None): DEFINITION},
        )

        self.assertFalse(report.is_valid)
        self.assertEqual(report.issues[0].code, "regulatory_edition_not_effective")

    def test_reports_unknown_un_number(self) -> None:
        report = validate_shipment(shipment(un_number=1234), {})

        self.assertFalse(report.is_valid)
        self.assertEqual(report.issues[0].code, "unknown_un_number")

    def test_builds_structured_declaration_for_required_mode(self) -> None:
        proposed = shipment(
            net="6",
            shipper=Party("Example Shipper", "1 Origin Way"),
            consignee=Party("Example Consignee", "2 Destination Road"),
        )
        report = validate_shipment(proposed, {(9999, None): DEFINITION})

        declaration = build_declaration(report)

        self.assertEqual(declaration.lines[0].un_number, "UN9999")
        self.assertEqual(declaration.lines[0].packing_instruction, "999")
        self.assertEqual(
            declaration.aircraft_limitation,
            "PASSENGER AND CARGO AIRCRAFT",
        )
        self.assertEqual(
            declaration.lines[0].quantity_and_type_of_packing,
            "1 Fibreboard Box, 6 L",
        )

    def test_rejects_declaration_for_exempt_mode(self) -> None:
        report = validate_shipment(shipment(), {(9999, None): DEFINITION})

        with self.assertRaisesRegex(ValueError, "does not require"):
            build_declaration(report)

    def test_rejects_declaration_without_controlled_packaging_wording(self) -> None:
        packaging = replace(TEST_PACKAGING, dgd_packaging_description=None)
        definition = replace(
            DEFINITION,
            rules=tuple(
                replace(rule, permitted_packagings=(packaging,))
                if rule.availability is RuleAvailability.PERMITTED
                else rule
                for rule in DEFINITION.rules
            ),
        )
        proposed = shipment(
            net="6",
            packages=(Package(packaging=packaging, net_quantity=Decimal("6")),),
            shipper=Party("Example Shipper", "1 Origin Way"),
            consignee=Party("Example Consignee", "2 Destination Road"),
        )
        report = validate_shipment(proposed, {(9999, None): definition})

        with self.assertRaisesRegex(ValueError, "verified DGD wording"):
            build_declaration(report)

    def test_requires_technical_name_for_marked_definition(self) -> None:
        definition = replace(DEFINITION, technical_name_required=True)

        report = validate_shipment(shipment(), {(9999, None): definition})

        self.assertFalse(report.is_valid)
        self.assertEqual(report.issues[0].code, "technical_name_required")

    def test_injects_multiple_technical_names_into_declaration(self) -> None:
        definition = replace(DEFINITION, technical_name_required=True)
        proposed = shipment(
            net="6",
            technical_names=(" chemical A ", "chemical B"),
            shipper=Party("Example Shipper", "1 Origin Way"),
            consignee=Party("Example Consignee", "2 Destination Road"),
        )
        report = validate_shipment(proposed, {(9999, None): definition})

        declaration = build_declaration(report)

        self.assertEqual(
            declaration.lines[0].proper_shipping_name,
            "TEST MATERIAL (chemical A, chemical B)",
        )

    def test_rejects_blank_technical_names(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot be blank"):
            shipment(technical_names=("",))

    def test_requires_variant_when_un_number_has_multiple_shipping_names(self) -> None:
        packed_with = replace(
            DEFINITION,
            proper_shipping_name="LITHIUM ION BATTERIES PACKED WITH EQUIPMENT",
            variant="packed_with_equipment",
        )
        contained_in = replace(
            DEFINITION,
            proper_shipping_name="LITHIUM ION BATTERIES CONTAINED IN EQUIPMENT",
            variant="contained_in_equipment",
        )
        definitions = {
            (9999, packed_with.variant): packed_with,
            (9999, contained_in.variant): contained_in,
        }

        report = validate_shipment(shipment(), definitions)

        self.assertFalse(report.is_valid)
        self.assertEqual(report.issues[0].code, "definition_variant_required")

    def test_resolves_selected_shipping_name_variant(self) -> None:
        packed_with = replace(
            DEFINITION,
            proper_shipping_name="LITHIUM ION BATTERIES PACKED WITH EQUIPMENT",
            variant="packed_with_equipment",
        )
        contained_in = replace(
            DEFINITION,
            proper_shipping_name="LITHIUM ION BATTERIES CONTAINED IN EQUIPMENT",
            variant="contained_in_equipment",
        )
        definitions = {
            (9999, packed_with.variant): packed_with,
            (9999, contained_in.variant): contained_in,
        }

        report = validate_shipment(
            shipment(definition_variant="contained_in_equipment"),
            definitions,
        )

        self.assertTrue(report.is_valid)
        self.assertIs(report.definition, contained_in)

    def test_requires_battery_ratings_to_determine_section(self) -> None:
        report = validate_shipment(
            shipment(requested_mode=TransportMode.PASSENGER_AND_CARGO),
            {(9999, None): battery_definition()},
        )

        self.assertFalse(report.is_valid)
        self.assertIn(
            "battery_details_required",
            {issue.code for issue in report.issues},
        )

    def test_rejects_non_battery_lithium_items(self) -> None:
        with self.assertRaisesRegex(TypeError, "LithiumIonBattery"):
            shipment(
                lithium_ion_batteries=("cell",),  # type: ignore[arg-type]
            )

    def test_batteries_at_100_wh_are_section_ii(self) -> None:
        report = validate_shipment(
            shipment(
                requested_mode=TransportMode.PASSENGER_AND_CARGO,
                lithium_ion_batteries=(LithiumIonBattery(Decimal("100")),),
            ),
            {(9999, None): battery_definition()},
        )

        self.assertTrue(report.is_valid)
        self.assertEqual(
            report.selected_rule.packing_instruction_section,
            PackingInstructionSection.SECTION_II,
        )
        self.assertFalse(report.declaration_required)

    def test_any_battery_over_100_wh_requires_section_i(self) -> None:
        report = validate_shipment(
            shipment(
                net="6",
                requested_mode=TransportMode.PASSENGER_AND_CARGO,
                lithium_ion_batteries=(
                    LithiumIonBattery(Decimal("80")),
                    LithiumIonBattery(Decimal("100.1")),
                ),
            ),
            {(9999, None): battery_definition()},
        )

        self.assertTrue(report.is_valid)
        self.assertEqual(
            report.selected_rule.packing_instruction_section,
            PackingInstructionSection.SECTION_I,
        )
        self.assertTrue(report.declaration_required)

    def test_battery_report_contains_indicated_level_warning(self) -> None:
        report = validate_shipment(
            shipment(
                requested_mode=TransportMode.PASSENGER_AND_CARGO,
                lithium_ion_batteries=(LithiumIonBattery(Decimal("50")),),
            ),
            {(9999, None): battery_definition()},
        )

        self.assertTrue(report.is_valid)
        self.assertIn(
            "battery_level_below_25_percent",
            {issue.code for issue in report.issues},
        )


if __name__ == "__main__":
    unittest.main()
