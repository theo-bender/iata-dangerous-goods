"""Dangerous-goods identification table headings."""

from .layout import (
    BOX_X_PADDING,
    BOX_Y_PADDING,
    COLUMNS,
    measure_paragraph as _measure_paragraph,
)


class TableHeaderRendererMixin:
    """Draw grouped and individual dangerous-goods column headings."""

    def draw_column_headers(self, box_canvas, box_left, box_bottom, box_width, box_height):
        """Draw the dangerous-goods table headings repeated on every page."""

        box_canvas.saveState()
                                
        x_padding = BOX_X_PADDING
        y_padding = BOX_Y_PADDING
        content_width = box_width - (2 * x_padding)
        content_top = box_bottom + box_height - y_padding
        (
            un_number_width,
            proper_shipping_name_width,
            hazard_class_width,
            packing_group_width,
            packing_description_width,
            packing_instruction_width,
            authorization_width,
        ) = COLUMNS.widths(box_width)

        # Draw content top-down
        cursor_y = content_top

        # Draw box border
        box_canvas.rect(box_left, box_bottom, box_width, box_height, stroke=1, fill=0)

        # Full-width table title.
        table_title, table_title_height = _measure_paragraph(
            "NATURE AND QUANTITY OF DANGEROUS GOODS", 
            self.header_title_style, 
            content_width
        )
        cursor_y -= table_title_height
        table_title.drawOn(box_canvas, box_left + x_padding, cursor_y)
        cursor_y -= y_padding*2

        # Rule separating the table title from grouped column headings.
        box_canvas.line(box_left, cursor_y, box_width+box_left, cursor_y)
        top_line_y = cursor_y

        cursor_y -= y_padding

        # Group heading spanning the first four identification columns.
        identification_header, identification_header_height = _measure_paragraph(
            "Dangerous Goods Identification", 
            self.centered_subhead_style, 
            content_width * sum(COLUMNS.fractions[:4])
        )
        cursor_y -= identification_header_height
        identification_header.drawOn(box_canvas, box_left, cursor_y)
        cursor_y -= y_padding

        box_canvas.line(box_left, cursor_y, box_width+box_left, cursor_y)

        # Measure every label before drawing so all column separators use
        # the tallest label as their common lower boundary.
        un_number_header, un_number_header_height = _measure_paragraph(
            "UN or ID No.", 
            self.centered_colhead_style, 
            un_number_width
        )
        proper_shipping_name_header, proper_shipping_name_header_height = _measure_paragraph(
            "Proper Shipping Name", 
            self.centered_colhead_style, 
            proper_shipping_name_width
        )
        hazard_class_header, hazard_class_header_height = _measure_paragraph(
            "Class or Division (subsidiary hazard)", 
            self.centered_colhead_style, 
            hazard_class_width
        )
        packing_group_header, packing_group_header_height = _measure_paragraph(
            "Packing Group", 
            self.centered_colhead_style, 
            packing_group_width
        )
        packing_description_header, packing_description_header_height = _measure_paragraph(
            "Quantity and Type of Packing", 
            self.centered_colhead_style, 
            packing_description_width
        )
        packing_instruction_header, packing_instruction_header_height = _measure_paragraph(
            "Packing Inst.", 
            self.centered_colhead_style, 
            packing_instruction_width
        )
        authorization_header, authorization_header_height = _measure_paragraph(
            "Auth.", 
            self.centered_colhead_style, 
            authorization_width
        )
        tallest_header_height = max(
            un_number_header_height,
            proper_shipping_name_header_height,
            hazard_class_header_height,
            packing_group_header_height,
            packing_description_header_height,
            packing_instruction_header_height,
            authorization_header_height,
        )
        
        column_left = box_left
        un_number_header.drawOn(
            box_canvas,
            column_left,
            cursor_y - un_number_header_height,
        )
        column_left += un_number_width
        box_canvas.line(
            column_left,
            cursor_y - tallest_header_height,
            column_left,
            cursor_y,
        )
        proper_shipping_name_header.drawOn(
            box_canvas,
            column_left,
            cursor_y - proper_shipping_name_header_height,
        )
        column_left += proper_shipping_name_width
        box_canvas.line(
            column_left,
            cursor_y - tallest_header_height,
            column_left,
            cursor_y,
        )
        hazard_class_header.drawOn(
            box_canvas,
            column_left,
            cursor_y - hazard_class_header_height,
        )
        column_left += hazard_class_width
        box_canvas.line(
            column_left,
            cursor_y - tallest_header_height,
            column_left,
            cursor_y,
        )
        packing_group_header.drawOn(
            box_canvas,
            column_left,
            cursor_y - packing_group_header_height,
        )
        column_left += packing_group_width
        box_canvas.line(
            column_left,
            cursor_y - tallest_header_height,
            column_left,
            top_line_y,
        )
        packing_description_header.drawOn(
            box_canvas,
            column_left,
            cursor_y - packing_description_header_height,
        )
        column_left += packing_description_width
        box_canvas.line(
            column_left,
            cursor_y - tallest_header_height,
            column_left,
            top_line_y,
        )
        packing_instruction_header.drawOn(
            box_canvas,
            column_left,
            cursor_y - packing_instruction_header_height,
        )
        column_left += packing_instruction_width
        box_canvas.line(
            column_left,
            cursor_y - tallest_header_height,
            column_left,
            top_line_y,
        )
        authorization_header.drawOn(
            box_canvas,
            column_left,
            cursor_y - authorization_header_height,
        )

        box_canvas.restoreState()

