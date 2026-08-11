"""Explicit ReportLab styles used by the declaration form."""

from dataclasses import dataclass

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet


@dataclass(frozen=True)
class DeclarationStyles:
    header_title: ParagraphStyle
    box_title: ParagraphStyle
    address_text: ParagraphStyle
    header_text: ParagraphStyle
    italic_text: ParagraphStyle
    enum: ParagraphStyle
    centered_subhead: ParagraphStyle
    centered_colhead: ParagraphStyle
    table_center: ParagraphStyle
    table_left: ParagraphStyle


def create_declaration_styles() -> DeclarationStyles:
    """Create styles without relying on mutable renderer-wide defaults."""

    sample_styles = getSampleStyleSheet()
    header_title = ParagraphStyle(
        "Helvetica12Bold",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=0,
        textColor=colors.black,
    )
    box_title = ParagraphStyle(
        "BoxTitle",
        parent=sample_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=9,
        textColor=colors.black,
    )
    address_text = ParagraphStyle(
        "AddressBoxText",
        parent=sample_styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=9,
        textColor=colors.black,
    )
    header_text = ParagraphStyle(
        "HeaderBoxText",
        parent=sample_styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=11,
        textColor=colors.black,
    )
    italic_text = ParagraphStyle(
        "ItalicBody",
        parent=sample_styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=6,
        leading=8,
        textColor=colors.black,
    )
    enum = ParagraphStyle(
        "EnumBody",
        parent=sample_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=8,
        textColor=colors.black,
        alignment=TA_CENTER,
    )
    centered_subhead = ParagraphStyle(
        "CenteredSubhead",
        parent=sample_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=11,
        textColor=colors.black,
        alignment=TA_CENTER,
    )
    centered_colhead = ParagraphStyle(
        "CenteredColhead",
        parent=sample_styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=9,
        textColor=colors.black,
        alignment=TA_CENTER,
    )
    table_center = ParagraphStyle(
        "TableCenter",
        fontName="Courier",
        parent=address_text,
        alignment=TA_CENTER,
    )
    table_left = ParagraphStyle(
        "TableLeft",
        fontName="Courier",
        parent=address_text,
        alignment=TA_LEFT,
    )
    return DeclarationStyles(
        header_title=header_title,
        box_title=box_title,
        address_text=address_text,
        header_text=header_text,
        italic_text=italic_text,
        enum=enum,
        centered_subhead=centered_subhead,
        centered_colhead=centered_colhead,
        table_center=table_center,
        table_left=table_left,
    )
