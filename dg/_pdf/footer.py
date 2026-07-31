"""Footer-section renderers for the dangerous-goods declaration form."""

from reportlab.lib.units import inch

from .layout import (
    BOX_X_PADDING,
    BOX_Y_PADDING,
    BoxOverflowError,
    FieldWrapError,
    measure_paragraph as _measure_paragraph,
    measure_value as _measure_value,
)


class FooterRendererMixin:
    """Draw the fixed footer sections of each declaration page."""

    def draw_additional_handling_box(self, box_canvas, box_left, box_bottom, box_width, box_height):
        """Draw optional additional-handling information in the footer."""

        box_canvas.saveState()
                                
        x_padding = BOX_X_PADDING
        y_padding = BOX_Y_PADDING
        content_width = box_width - (2 * x_padding)
        content_top = box_bottom + box_height - y_padding

        # Draw content top-down
        cursor_y = content_top

        # Draw box border
        box_canvas.rect(box_left, box_bottom, box_width, box_height, stroke=1, fill=0)

        # subheader
        handling_information_label, handling_information_label_height = _measure_paragraph(
            "Additional Handling Information", 
            self.box_title_style, 
            content_width
        )
        cursor_y -= handling_information_label_height
        handling_information_label.drawOn(
            box_canvas,
            box_left + x_padding,
            cursor_y,
        )
        cursor_y -= y_padding

        if self.declaration_data.additional_handling_information:
            handling_information_paragraph, handling_information_height = _measure_value(
                self.declaration_data.additional_handling_information, 
                self.address_text_style, 
                content_width
            )

            available_height = cursor_y - box_bottom
            if handling_information_height > available_height:
                raise BoxOverflowError(
                    box_name="Additional handling information",
                    required=handling_information_height,
                    available=available_height,
                )

            handling_information_paragraph.drawOn(
                box_canvas,
                box_left + x_padding,
                cursor_y - handling_information_height,
            )

        box_canvas.restoreState()

    def draw_signature_box(self, box_canvas, box_left, box_bottom, box_width, box_height):
        """Draw the declaration statement and signatory details."""

        box_canvas.saveState()
                                
        x_padding = BOX_X_PADDING
        y_padding = BOX_Y_PADDING
        content_width = box_width - (2 * x_padding)
        content_top = box_bottom + box_height - y_padding

        declaration_section_left = box_left
        signature_section_left = box_left + (box_width * (2 / 3))

        # Draw content top-down
        declaration_cursor_y = content_top
        signature_cursor_y = content_top

        # Draw box border
        box_canvas.rect(box_left, box_bottom, box_width, box_height, stroke=1, fill=0)
        # The declaration statement uses two-thirds of the footer; the
        # signatory details occupy the remaining third.
        box_canvas.line(
            signature_section_left,
            box_bottom,
            signature_section_left,
            box_bottom + box_height,
        )

        declaration_paragraph, declaration_height = _measure_paragraph(
            "I hereby declare that the contents of this consignment are fully and accurately described above by the proper shipping name, and are classified, packaged, marked and labelled/placarded, and are in all respects in proper condition for transport according to applicable international and national governmental regulations. I declare that all of the applicable air transport requirements have been met.", 
            self.address_text_style, 
            content_width * (2/3)
        )
        declaration_cursor_y -= declaration_height
        declaration_paragraph.drawOn(
            box_canvas,
            declaration_section_left + x_padding,
            declaration_cursor_y,
        )
        declaration_cursor_y -= y_padding


        # Signatory name.
        signatory_name_label, signatory_name_label_height = _measure_paragraph(
            "Name of Signatory", 
            self.box_title_style, 
            content_width * (1/3)
        )
        signature_cursor_y -= signatory_name_label_height
        signatory_name_label.drawOn(
            box_canvas,
            signature_section_left + x_padding,
            signature_cursor_y,
        )
        signature_cursor_y -= y_padding

        signatory_name_paragraph, signatory_name_height = _measure_value(
            self.declaration_data.signatory, 
            self.address_text_style, 
            content_width * (1/3)
        )
        signature_cursor_y -= signatory_name_height
        # Signatory fields must remain on one line in the fixed-width cell.
        if signatory_name_height > self.address_text_style.leading * 1.2:
            raise FieldWrapError(
                field_name='Signatory Name',
                value=self.declaration_data.signatory,
            )
        signatory_name_paragraph.drawOn(
            box_canvas,
            signature_section_left + x_padding,
            signature_cursor_y,
        )


        # Signatory date.
        signatory_date_label, signatory_date_label_height = _measure_paragraph(
            "Date", 
            self.box_title_style, 
            content_width * (1/3)
        )
        signature_cursor_y -= signatory_date_label_height
        signatory_date_label.drawOn(
            box_canvas,
            signature_section_left + x_padding,
            signature_cursor_y,
        )
        signature_cursor_y -= y_padding

        signatory_date_paragraph, signatory_date_height = _measure_value(
            self.declaration_data.signatory_date.strftime("%Y-%m-%d"),
            self.address_text_style, 
            content_width * (1/3)
        )
        signature_cursor_y -= signatory_date_height
        if signatory_date_height > self.address_text_style.leading * 1.2:
            raise FieldWrapError(
                field_name='Signatory Date',
                value=self.declaration_data.signatory_date.strftime("%Y-%m-%d"),
            )
        signatory_date_paragraph.drawOn(
            box_canvas,
            signature_section_left + x_padding,
            signature_cursor_y,
        )

        # Empty signature area label.
        signature_label, signature_label_height = _measure_paragraph(
            "Signature<br/>(See warning above)", 
            self.box_title_style, 
            content_width * (1/3)
        )
        signature_cursor_y -= signature_label_height
        signature_label.drawOn(
            box_canvas,
            signature_section_left + x_padding,
            signature_cursor_y,
        )
        signature_cursor_y -= y_padding

        box_canvas.restoreState()

    def draw_footer(self, footer_canvas, doc):

        page_left = doc.leftMargin
        footer_top = doc.bottomMargin
        additional_handling_height = 0.6 * inch
        signature_box_height = 1.275 * inch

        additional_handling_bottom = (
            footer_top - additional_handling_height
        )
        signature_box_bottom = (
            additional_handling_bottom - signature_box_height
        )

        self.draw_additional_handling_box(
            footer_canvas,
            page_left,
            additional_handling_bottom,
            doc.width,
            additional_handling_height,
        )

        self.draw_signature_box(
            footer_canvas,
            page_left,
            signature_box_bottom,
            doc.width,
            signature_box_height,
        )
