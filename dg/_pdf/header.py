"""General header-section renderers for the declaration form."""

from reportlab.platypus import Paragraph

from ..models import Party
from .layout import (
    BOX_X_PADDING,
    BOX_Y_PADDING,
    TITLE_TEXT,
    BoxOverflowError,
    FieldWrapError,
    measure_paragraph as _measure_paragraph,
    measure_value as _measure_value,
)
from .table_header import TableHeaderRendererMixin
from .transport import TransportRendererMixin


class HeaderRendererMixin(TransportRendererMixin, TableHeaderRendererMixin):
    """Draw the fixed header sections of each declaration page."""

    def draw_fx18_box(self, box_canvas, box_left, box_bottom, box_width, box_height):
        """Reserve the blank box intended for future FX-18 information."""

        box_canvas.saveState()
        box_canvas.rect(box_left, box_bottom, box_width, box_height, stroke=1, fill=0)
        box_canvas.restoreState()

    def draw_waybill_number_box(self, box_canvas, box_left, box_bottom, box_width, box_height):
        """Draw waybill, page-count, and shipper-reference information."""

        box_canvas.saveState()

        x_padding = BOX_X_PADDING
        y_padding = BOX_Y_PADDING
        content_width = box_width - (2 * x_padding)
        content_top = box_bottom + box_height

        # Paragraphs report their height after wrapping, so position them
        # by moving a cursor downward from the top edge of the box.
        cursor_y = content_top - y_padding

        # Draw box border
        box_canvas.rect(box_left, box_bottom, box_width, box_height, stroke=1, fill=0)

        # Air waybill occupies the first line of the upper-right box.
        waybill_paragraph, waybill_paragraph_height = _measure_value(
            f"Air Waybill No. {self.declaration_data.air_waybill_number or ''}",
            self.header_text_style, 
            content_width
        )
        cursor_y -= waybill_paragraph_height
        # Allow a small tolerance for font metrics while rejecting wraps.
        if waybill_paragraph_height > self.header_text_style.leading * 1.2:
            raise FieldWrapError(
                field_name='Air Waybill Number',
                value=self.declaration_data.air_waybill_number,
            )
        waybill_paragraph.drawOn(box_canvas, box_left + x_padding, cursor_y)

        # DangerousGoodsCanvas adds the page count in a second pass because
        # ReportLab does not know the final page total during initial layout.
        reference_row_top = 715
        reference_label_paragraph, reference_label_height = _measure_paragraph(
            "Shipper's Reference No. (optional)", 
            self.header_text_style, 
            content_width/2
        )
        cursor_y = reference_row_top - reference_label_height
        reference_label_paragraph.drawOn(
            box_canvas,
            box_left + x_padding,
            cursor_y,
        )

        if self.declaration_data.shippers_reference:

            reference_value_paragraph, reference_value_height = _measure_value(
                self.declaration_data.shippers_reference, 
                self.header_text_style, 
                content_width/2
            )

            available_height = reference_row_top - box_bottom
            if reference_value_height > available_height:
                raise BoxOverflowError(
                    box_name="Shipper's Reference",
                    required=reference_value_height,
                    available=available_height,
                )

            reference_value_paragraph.drawOn(
                box_canvas,
                box_left + x_padding + (content_width / 2),
                reference_row_top - reference_value_height,
            )

        box_canvas.restoreState()

    def draw_address_box(self, box_canvas, box_left, box_bottom, box_width, box_height, title, address: Party):
        """Draw a titled party address inside a fixed-height header box."""
        box_canvas.saveState()

        x_padding = BOX_X_PADDING
        y_padding = BOX_Y_PADDING
        content_width = box_width - (2 * x_padding)
        content_top = box_bottom + box_height - y_padding
        content_height = box_height - 2 * y_padding

        # Measure everything first so overflow fails before partial content
        # is committed to the page.
        measured_paragraphs = []

        title_paragraph, title_height = _measure_paragraph(title, self.box_title_style, content_width)
        measured_paragraphs.append((title_paragraph, title_height))

        # Small gap after the title.
        title_gap = 2

        name_paragraph, name_height = _measure_value(address.name, self.address_text_style, content_width)
        measured_paragraphs.append((name_paragraph, name_height))

        if address.business:
            business_paragraph, business_height = _measure_value(address.business, self.address_text_style, content_width)
            measured_paragraphs.append((business_paragraph, business_height))

        for line in address.address:
            line_paragraph, line_height = _measure_value(line, self.address_text_style, content_width)
            measured_paragraphs.append((line_paragraph, line_height))

        needed_height = (
            title_height
            + title_gap
            # Everything after the title.
            + sum(
                paragraph_height
                for _, paragraph_height in measured_paragraphs[1:]
            )
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

    def draw_header(self, header_canvas, doc):
        layout = self.header_layout(doc.width)

        page_left = doc.leftMargin
        box_width = doc.width / 2

        box_left = page_left
        box_right = page_left + box_width

        # The header is a two-column grid for its first three bands, then a
        # single full-width band for the dangerous-goods table headings.

        title_paragraph = Paragraph(
            TITLE_TEXT,
            self.header_title_style,
        )
        title_paragraph.wrap(doc.width, 1000)
        title_paragraph.drawOn(
            header_canvas,
            page_left,
            layout.title_top - layout.title_height,
        )

        self.draw_address_box(
            header_canvas,
            box_left, 
            layout.shipper_row_bottom,
            box_width, 
            layout.shipper_row_top - layout.shipper_row_bottom,
            "Shipper",
            self.declaration_data.shipper,
        )

        self.draw_address_box(
            header_canvas,
            box_left, 
            layout.consignee_row_bottom,
            box_width, 
            layout.consignee_row_top - layout.consignee_row_bottom,
            "Consignee",
            self.declaration_data.consignee,
        )

        self.draw_waybill_number_box(
            header_canvas,
            box_right,
            layout.shipper_row_bottom,
            box_width,
            layout.shipper_row_top - layout.shipper_row_bottom,
        )

        self.draw_fx18_box(
            header_canvas,
            box_right,
            layout.consignee_row_bottom,
            box_width,
            layout.consignee_row_top - layout.consignee_row_bottom,
        )

        self.draw_transport_details_box(
            header_canvas,
            box_left,
            layout.transport_row_bottom,
            box_width,
            layout.transport_row_top - layout.transport_row_bottom,
        )

        self.draw_shipment_type_box(
            header_canvas,
            box_right,
            layout.transport_row_bottom,
            box_width,
            layout.transport_row_top - layout.transport_row_bottom,
        )

        self.draw_column_headers(
            header_canvas,
            box_left,
            layout.column_header_row_bottom,
            box_width*2,
            layout.column_header_row_top - layout.column_header_row_bottom,
        )

