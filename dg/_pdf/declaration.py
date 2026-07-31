from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Paragraph,
    Table,
    TableStyle,
)
from ..declarations import DeclarationData

from io import BytesIO
from pathlib import Path
from .canvas import DangerousGoodsCanvas
from .page import DeclarationPageRenderer
from .layout import (
    COLUMNS,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    TEXT_COLUMN_PADDING,
    TITLE_TEXT,
    BoxOverflowError,
    DocumentLayoutError,
    FieldWrapError,
    HeaderLayout,
    hazard_text as _hazard_text,
    value_paragraph as _value_paragraph,
)
from .styles import create_declaration_styles

class DangerousGoodsDeclaration(DeclarationPageRenderer):
    """Render a validated declaration data object as the established PDF form."""

    def __init__(self, declaration_data: DeclarationData):
        self.declaration_data = declaration_data

        styles = create_declaration_styles()
        self.header_title_style = styles.header_title
        self.box_title_style = styles.box_title
        self.address_text_style = styles.address_text
        self.header_text_style = styles.header_text
        self.italic_text_style = styles.italic_text
        self.enum_style = styles.enum
        self.centered_subhead_style = styles.centered_subhead
        self.centered_colhead_style = styles.centered_colhead
        self.table_center_style = styles.table_center
        self.table_left_style = styles.table_left

        self.page_size = letter
        self.left_margin = 0.875 * inch
        self.right_margin = 0.875 * inch

        document_width = (
            PAGE_WIDTH
            - self.left_margin
            - self.right_margin
        )
        layout = self.header_layout(document_width)

        self.top_margin = layout.total_height
        self.bottom_margin = 2.375 * inch

    def header_layout(self, doc_width: float) -> HeaderLayout:
        title_top = PAGE_HEIGHT - 0.5 * inch

        title = Paragraph(
            TITLE_TEXT,
            self.header_title_style,
        )
        _, title_height = title.wrap(doc_width, 1000)

        gap_below_title = 0

        shipper_row_height = 1 * inch
        consignee_row_height = 1 * inch
        transport_row_height = 2 * inch
        column_header_row_height = 1 * inch

        # ReportLab coordinates start at the bottom-left. Calculate each band
        # top-down so adjacent boxes share exactly the same boundary line.
        shipper_row_top = title_top - title_height - gap_below_title
        shipper_row_bottom = shipper_row_top - shipper_row_height

        consignee_row_top = shipper_row_bottom
        consignee_row_bottom = consignee_row_top - consignee_row_height

        transport_row_top = consignee_row_bottom
        transport_row_bottom = transport_row_top - transport_row_height

        column_header_row_top = transport_row_bottom
        column_header_row_bottom = (
            column_header_row_top - column_header_row_height
        )

        return HeaderLayout(
            title_top=title_top,
            title_height=title_height,
            shipper_row_top=shipper_row_top,
            shipper_row_bottom=shipper_row_bottom,
            consignee_row_top=consignee_row_top,
            consignee_row_bottom=consignee_row_bottom,
            transport_row_top=transport_row_top,
            transport_row_bottom=transport_row_bottom,
            column_header_row_top=column_header_row_top,
            column_header_row_bottom=column_header_row_bottom,
            total_height=PAGE_HEIGHT - column_header_row_bottom,
        )

    def _build_story(self, doc: BaseDocTemplate):
        """Build the table rows that flow between the fixed header and footer."""

        # Table cells intentionally omit borders. Continuous vertical rules are
        # drawn by the page callback so they extend through unused table space.
        rows = [
            [
                _value_paragraph(line.un_number, self.table_center_style),
                _value_paragraph(line.proper_shipping_name, self.table_left_style),
                _value_paragraph(_hazard_text(line), self.table_center_style),
                _value_paragraph(line.packing_group or "", self.table_center_style),
                _value_paragraph(
                    line.quantity_and_type_of_packing,
                    self.table_left_style,
                ),
                _value_paragraph(line.packing_instruction, self.table_center_style),
                _value_paragraph(line.authorization or "", self.table_center_style),
            ]
            for line in self.declaration_data.lines
        ]

        table = Table(
            rows,
            colWidths=COLUMNS.widths(doc.width),
            repeatRows=0,
            splitByRow=1,
            rowHeights=None,
        )
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("LEADING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (1, 0), (1, -1), TEXT_COLUMN_PADDING),
            ("RIGHTPADDING", (1, 0), (1, -1), TEXT_COLUMN_PADDING),
            ("LEFTPADDING", (4, 0), (4, -1), TEXT_COLUMN_PADDING),
            ("RIGHTPADDING", (4, 0), (4, -1), TEXT_COLUMN_PADDING),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        return [table]

    def build(self, filename: str | None = None) -> bytes:
        """Build and return the PDF, optionally writing a copy to ``filename``."""

        if filename is not None and not filename.endswith(".pdf"):
            raise ValueError("Provided filenames must end with .pdf")

        self.filename = filename
        output = BytesIO()

        doc = BaseDocTemplate(
            output,
            pagesize=self.page_size,
            leftMargin=self.left_margin,
            rightMargin=self.right_margin,
            topMargin=self.top_margin,
            bottomMargin=self.bottom_margin,
        )

        template = self._build_page_template(doc)
        story = self._build_story(doc)
        doc.addPageTemplates([template])
        doc.build(
            story,
            canvasmaker=DangerousGoodsCanvas,
        )

        pdf = output.getvalue()
        if filename is not None:
            Path(filename).write_bytes(pdf)
        return pdf
