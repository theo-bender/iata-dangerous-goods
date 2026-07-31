from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfgen import canvas

from dg import (
    DeclarationData,
    DeclarationLine,
    Party,
    AircraftType,
)

from datetime import datetime, date
from dataclasses import dataclass

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

@dataclass(frozen=True)
class HeaderLayout:
    title_top: float
    title_height: float

    r1_top: float
    r1_bottom: float

    r2_top: float
    r2_bottom: float

    r3_top: float
    r3_bottom: float

    r4_top: float
    r4_bottom: float

    total_height: float

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

        # Styles
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

        self.italic_text_style = ParagraphStyle(
            "ItalicBody",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=6,
            leading=8,
            textColor=colors.black,
        )

        self.enum_style = ParagraphStyle(
            "EnumBody",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            textColor=colors.black,
            alignment=TA_CENTER
        )

        self.centered_subhead_style = ParagraphStyle(
            "CenteredSubhead",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=11,
            textColor=colors.black,
            alignment=TA_CENTER
        )

        self.centered_colhead_style = ParagraphStyle(
            "CenteredColhead",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=9,
            textColor=colors.black,
            alignment=TA_CENTER
        )

        self.table_center_style = ParagraphStyle(
            "TableCenter",
            fontName="Courier",
            parent=self.address_text_style,
            alignment=TA_CENTER,
        )

        self.table_left_style = ParagraphStyle(
            "TableLeft",
            fontName="Courier",
            parent=self.address_text_style,
            alignment=TA_LEFT,
        )

        self.pagesize = letter
        self.left_margin = 0.875 * inch
        self.right_margin = 0.875 * inch

        dummy_doc_width = (
            PAGE_W
            - self.left_margin
            - self.right_margin
        )
        layout = self.header_layout(dummy_doc_width)

        self.top_margin = layout.total_height
        self.bottom_margin = 2.375 * inch

        #Column widths
        self.un_col_width = 0.75/9
        self.psn_col_width = 2.25/9
        self.class_col_width = 1/9
        self.pg_col_width = 0.75/9
        self.desc_col_width = 3.15/9
        self.pi_col_width = 0.6/9
        self.auth_col_width = 0.5/9

    def header_layout(self, doc_width: float) -> HeaderLayout:
        title_top = PAGE_H - 0.5 * inch

        title = Paragraph(
            "SHIPPER'S DECLARATION FOR DANGEROUS GOODS",
            self.header_title_style,
        )
        _, title_height = title.wrap(doc_width, 1000)

        gap_below_title = 0

        r1_height = 1 * inch
        r2_height = 1 * inch
        r3_height = 2 * inch
        r4_height = 1 * inch

        r1_top = title_top - title_height - gap_below_title
        r1_bottom = r1_top - r1_height

        r2_top = r1_bottom
        r2_bottom = r2_top - r2_height

        r3_top = r2_bottom
        r3_bottom = r3_top - r3_height

        r4_top = r3_bottom
        r4_bottom = r4_top - r4_height

        return HeaderLayout(
            title_top=title_top,
            title_height=title_height,
            r1_top=r1_top,
            r1_bottom=r1_bottom,
            r2_top=r2_top,
            r2_bottom=r2_bottom,
            r3_top=r3_top,
            r3_bottom=r3_bottom,
            r4_top=r4_top,
            r4_bottom=r4_bottom,
            total_height=PAGE_H - r4_bottom,
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

        def draw_transport_details_box(box_canvas, box_left, box_bottom, box_width, box_height):
            """
            Draws the transport details box which contains aircraft type, airport of departure, and airport of destination
            """
            box_canvas.saveState()
            
            x_padding = 4
            y_padding = 2
            content_width = box_width - (2 * x_padding)
            content_top = box_bottom + box_height - y_padding
            content_height = box_height - 2 * y_padding

            # Draw content top-down
            cursor_y = content_top - y_padding

            # Draw box border
            box_canvas.rect(box_left, box_bottom, box_width, box_height, stroke=1, fill=0)

            #Copy count statement
            copies_paragraph, copies_paragraph_height = measure_paragraph(
                "Two completed and signed copies of this Declaration must be handed to the operator.", 
                self.italic_text_style, 
                content_width
            )
            cursor_y -= copies_paragraph_height
            copies_paragraph.drawOn(box_canvas, box_left + x_padding, cursor_y)
            cursor_y -= y_padding

            # Draw line under copies statement
            box_canvas.line(box_left, cursor_y, box_width+box_left, cursor_y)

            #TRANSPORT DETAILS subheader
            subheader_paragraph, subheader_paragraph_height = measure_paragraph(
                "TRANSPORT DETAILS", 
                self.box_title_style, 
                content_width
            )
            cursor_y -= subheader_paragraph_height
            subheader_paragraph.drawOn(box_canvas, box_left + x_padding, cursor_y)
            cursor_y -= y_padding * 2

            # Draw line under copies statement
            box_canvas.line(box_left, cursor_y, box_width+box_left, cursor_y)

            sub_box_width = box_width/2
            #Draw vertical line seperating halves of box
            box_canvas.line(box_left+sub_box_width, cursor_y, box_left+sub_box_width, cursor_y - 1*inch)
            box_canvas.line(box_left, cursor_y - 1*inch, box_width+box_left, cursor_y - 1*inch)

            #Aircraft type
            actype_label_paragraph, actype_label_paragraph_height = measure_paragraph(
                "This shipment is within the limitations prescribed for:<br/><br/>(delete non-applicable)", 
                self.address_text_style, 
                content_width/2
            )
            left_side_cursor_y = cursor_y - actype_label_paragraph_height
            actype_label_paragraph.drawOn(box_canvas, box_left + x_padding, left_side_cursor_y)
            left_side_cursor_y -= y_padding*2

            if self.declaration_data.aircraft_limitation == AircraftType.PASSENGER_AND_CARGO:
                pca_fill = False
                cao_fill = True
            elif self.declaration_data.aircraft_limitation == AircraftType.CARGO_ONLY:
                pca_fill = True
                cao_fill = False
            else:
                raise ValueError('Aircraft type must be PASSENGER_AND_CARGO or CARGO_ONLY')

            pca_paragraph, pca_paragraph_height = measure_paragraph(
                "PASSENGER AND CARGO AIRCRAFT", 
                self.enum_style, 
                sub_box_width/2 - x_padding*2
            )
            cao_paragraph, cao_paragraph_height = measure_paragraph(
                "CARGO AIRCRAFT ONLY", 
                self.enum_style, 
                sub_box_width/2 - x_padding*2
            )

            pca_y = left_side_cursor_y - pca_paragraph_height
            cao_y = pca_y
            pca_paragraph.drawOn(box_canvas, box_left + x_padding, pca_y)
            cao_paragraph.drawOn(box_canvas, sub_box_width + x_padding, cao_y)

            #Boxes around aircraft type enums
            box_canvas.rect(box_left, pca_y - y_padding, sub_box_width/2, pca_paragraph_height + y_padding*2, stroke=1, fill=pca_fill)
            box_canvas.rect(box_left+sub_box_width/2, cao_y-y_padding, sub_box_width/2, cao_paragraph_height + y_padding*2, stroke=1, fill=cao_fill)

            #Airport of departure
            aod_header_paragraph, aod_header_paragraph_height = measure_paragraph(
                "Airport of Departure (optional)",
                self.address_text_style, 
                content_width/2
            )
            right_side_cursor_y = cursor_y - aod_header_paragraph_height
            aod_header_paragraph.drawOn(box_canvas, box_left + sub_box_width + x_padding, right_side_cursor_y)
            right_side_cursor_y -= y_padding*2

            if self.declaration_data.departure_airport:
                aod_paragraph, aod_paragraph_height = measure_paragraph(
                    self.declaration_data.departure_airport, 
                    self.address_text_style, 
                    content_width/2
                )

                available_height = right_side_cursor_y - (cursor_y - 1*inch)
                if aod_paragraph_height > available_height:
                    raise BoxOverflowError(
                        box_name="Airport of departure",
                        required=aod_paragraph_height,
                        available=available_height,
                    )
                
                aod_paragraph.drawOn(box_canvas, box_left + sub_box_width + x_padding, right_side_cursor_y - aod_paragraph_height)

            cursor_y = cursor_y - 1*inch

            #Airport of destination
            aod_header_paragraph, aod_header_paragraph_height = measure_paragraph(
                "Airport of Destination (optional)",
                self.address_text_style, 
                content_width
            )
            cursor_y -= aod_header_paragraph_height
            aod_header_paragraph.drawOn(box_canvas, box_left + x_padding, cursor_y)
            cursor_y -= y_padding*2

            if self.declaration_data.destination_airport:
                aod_paragraph, aod_paragraph_height = measure_paragraph(
                    self.declaration_data.destination_airport, 
                    self.address_text_style, 
                    content_width
                )

                available_height = cursor_y - box_bottom
                if aod_paragraph_height > available_height:
                    raise BoxOverflowError(
                        box_name="Airport of destination",
                        required=aod_paragraph_height,
                        available=available_height,
                    )
                
                aod_paragraph.drawOn(box_canvas, box_left + x_padding, cursor_y - aod_paragraph_height)

            box_canvas.restoreState()

        def draw_shipment_type_box(box_canvas, box_left, box_bottom, box_width, box_height):
            """
            Draws shipment type box which contains a warning header, and the shipment type (radioactive/non-radioactive)
            """
            box_canvas.saveState()
                        
            x_padding = 4
            y_padding = 2
            content_width = box_width - (2 * x_padding)
            content_top = box_bottom + box_height - y_padding
            content_height = box_height - 2 * y_padding

            # Draw content top-down
            cursor_y = content_top - y_padding

            # Draw box border
            box_canvas.rect(box_left, box_bottom, box_width, box_height, stroke=1, fill=0)

            #Warning subheader
            subheader_paragraph, subheader_paragraph_height = measure_paragraph(
                "WARNING<br/><br/>Failure to comply in all respects with the applicable Dangerous Goods Regulations may be in breach of the applicable law, subject to legal penalties.", 
                self.box_title_style, 
                content_width
            )
            cursor_y -= subheader_paragraph_height
            subheader_paragraph.drawOn(box_canvas, box_left + x_padding, cursor_y)
            cursor_y -= 0.695*inch

            # Draw line under warning statement
            box_canvas.line(box_left, cursor_y, box_width+box_left, cursor_y)

            cursor_y -= y_padding*2

            #Shipment type
            type_label_paragraph, type_label_paragraph_height = measure_paragraph(
                "Shipment type: (delete non-applicable)", 
                self.address_text_style, 
                content_width
            )
            cursor_y -= type_label_paragraph_height
            type_label_paragraph.drawOn(box_canvas, box_left + x_padding, cursor_y)
            cursor_y -= y_padding*3


            nr_paragraph, nr_paragraph_height = measure_paragraph(
                "NON-RADIOACTIVE", 
                self.enum_style, 
                content_width/2
            )
            cursor_y -= nr_paragraph_height
            nr_paragraph.drawOn(box_canvas, box_left + x_padding, cursor_y)

            rr_paragraph, rr_paragraph_height = measure_paragraph(
                "RADIOACTIVE", 
                self.enum_style, 
                content_width/2
            )
            rr_paragraph.drawOn(box_canvas, box_left + (box_width/2) + x_padding, cursor_y)

            #Boxes around shipment type enums
            box_canvas.rect(box_left, cursor_y - y_padding, box_width/2, nr_paragraph_height + y_padding*2, stroke=1, fill=self.declaration_data.is_radioactive)
            box_canvas.rect(box_left+box_width/2, cursor_y-y_padding, box_width/2, rr_paragraph_height + y_padding*2, stroke=1, fill=not self.declaration_data.is_radioactive)

            box_canvas.restoreState()

        def draw_column_headers(box_canvas, box_left, box_bottom, box_width, box_height):
            """
            This draws the nature and quantity of dangerous goods headers, which appear on every page
            """

            box_canvas.saveState()
                                    
            x_padding = 4
            y_padding = 2
            content_width = box_width - (2 * x_padding)
            content_top = box_bottom + box_height - y_padding
            content_height = box_height - 2 * y_padding

            # Draw content top-down
            cursor_y = content_top

            # Draw box border
            box_canvas.rect(box_left, box_bottom, box_width, box_height, stroke=1, fill=0)

            #Nature and quantity of dangerous goods subheader
            subheader_paragraph, subheader_paragraph_height = measure_paragraph(
                "NATURE AND QUANTITY OF DANGEROUS GOODS", 
                self.header_title_style, 
                content_width
            )
            cursor_y -= subheader_paragraph_height
            subheader_paragraph.drawOn(box_canvas, box_left + x_padding, cursor_y)
            cursor_y -= y_padding*2

            # Draw line under warning statement
            box_canvas.line(box_left, cursor_y, box_width+box_left, cursor_y)
            top_line_y = cursor_y

            cursor_y -= y_padding

            #Dangerous goods identification subheader
            dg_subheader_paragraph, dg_subheader_paragraph_height = measure_paragraph(
                "Dangerous Goods Identification", 
                self.centered_subhead_style, 
                content_width * (self.un_col_width + self.psn_col_width + self.class_col_width + self.pg_col_width)
            )
            cursor_y -= dg_subheader_paragraph_height
            dg_subheader_paragraph.drawOn(box_canvas, box_left, cursor_y)
            cursor_y -= y_padding

            box_canvas.line(box_left, cursor_y, box_width+box_left, cursor_y)

            #Box column headers
            un_paragraph, un_paragraph_height = measure_paragraph(
                "UN or ID No.", 
                self.centered_colhead_style, 
                box_width * self.un_col_width
            )
            psn_paragraph, psn_paragraph_height = measure_paragraph(
                "Proper Shipping Name", 
                self.centered_colhead_style, 
                box_width * self.psn_col_width
            )
            class_paragraph, class_paragraph_height = measure_paragraph(
                "Class or Division (subsidiary hazard)", 
                self.centered_colhead_style, 
                box_width * self.class_col_width
            )
            pg_paragraph, pg_paragraph_height = measure_paragraph(
                "Packing Group", 
                self.centered_colhead_style, 
                box_width * self.pg_col_width
            )
            desc_paragraph, desc_paragraph_height = measure_paragraph(
                "Quantity and Type of Packing", 
                self.centered_colhead_style, 
                box_width * self.desc_col_width
            )
            pi_paragraph, pi_paragraph_height = measure_paragraph(
                "Packing Inst.", 
                self.centered_colhead_style, 
                box_width * self.pi_col_width
            )
            auth_paragraph, auth_paragraph_height = measure_paragraph(
                "Auth.", 
                self.centered_colhead_style, 
                box_width * self.auth_col_width
            )
            tallest_col = max(un_paragraph_height, psn_paragraph_height, class_paragraph_height, pg_paragraph_height, desc_paragraph_height, pi_paragraph_height, auth_paragraph_height)
            
            cursor_x = box_left
            un_paragraph.drawOn(box_canvas, cursor_x, cursor_y-un_paragraph_height)
            cursor_x += box_width * self.un_col_width
            box_canvas.line(cursor_x, cursor_y - tallest_col, cursor_x, cursor_y)
            psn_paragraph.drawOn(box_canvas, cursor_x, cursor_y-psn_paragraph_height)
            cursor_x += box_width * self.psn_col_width
            box_canvas.line(cursor_x, cursor_y - tallest_col, cursor_x, cursor_y)
            class_paragraph.drawOn(box_canvas, cursor_x, cursor_y-class_paragraph_height)
            cursor_x += box_width * self.class_col_width
            box_canvas.line(cursor_x, cursor_y - tallest_col, cursor_x, cursor_y)
            pg_paragraph.drawOn(box_canvas, cursor_x, cursor_y-pg_paragraph_height)
            cursor_x += box_width * self.pg_col_width
            box_canvas.line(cursor_x, cursor_y - tallest_col, cursor_x, top_line_y)
            desc_paragraph.drawOn(box_canvas, cursor_x, cursor_y-desc_paragraph_height)
            cursor_x += box_width * self.desc_col_width
            box_canvas.line(cursor_x, cursor_y - tallest_col, cursor_x, top_line_y)
            pi_paragraph.drawOn(box_canvas, cursor_x, cursor_y-pi_paragraph_height)
            cursor_x += box_width * self.pi_col_width
            box_canvas.line(cursor_x, cursor_y - tallest_col, cursor_x, top_line_y)
            auth_paragraph.drawOn(box_canvas, cursor_x, cursor_y-auth_paragraph_height)

            box_canvas.restoreState()

        def draw_additional_handling_box(box_canvas, box_left, box_bottom, box_width, box_height):
            """
            This draws the additional handling statement
            """

            box_canvas.saveState()
                                    
            x_padding = 4
            y_padding = 2
            content_width = box_width - (2 * x_padding)
            content_top = box_bottom + box_height - y_padding
            content_height = box_height - 2 * y_padding

            # Draw content top-down
            cursor_y = content_top

            # Draw box border
            box_canvas.rect(box_left, box_bottom, box_width, box_height, stroke=1, fill=0)

            # subheader
            subheader_paragraph, subheader_paragraph_height = measure_paragraph(
                "Additional Handling Information", 
                self.box_title_style, 
                content_width
            )
            cursor_y -= subheader_paragraph_height
            subheader_paragraph.drawOn(box_canvas, box_left + x_padding, cursor_y)
            cursor_y -= y_padding

            if self.declaration_data.additional_handling_information:
                hi_paragraph, hi_paragraph_height = measure_paragraph(
                    self.declaration_data.additional_handling_information, 
                    self.address_text_style, 
                    content_width
                )

                available_height = cursor_y - box_bottom
                if hi_paragraph_height > available_height:
                    raise BoxOverflowError(
                        box_name="Additional handling information",
                        required=hi_paragraph_height,
                        available=available_height,
                    )
                
                hi_paragraph.drawOn(box_canvas, box_left + x_padding, cursor_y - hi_paragraph_height)

            box_canvas.restoreState()

        def draw_signature_box(box_canvas, box_left, box_bottom, box_width, box_height):
            """
            This draws the signature box at the bottom of the page
            """

            box_canvas.saveState()
                                    
            x_padding = 4
            y_padding = 2
            content_width = box_width - (2 * x_padding)
            content_top = box_bottom + box_height - y_padding
            content_height = box_height - 2 * y_padding

            left_side_start = box_left
            right_side_start = box_left + (box_width * (2/3))

            # Draw content top-down
            cursor_y = content_top
            left_cursor_y = cursor_y
            right_cursor_y = cursor_y

            # Draw box border
            box_canvas.rect(box_left, box_bottom, box_width, box_height, stroke=1, fill=0)
            #Draw vertical line
            box_canvas.line(right_side_start, box_bottom, right_side_start, box_bottom + box_height)

            # declaration statement
            dec_paragraph, dec_paragraph_height = measure_paragraph(
                "I hereby declare that the contents of this consignment are fully and accurately described above by the proper shipping name, and are classified, packaged, marked and labelled/placarded, and are in all respects in proper condition for transport according to applicable international and national governmental regulations. I declare that all of the applicable air transport requirements have been met.", 
                self.address_text_style, 
                content_width * (2/3)
            )
            left_cursor_y -= dec_paragraph_height
            dec_paragraph.drawOn(box_canvas, left_side_start + x_padding, left_cursor_y)
            left_cursor_y -= y_padding


            #Signatory name
            sigheader_paragraph, sigheader_paragraph_height = measure_paragraph(
                "Name of Signatory", 
                self.box_title_style, 
                content_width * (1/3)
            )
            right_cursor_y -= sigheader_paragraph_height
            sigheader_paragraph.drawOn(box_canvas, right_side_start + x_padding, right_cursor_y)
            right_cursor_y -= y_padding

            sign_paragraph, sign_paragraph_height = measure_paragraph(
                self.declaration_data.signatory, 
                self.address_text_style, 
                content_width * (1/3)
            )
            right_cursor_y -= sign_paragraph_height
            if sign_paragraph_height > self.address_text_style.leading * 1.2: # Allow a little tolerance for font metrics
                raise FieldWrapError(
                    field_name='Signatory Name',
                    value=self.declaration_data.signatory,
                )
            sign_paragraph.drawOn(box_canvas, right_side_start + x_padding, right_cursor_y)


            #Signatory date
            sigdateheader_paragraph, sigdateheader_paragraph_height = measure_paragraph(
                "Date", 
                self.box_title_style, 
                content_width * (1/3)
            )
            right_cursor_y -= sigdateheader_paragraph_height
            sigdateheader_paragraph.drawOn(box_canvas, right_side_start + x_padding, right_cursor_y)
            right_cursor_y -= y_padding

            sigdate_paragraph, sigdate_paragraph_height = measure_paragraph(
                self.declaration_data.signatory_date.strftime("%Y-%m-%d"), #Format date like 2026-07-31
                self.address_text_style, 
                content_width * (1/3)
            )
            right_cursor_y -= sigdate_paragraph_height
            if sigdate_paragraph_height > self.address_text_style.leading * 1.2: # Allow a little tolerance for font metrics
                raise FieldWrapError(
                    field_name='Signatory Date',
                    value=self.declaration_data.signatory_date.strftime("%Y-%m-%d"),
                )
            sigdate_paragraph.drawOn(box_canvas, right_side_start + x_padding, right_cursor_y)

            #Signature label
            siglabel_paragraph, siglabel_paragraph_height = measure_paragraph(
                "Signature<br/>(See warning above)", 
                self.box_title_style, 
                content_width * (1/3)
            )
            right_cursor_y -= siglabel_paragraph_height
            siglabel_paragraph.drawOn(box_canvas, right_side_start + x_padding, right_cursor_y)
            right_cursor_y -= y_padding

            box_canvas.restoreState()


        def draw_header(header_canvas, doc):
            layout = self.header_layout(doc.width)

            page_left = doc.leftMargin
            page_right = PAGE_W - doc.rightMargin
            box_width = doc.width / 2

            box_left = page_left
            box_right = page_left + box_width

            # Big top title
            header_title_top = PAGE_H - 0.5 * inch

            p = Paragraph(
                "SHIPPER'S DECLARATION FOR DANGEROUS GOODS",
                self.header_title_style,
            )
            _, header_title_height = p.wrap(page_right - page_left, 1000)
            p.drawOn(header_canvas, page_left, layout.title_top - layout.title_height)

            draw_address_box(
                header_canvas,
                box_left, 
                layout.r1_bottom, 
                box_width, 
                layout.r1_top - layout.r1_bottom,
                "Shipper",
                self.declaration_data.shipper,
            )

            draw_address_box(
                header_canvas,
                box_left, 
                layout.r2_bottom, 
                box_width, 
                layout.r2_top - layout.r2_bottom,
                "Consignee",
                self.declaration_data.consignee,
            )

            draw_waybill_number_box(
                header_canvas,
                box_right,
                layout.r1_bottom,
                box_width,
                layout.r1_top - layout.r1_bottom
            )

            draw_fx18_box(
                header_canvas,
                box_right,
                layout.r2_bottom,
                box_width,
                layout.r2_top - layout.r2_bottom
            )

            draw_transport_details_box(
                header_canvas,
                box_left,
                layout.r3_bottom,
                box_width,
                layout.r3_top - layout.r3_bottom
            )

            draw_shipment_type_box(
                header_canvas,
                box_right,
                layout.r3_bottom,
                box_width,
                layout.r3_top - layout.r3_bottom
            )

            draw_column_headers(
                header_canvas,
                box_left,
                layout.r4_bottom,
                box_width*2,
                layout.r4_top - layout.r4_bottom
            )

        def draw_footer(footer_canvas, doc):

            page_left = doc.leftMargin
            page_right = PAGE_W - doc.rightMargin

            footer_y = doc.bottomMargin

            gap_below_title = 0 * inch
            r1_box_top = footer_y - gap_below_title

            r1_box_height = 0.6 * inch
            r2_box_height = 1.275 * inch

            gap_between_boxes = 0 * inch

            r1_box_bottom = r1_box_top - r1_box_height
            r2_box_bottom = r1_box_bottom - r2_box_height

            draw_additional_handling_box(
                footer_canvas,
                page_left,
                r1_box_bottom,
                doc.width,
                r1_box_height
            )

            draw_signature_box(
                footer_canvas,
                page_left,
                r2_box_bottom,
                doc.width,
                r2_box_height
            )

        def draw_story_vertical_rules(page_canvas, doc):
            page_canvas.saveState()

            x_left = doc.leftMargin
            x_right = doc.leftMargin + doc.width
            y_bottom = doc.bottomMargin
            y_top = PAGE_H - doc.topMargin

            widths = [
                doc.width * self.un_col_width,
                doc.width * self.psn_col_width,
                doc.width * self.class_col_width,
                doc.width * self.pg_col_width,
                doc.width * self.desc_col_width,
                doc.width * self.pi_col_width,
                doc.width * self.auth_col_width,
            ]

            # Left outer border
            page_canvas.line(x_left, y_bottom, x_left, y_top)

            # Internal separators
            x = x_left
            for w in widths[:-1]:
                x += w
                page_canvas.line(x, y_bottom, x, y_top)

            # Right outer border
            page_canvas.line(x_right, y_bottom, x_right, y_top)

            page_canvas.restoreState()

        def draw_page(page_canvas, doc):
            draw_header(page_canvas, doc)
            draw_story_vertical_rules(page_canvas, doc)
            draw_footer(page_canvas, doc) 

        def build_story(doc):
            story = []
            TEXT_COL_PADDING = 3

            def hazard_text(line: DeclarationLine) -> str:
                if not line.subsidiary_hazards:
                    return line.class_or_division
                wrapped = " ".join(f"({hazard})" for hazard in line.subsidiary_hazards)
                return f"{line.class_or_division} {wrapped}"

            # Keep these widths in the exact same order as the header
            col_widths = [
                doc.width * self.un_col_width,
                doc.width * self.psn_col_width,
                doc.width * self.class_col_width,
                doc.width * self.pg_col_width,
                doc.width * self.desc_col_width,
                doc.width * self.pi_col_width,
                doc.width * self.auth_col_width,
            ]

            rows = []
            for line in self.declaration_data.lines:
                rows.append([
                    Paragraph(line.un_number, self.table_center_style),
                    Paragraph(line.proper_shipping_name, self.table_left_style),
                    Paragraph(hazard_text(line), self.table_center_style),
                    Paragraph(line.packing_group or "", self.table_center_style),
                    Paragraph(line.quantity_and_type_of_packing, self.table_left_style),
                    Paragraph(line.packing_instruction, self.table_center_style),
                    Paragraph(line.authorization or "", self.table_center_style),
                ])

            table = Table(
                rows,
                colWidths=col_widths,
                repeatRows=0,
                splitByRow=1,
                rowHeights=None,
            )

            table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LEADING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

                # Default
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),

                # Padding for left-aligned columns
                ("LEFTPADDING", (1, 0), (1, -1), TEXT_COL_PADDING),
                ("RIGHTPADDING", (1, 0), (1, -1), TEXT_COL_PADDING),

                ("LEFTPADDING", (4, 0), (4, -1), TEXT_COL_PADDING),
                ("RIGHTPADDING", (4, 0), (4, -1), TEXT_COL_PADDING),

                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))

            story.append(table)
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
            onPage=draw_page,
        )
        doc.addPageTemplates([template])

        story = build_story(doc)
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
        signatory='Person Signing',
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