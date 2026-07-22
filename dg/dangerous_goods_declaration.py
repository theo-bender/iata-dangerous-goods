from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfgen import canvas

from dg import (
    DeclarationData,
    Party,
)

from datetime import datetime, date

styles = getSampleStyleSheet()
PAGE_W, PAGE_H = letter

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
                message = (
                    f'The "{field_name}" field '
                    "wrapped onto multiple lines."
                )
            elif field_name is not None:
                message = f'The "{field_name}" field wrapped onto multiple lines.'
            else:
                message = "A field wrapped onto multiple lines."

        super().__init__(message)

        self.field_name = field_name
        self.value = value

class DangerousGoodsCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        # Save the current page's state before moving on
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)

        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(page_count)
            super().showPage()

        super().save()

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 10)
        self.drawString(
            # Page number position must be hard-coded
            309,
            720,
            f"Page {self._pageNumber} of {page_count} Pages",
        )

class DangerousGoodsDeclaration:
    def __init__(
            self, 
            declaration_data: DeclarationData,
        ):

        self.declaration_data = declaration_data

        self.pagesize = letter
        self.left_margin = 0.875 * inch
        self.right_margin = 0.875 * inch
        self.top_margin = 5.05 * inch
        self.bottom_margin = 1.875 * inch

        # Styles for the top title
        self.header_title_style = ParagraphStyle(
            "Helvetica12Bold",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            alignment=TA_LEFT,
            spaceAfter=0,
            textColor=colors.black,
        )

        # Styles for address box title and content
        self.box_title_style = ParagraphStyle(
            "BoxTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=9,
            textColor=colors.black,
        )

        self.address_text_style = ParagraphStyle(
            "AddressBoxText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=9,
            textColor=colors.black,
        )

        self.header_text_style = ParagraphStyle(
            "HeaderBoxText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=11,
            textColor=colors.black,
        )
    
    def build(
            self,
            filename: str | None = None
        ):
        def measure_paragraph(text, style, width):
            p = Paragraph(text, style)
            _, h = p.wrap(width, 10_000)
            return p, h
        
        def draw_fx18_box(box_canvas, box_left, box_bottom, box_width, box_height):
            #Plan to attempt to get this package FX-18 certified, if this happens some details will be added in this box
            box_canvas.saveState()
            box_canvas.rect(box_left, box_bottom, box_width, box_height, stroke=1, fill=0)
            box_canvas.restoreState()

        def draw_waybill_number_box(box_canvas, box_left, box_bottom, box_width, box_height):
            """
            Draws one header box containing air waybill number, page numbers, and shippers reference number"""

            box_canvas.saveState()

            x_padding = 4
            y_padding = 2
            content_width = box_width - (2 * x_padding)
            content_top = box_bottom + box_height

            # Draw content top-down
            cursor_y = content_top - y_padding

            # Draw box border
            box_canvas.rect(box_left, box_bottom, box_width, box_height, stroke=1, fill=0)

            #Air waybill
            waybill_paragraph, waybill_paragraph_height = measure_paragraph(
                f'Air Waybill No. {self.declaration_data.air_waybill_number if self.declaration_data.air_waybill_number else ''}', 
                self.header_text_style, 
                content_width
            )
            cursor_y -= waybill_paragraph_height
            if waybill_paragraph_height > self.header_text_style.leading * 1.2: # Allow a little tolerance for font metrics
                raise FieldWrapError(
                    field_name='Air Waybill Number',
                    value=self.declaration_data.air_waybill_number,
                )
            waybill_paragraph.drawOn(box_canvas, box_left + x_padding, cursor_y)

            #Page number is drawn on by DangerousGoodsCanvas
            #Total number of pages cannot be determined until document is drawn, so page number is added after this happens

            #Reference number

            cursor_y_after_page = 715
            ref_paragraph, ref_paragraph_height = measure_paragraph(
                "Shipper's Reference No. (optional)", 
                self.header_text_style, 
                content_width/2
            )
            cursor_y = cursor_y_after_page - ref_paragraph_height
            ref_paragraph.drawOn(box_canvas, box_left + x_padding, cursor_y)

            if self.declaration_data.shippers_reference:

                ref_value_paragraph, ref_value_paragraph_height = measure_paragraph(
                    self.declaration_data.shippers_reference, 
                    self.header_text_style, 
                    content_width/2
                )

                available_height = cursor_y_after_page - box_bottom
                if ref_value_paragraph_height > available_height:
                    raise BoxOverflowError(
                        box_name="Shipper's Reference",
                        required=ref_value_paragraph_height,
                        available=available_height,
                    )
                
                ref_value_paragraph.drawOn(box_canvas, box_left + x_padding + (content_width/2), cursor_y_after_page - ref_value_paragraph_height)

            box_canvas.restoreState()

        def draw_address_box(box_canvas, box_left, box_bottom, box_width, box_height, title, address: Party):
            """
            Draws one header box with a title and address content.
            box_left, box_bottom = bottom-left corner.
            """
            box_canvas.saveState()

            x_padding = 4
            y_padding = 2
            content_width = box_width - (2 * x_padding)
            content_top = box_bottom + box_height - y_padding
            content_height = box_height - 2 * y_padding

            # Measure everything first
            measured_paragraphs = []

            title_paragraph, title_height = measure_paragraph(title, self.box_title_style, content_width)
            measured_paragraphs.append((title_paragraph, title_height))

            # small gap after title
            title_gap = 2

            name_paragraph, name_height = measure_paragraph(address.name, self.address_text_style, content_width)
            measured_paragraphs.append((name_paragraph, name_height))

            if address.business:
                business_paragraph, business_height = measure_paragraph(address.business, self.address_text_style, content_width)
                measured_paragraphs.append((business_paragraph, business_height))

            for line in address.address:
                line_paragraph, line_height = measure_paragraph(line, self.address_text_style, content_width)
                measured_paragraphs.append((line_paragraph, line_height))

            needed_height = (
                title_height
                + title_gap
                + sum(paragraph_height for _, paragraph_height in measured_paragraphs[1:])   # everything after the title
            )

            available_height = content_height

            if needed_height > available_height:
                raise BoxOverflowError(
                    box_name=title,
                    required=needed_height,
                    available=available_height,
                )

            # Draw box border
            box_canvas.rect(box_left, box_bottom, box_width, box_height, stroke=1, fill=0)

            # Draw content top-down
            current_y = content_top

            title_paragraph.drawOn(box_canvas, box_left + x_padding, current_y - title_height)
            current_y -= title_height + title_gap

            for paragraph, paragraph_height in measured_paragraphs[1:]:
                paragraph.drawOn(box_canvas, box_left + x_padding, current_y - paragraph_height)
                current_y -= paragraph_height

            box_canvas.restoreState()

        def draw_header(header_canvas, doc):
            header_canvas.saveState()

            page_left = doc.leftMargin
            page_right = PAGE_W - doc.rightMargin

            # Big top title
            header_title_top = PAGE_H - 0.4 * inch

            p = Paragraph(
                "SHIPPER'S DECLARATION FOR DANGEROUS GOODS",
                self.header_title_style,
            )
            _, header_title_height = p.wrap(page_right - page_left, 1000)
            p.drawOn(header_canvas, page_left, header_title_top - header_title_height)

            # Boxes start directly under the title
            gap_below_title = 0 * inch
            r1_box_top = header_title_top - header_title_height - gap_below_title

            r1_box_height = 1 * inch
            r2_box_height = 1 * inch

            gap_between_boxes = 0 * inch
            box_width = (doc.width - gap_between_boxes) / 2

            box_left = page_left
            box_right = page_left + box_width

            r1_box_bottom = r1_box_top - r1_box_height
            r2_box_bottom = r1_box_bottom - r1_box_height

            draw_address_box(
                header_canvas,
                box_left, r1_box_bottom, box_width, r1_box_height,
                "Shipper",
                self.declaration_data.shipper,
            )

            draw_address_box(
                header_canvas,
                box_left, r2_box_bottom, box_width, r1_box_height,
                "Consignee",
                self.declaration_data.consignee,
            )

            draw_waybill_number_box(
                header_canvas,
                box_right,
                r1_box_bottom,
                box_width,
                r1_box_height
            )

            draw_fx18_box(
                header_canvas,
                box_right,
                r2_box_bottom,
                box_width,
                r2_box_height
            )

            header_canvas.restoreState()

        def build_story():
            story = []
            for i in range(40):
                story.append(Paragraph(f"Body paragraph {i + 1}.", styles["BodyText"]))
                story.append(Spacer(1, 0.12 * inch))
            return story

        if filename:
            if not filename.endswith('.pdf'):
                raise ValueError('Provided filenames must end with .pdf')
            self.filename = filename
        else:
            tnow = datetime.now()
            self.filename = f"dgd_{tnow.strftime('%Y-%m-%d_%H-%M-%S')}.pdf"

        doc = BaseDocTemplate(
            self.filename,
            pagesize=self.pagesize,
            leftMargin=self.left_margin,
            rightMargin=self.right_margin,
            topMargin=self.top_margin,
            bottomMargin=self.bottom_margin,
        )

        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id="content",
        )

        template = PageTemplate(
            id="main",
            frames=[frame],
            onPage=draw_header,
        )
        doc.addPageTemplates([template])

        story = build_story()
        doc.build(
            story,
            canvasmaker=DangerousGoodsCanvas,
        )

if __name__ == '__main__':

    from dg import (
        InnerReceptacle,
        Package,
        Party,
        PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE,
        Shipment,
        build_declaration,
        validate_shipment,
    )
    from decimal import Decimal
    import sys

    shipment = Shipment(
        un_number=3266,
        packages=(
            Package(
                packaging=PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE,
                net_quantity=Decimal("1"),
                inner_receptacles=(
                    InnerReceptacle(
                        quantity=Decimal("1"),
                    ),
                ),
            ),
        ),
        ship_date=date.today(),
        technical_names=('tripotassium phosphate',),

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
        shippers_reference='1234',
        departure_airport='SEA',
        destination_airport="PDX",
        additional_handling_information="Emergency contact: +1 555 555 0100",
    )

    report = validate_shipment(shipment)
    if not report.is_valid:
        for issue in report.issues:
            print(issue.code, issue.severity.value, issue.message)
        sys.exit()
        
    declaration = build_declaration(report)

    dgd = DangerousGoodsDeclaration(declaration)
    dgd.build(filename='dgd.pdf')