"""Shared geometry, measurement helpers, and layout errors for the PDF form."""

from dataclasses import dataclass
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from ..declarations import DeclarationLine

PAGE_WIDTH, PAGE_HEIGHT = letter

TITLE_TEXT = "SHIPPER'S DECLARATION FOR DANGEROUS GOODS"
BOX_X_PADDING = 4
BOX_Y_PADDING = 2
TEXT_COLUMN_PADDING = 3


@dataclass(frozen=True)
class ColumnLayout:
    """The single source of truth for all seven declaration columns."""

    un: float = 0.75 / 9
    proper_shipping_name: float = 2.25 / 9
    hazard_class: float = 1 / 9
    packing_group: float = 0.75 / 9
    packing_description: float = 3.15 / 9
    packing_instruction: float = 0.6 / 9
    authorization: float = 0.5 / 9

    @property
    def fractions(self) -> tuple[float, ...]:
        return (
            self.un,
            self.proper_shipping_name,
            self.hazard_class,
            self.packing_group,
            self.packing_description,
            self.packing_instruction,
            self.authorization,
        )

    def widths(self, total_width: float) -> list[float]:
        return [total_width * fraction for fraction in self.fractions]


COLUMNS = ColumnLayout()


def measure_paragraph(text: str, style: ParagraphStyle, width: float):
    """Measure trusted template markup such as explicit ``<br/>`` tags."""

    paragraph = Paragraph(text, style)
    _, height = paragraph.wrap(width, 10_000)
    return paragraph, height


def value_paragraph(value: object, style: ParagraphStyle) -> Paragraph:
    """Create a paragraph with safe values and explicit newline breaks."""

    escaped_value = escape(str(value)).replace("\n", "<br/>")
    return Paragraph(escaped_value, style)


def measure_value(value: object, style: ParagraphStyle, width: float):
    paragraph = value_paragraph(value, style)
    _, height = paragraph.wrap(width, 10_000)
    return paragraph, height


def hazard_text(line: DeclarationLine) -> str:
    if not line.subsidiary_hazards:
        return line.class_or_division
    wrapped = " ".join(f"({hazard})" for hazard in line.subsidiary_hazards)
    return f"{line.class_or_division} {wrapped}"


class DocumentLayoutError(Exception):
    """Base class for dangerous goods declaration layout errors."""


class BoxOverflowError(DocumentLayoutError):
    """Raised when the contents of a fixed-size box exceed its available space."""

    def __init__(
        self,
        message: str | None = None,
        *,
        box_name: str | None = None,
        required: float | None = None,
        available: float | None = None,
    ):
        if message is None:
            if box_name is None or required is None or available is None:
                message = "Box overflowed."
            else:
                message = (
                    f"'{box_name}' overflowed: required {required:.1f} pts, "
                    f"available {available:.1f} pts."
                )

        super().__init__(message)
        self.box_name = box_name
        self.required = required
        self.available = available


class FieldWrapError(DocumentLayoutError):
    """Raised when a field that must remain on one line wraps onto multiple lines."""

    def __init__(
        self,
        message: str | None = None,
        *,
        field_name: str | None = None,
        value: str | None = None,
    ):
        if message is None:
            if field_name is not None:
                message = f'The "{field_name}" field wrapped onto multiple lines.'
            else:
                message = "A field wrapped onto multiple lines."

        super().__init__(message)
        self.field_name = field_name
        self.value = value


@dataclass(frozen=True)
class HeaderLayout:
    """Vertical coordinates for the fixed header bands on every page."""

    title_top: float
    title_height: float
    shipper_row_top: float
    shipper_row_bottom: float
    consignee_row_top: float
    consignee_row_bottom: float
    transport_row_top: float
    transport_row_bottom: float
    column_header_row_top: float
    column_header_row_bottom: float
    total_height: float
