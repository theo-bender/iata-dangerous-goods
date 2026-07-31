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
    AircraftType,
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
        self.top_margin = 5.5 * inch
        self.bottom_margin = 1.875 * inch

        #Column widths
        self.un_col_width = 1/9
        self.psn_col_width = 2/9
        self.class_col_width = 1/9
        self.pg_col_width = 1/9
        self.desc_col_width = 2/9
        self.pi_col_width = 1/9
        self.auth_col_width = 1/9

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
            r3_box_height = 2 * inch
            r4_box_height = 1 * inch

            gap_between_boxes = 0 * inch
            box_width = (doc.width - gap_between_boxes) / 2

            box_left = page_left
            box_right = page_left + box_width

            r1_box_bottom = r1_box_top - r1_box_height
            r2_box_bottom = r1_box_bottom - r2_box_height
            r3_box_bottom = r2_box_bottom - r3_box_height
            r4_box_bottom = r3_box_bottom - r4_box_height

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

            draw_transport_details_box(
                header_canvas,
                box_left,
                r3_box_bottom,
                box_width,
                r3_box_height
            )

            draw_shipment_type_box(
                header_canvas,
                box_right,
                r3_box_bottom,
                box_width,
                r3_box_height
            )

            draw_column_headers(
                header_canvas,
                box_left,
                r4_box_bottom,
                box_width*2,
                r4_box_height
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