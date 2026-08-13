from __future__ import annotations

import hashlib
import re
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

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
from dg._pdf.page import HATCH_BAND_WIDTH


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


class _RecordingPath:
    def __init__(self):
        self.points = []
        self.closed = False

    def moveTo(self, x, y):
        self.points.append((x, y))

    def lineTo(self, x, y):
        self.points.append((x, y))

    def close(self):
        self.closed = True


class _RecordingCanvas:
    def __init__(self):
        self.saved_states = 0
        self.restored_states = 0
        self.fill_colors = []
        self.paths = []

    def saveState(self):
        self.saved_states += 1

    def restoreState(self):
        self.restored_states += 1

    def setFillColor(self, color):
        self.fill_colors.append(color)

    def beginPath(self):
        return _RecordingPath()

    def drawPath(self, path, *, stroke, fill):
        self.paths.append((path, stroke, fill))


class DangerousGoodsDeclarationTests(unittest.TestCase):
    def test_direct_import_path_remains_compatible(self) -> None:
        from dg import DangerousGoodsDeclaration as PublicRenderer

        self.assertIs(PublicRenderer, DangerousGoodsDeclaration)

    def test_build_returns_pdf_bytes_without_a_filename(self) -> None:
        renderer = DangerousGoodsDeclaration(_example_declaration())

        pdf = renderer.build()

        self.assertIsInstance(pdf, bytes)
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertIsNone(renderer.filename)

    def test_hatched_margins_default_to_disabled(self) -> None:
        renderer = DangerousGoodsDeclaration(_example_declaration())

        with patch.object(
            renderer,
            "draw_hatched_margins",
            wraps=renderer.draw_hatched_margins,
        ) as draw_hatched_margins:
            renderer.build()
            renderer.build(hatched_margins=False)

        draw_hatched_margins.assert_not_called()

    def test_hatched_margins_are_scoped_to_each_build(self) -> None:
        renderer = DangerousGoodsDeclaration(_example_declaration())

        with patch.object(
            renderer,
            "draw_hatched_margins",
            wraps=renderer.draw_hatched_margins,
        ) as draw_hatched_margins:
            renderer.build(hatched_margins=True)
            self.assertEqual(draw_hatched_margins.call_count, 1)

            draw_hatched_margins.reset_mock()
            renderer.build()

        draw_hatched_margins.assert_not_called()

    def test_hatched_margins_can_be_written_to_a_file(self) -> None:
        renderer = DangerousGoodsDeclaration(_example_declaration())

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "hatched.pdf"
            pdf = renderer.build(str(output), hatched_margins=True)

            self.assertEqual(output.read_bytes(), pdf)
            self.assertTrue(pdf.startswith(b"%PDF-"))

    def test_hatched_margins_are_drawn_on_every_page(self) -> None:
        declaration = _example_declaration()
        declaration = replace(declaration, lines=declaration.lines * 80)
        renderer = DangerousGoodsDeclaration(declaration)

        with (
            patch.object(
                renderer,
                "draw_hatched_margins",
                wraps=renderer.draw_hatched_margins,
            ) as draw_hatched_margins,
            patch.object(
                renderer,
                "draw_page",
                wraps=renderer.draw_page,
            ) as draw_page,
        ):
            pdf = renderer.build(hatched_margins=True)

        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreater(draw_page.call_count, 1)
        self.assertEqual(draw_hatched_margins.call_count, draw_page.call_count)

    def test_hatched_margin_geometry_uses_both_full_height_side_margins(self) -> None:
        renderer = DangerousGoodsDeclaration(_example_declaration())
        page_canvas = _RecordingCanvas()
        doc = SimpleNamespace(
            pagesize=letter,
            leftMargin=0.875 * inch,
            rightMargin=0.875 * inch,
        )

        renderer.draw_hatched_margins(page_canvas, doc)

        self.assertEqual(page_canvas.saved_states, 1)
        self.assertEqual(page_canvas.restored_states, 1)
        self.assertEqual(page_canvas.fill_colors, [colors.red])
        self.assertGreater(len(page_canvas.paths), 2)
        self.assertEqual(len(page_canvas.paths) % 2, 0)
        self.assertTrue(
            all(
                path.closed and stroke == 0 and fill == 1
                for path, stroke, fill in page_canvas.paths
            )
        )

        left_path = page_canvas.paths[0][0]
        right_path = page_canvas.paths[1][0]
        left_edge = min(x for x, _ in left_path.points)
        right_edge = max(x for x, _ in right_path.points)
        expected_outer_gap = (doc.leftMargin - HATCH_BAND_WIDTH) / 2
        self.assertAlmostEqual(left_edge, expected_outer_gap)
        self.assertAlmostEqual(letter[0] - right_edge, expected_outer_gap)

        all_y_coordinates = [
            y
            for path, _, _ in page_canvas.paths
            for _, y in path.points
        ]
        self.assertLess(min(all_y_coordinates), 0)
        self.assertGreater(max(all_y_coordinates), letter[1])

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
