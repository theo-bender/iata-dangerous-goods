from __future__ import annotations

import hashlib
import re
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

from reportlab.lib.styles import getSampleStyleSheet

from dg import (
    InnerReceptacle,
    Overpack,
    Package,
    Party,
    PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE,
    Shipment,
    build_declaration,
    validate_shipment,
)
from dg.dangerous_goods_declaration import (
    BoxOverflowError,
    COLUMNS,
    DangerousGoodsDeclaration,
    FieldWrapError,
    _value_paragraph,
)


EXPECTED_NORMALIZED_PDF_SHA256 = (
    "d34929464ff8089d1f35b658a477fa77cff6715198f7902224d73c525af801ce"
)


def _example_declaration(*, overpacked: bool = False):
    package = Package(
        packaging=PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE,
        net_quantity=Decimal("1"),
        inner_receptacles=(InnerReceptacle(quantity=Decimal("1")),),
    )
    shipment = Shipment(
        un_number=3266,
        packages=() if overpacked else (package,),
        overpacks=(
            (
                Overpack(packages=(package,), identifier="OP-1"),
                Overpack(packages=(package,), identifier="OP-2"),
            )
            if overpacked
            else ()
        ),
        ship_date=date(2026, 7, 31),
        technical_names=("tripotassium phosphate",),
        shipper=Party(
            name="Example Shipper",
            business="Example Business",
            address=["123 Shipping Street", "STE 150", "Seattle, WA 98101", "USA"],
        ),
        consignee=Party(
            name="Example Consignee",
            address=["456 Receiving Road", "Portland, OR 97201", "USA"],
        ),
        air_waybill_number="123-12345678",
        shippers_reference="1234",
        departure_airport="SEA",
        destination_airport="PDX",
        signatory="Person Signing",
        additional_handling_information="Emergency contact: +1 555 555 0100",
    )

    report = validate_shipment(shipment)
    if not report.is_valid:
        raise AssertionError(report.issues)
    return build_declaration(report)


def _normalized_pdf_hash(path: Path) -> str:
    pdf = path.read_bytes()
    pdf = re.sub(rb"/CreationDate \([^)]*\)", b"/CreationDate ()", pdf)
    pdf = re.sub(rb"/ModDate \([^)]*\)", b"/ModDate ()", pdf)
    pdf = re.sub(rb"/ID\s*\[[^]]*\]", b"/ID []", pdf)
    return hashlib.sha256(pdf).hexdigest()


class DangerousGoodsDeclarationTests(unittest.TestCase):
    def test_direct_import_path_remains_compatible(self) -> None:
        from dg import DangerousGoodsDeclaration as PublicRenderer

        self.assertIs(PublicRenderer, DangerousGoodsDeclaration)

    def test_example_pdf_matches_established_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "dgd.pdf"
            pdf = DangerousGoodsDeclaration(_example_declaration()).build(str(output))

            self.assertEqual(output.read_bytes(), pdf)
            self.assertEqual(
                _normalized_pdf_hash(output),
                EXPECTED_NORMALIZED_PDF_SHA256,
            )

    def test_build_returns_pdf_bytes_without_a_filename(self) -> None:
        renderer = DangerousGoodsDeclaration(_example_declaration())

        pdf = renderer.build()

        self.assertIsInstance(pdf, bytes)
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertIsNone(renderer.filename)

    def test_builds_pdf_with_multiple_overpack_lines(self) -> None:
        declaration = _example_declaration(overpacked=True)

        self.assertEqual(len(declaration.lines), 2)
        pdf = DangerousGoodsDeclaration(declaration).build()

        self.assertTrue(pdf.startswith(b"%PDF-"))

    def test_dynamic_text_is_not_interpreted_as_reportlab_markup(self) -> None:
        value = "A <b>& B</b>"
        paragraph = _value_paragraph(value, getSampleStyleSheet()["Normal"])

        self.assertEqual(paragraph.getPlainText(), value)

    def test_dynamic_text_newlines_create_explicit_line_breaks(self) -> None:
        paragraph = _value_paragraph(
            "Overpack used\n#OP-1",
            getSampleStyleSheet()["Normal"],
        )

        self.assertEqual(
            paragraph.text,
            "Overpack used<br/>#OP-1",
        )

    def test_markup_like_values_can_be_rendered_as_literal_text(self) -> None:
        marker = "<not-a-reportlab-tag>"
        declaration = _example_declaration()
        declaration = replace(
            declaration,
            shipper=Party(name=marker, business=marker, address=[marker]),
            consignee=Party(name=marker, business=marker, address=[marker]),
            air_waybill_number=marker,
            shippers_reference=marker,
            departure_airport=marker,
            destination_airport=marker,
            lines=(
                replace(
                    declaration.lines[0],
                    un_number=marker,
                    proper_shipping_name=marker,
                    class_or_division=marker,
                    subsidiary_hazards=(marker,),
                    packing_group=marker,
                    quantity_and_type_of_packing=marker,
                    packing_instruction=marker,
                    authorization=marker,
                ),
            ),
            additional_handling_information=marker,
            signatory=marker,
        )

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "special-characters.pdf"
            DangerousGoodsDeclaration(declaration).build(str(output))

            self.assertTrue(output.is_file())

    def test_column_layout_fills_the_declaration_width(self) -> None:
        self.assertAlmostEqual(sum(COLUMNS.fractions), 1.0)

    def test_build_rejects_non_pdf_filename(self) -> None:
        renderer = DangerousGoodsDeclaration(_example_declaration())

        with self.assertRaisesRegex(ValueError, "must end with .pdf"):
            renderer.build("declaration.txt")

    def test_address_overflow_identifies_the_box(self) -> None:
        declaration = _example_declaration()
        declaration = replace(
            declaration,
            shipper=replace(
                declaration.shipper,
                address=[f"Address line {number}" for number in range(20)],
            ),
        )

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "overflow.pdf"
            with self.assertRaises(BoxOverflowError) as raised:
                DangerousGoodsDeclaration(declaration).build(str(output))

        self.assertIn("'Shipper' overflowed", str(raised.exception))

    def test_waybill_wrap_identifies_the_field(self) -> None:
        declaration = replace(
            _example_declaration(),
            air_waybill_number="WAYBILL-" * 30,
        )

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "wrapped.pdf"
            with self.assertRaises(FieldWrapError) as raised:
                DangerousGoodsDeclaration(declaration).build(str(output))

        self.assertIn('"Air Waybill Number" field', str(raised.exception))


if __name__ == "__main__":
    unittest.main()
