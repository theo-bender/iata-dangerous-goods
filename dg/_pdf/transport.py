"""Aircraft and shipment-type sections of the declaration header."""

from reportlab.lib.units import inch

from ..models import AircraftType
from .layout import (
    BOX_X_PADDING,
    BOX_Y_PADDING,
    BoxOverflowError,
    FieldWrapError,
    measure_paragraph as _measure_paragraph,
    measure_value as _measure_value,
)


class TransportRendererMixin:
    """Draw transport details and shipment-type choices."""

    def draw_transport_details_box(self, box_canvas, box_left, box_bottom, box_width, box_height):
        """Draw aircraft limitations and optional origin/destination fields."""
        box_canvas.saveState()
        
        x_padding = BOX_X_PADDING
        y_padding = BOX_Y_PADDING
        content_width = box_width - (2 * x_padding)
        content_top = box_bottom + box_height - y_padding

        # Draw content top-down
        cursor_y = content_top - y_padding

        # Draw box border
        box_canvas.rect(box_left, box_bottom, box_width, box_height, stroke=1, fill=0)

        # Mandatory copy-count statement above the transport details.
        copy_requirement_paragraph, copy_requirement_height = _measure_paragraph(
            "Two completed and signed copies of this Declaration must be handed to the operator.", 
            self.italic_text_style, 
            content_width
        )
        cursor_y -= copy_requirement_height
        copy_requirement_paragraph.drawOn(
            box_canvas,
            box_left + x_padding,
            cursor_y,
        )
        cursor_y -= y_padding

        # Rule below the copy-count statement.
        box_canvas.line(box_left, cursor_y, box_width+box_left, cursor_y)

        # Transport-details subheader.
        transport_header, transport_header_height = _measure_paragraph(
            "TRANSPORT DETAILS", 
            self.box_title_style, 
            content_width
        )
        cursor_y -= transport_header_height
        transport_header.drawOn(box_canvas, box_left + x_padding, cursor_y)
        cursor_y -= y_padding * 2

        # Rule below the transport-details subheader.
        box_canvas.line(box_left, cursor_y, box_width+box_left, cursor_y)

        transport_column_width = box_width / 2
        # The upper transport area is split between aircraft limitations
        # (left) and airport of departure (right).
        box_canvas.line(
            box_left + transport_column_width,
            cursor_y,
            box_left + transport_column_width,
            cursor_y - 1 * inch,
        )
        box_canvas.line(box_left, cursor_y - 1*inch, box_width+box_left, cursor_y - 1*inch)

        aircraft_limitations_label, aircraft_limitations_label_height = _measure_paragraph(
            "This shipment is within the limitations prescribed for:<br/><br/>(delete non-applicable)", 
            self.address_text_style, 
            content_width/2
        )
        aircraft_cursor_y = cursor_y - aircraft_limitations_label_height
        aircraft_limitations_label.drawOn(
            box_canvas,
            box_left + x_padding,
            aircraft_cursor_y,
        )
        aircraft_cursor_y -= y_padding * 2

        # A filled option represents the non-applicable choice being
        # deleted; the selected aircraft limitation remains unfilled.
        if self.declaration_data.aircraft_limitation == AircraftType.PASSENGER_AND_CARGO:
            passenger_cargo_deleted = False
            cargo_only_deleted = True
        elif self.declaration_data.aircraft_limitation == AircraftType.CARGO_ONLY:
            passenger_cargo_deleted = True
            cargo_only_deleted = False
        else:
            raise ValueError('Aircraft type must be PASSENGER_AND_CARGO or CARGO_ONLY')

        passenger_cargo_paragraph, passenger_cargo_height = _measure_paragraph(
            "PASSENGER AND CARGO AIRCRAFT", 
            self.enum_style, 
            transport_column_width / 2 - x_padding * 2
        )
        cargo_only_paragraph, cargo_only_height = _measure_paragraph(
            "CARGO AIRCRAFT ONLY", 
            self.enum_style, 
            transport_column_width / 2 - x_padding * 2
        )

        aircraft_option_y = aircraft_cursor_y - passenger_cargo_height
        passenger_cargo_paragraph.drawOn(
            box_canvas,
            box_left + x_padding,
            aircraft_option_y,
        )
        cargo_label_x = box_left + (transport_column_width / 2) + x_padding
        # Preserve the established PDF position. The old expression omitted
        # box_left; keeping that discrepancy explicit prevents it from being
        # mistaken for the second enum box's true origin in future changes.
        cargo_label_compatibility_offset = (
            transport_column_width / 2
        ) - box_left
        cargo_only_paragraph.drawOn(
            box_canvas,
            cargo_label_x + cargo_label_compatibility_offset,
            aircraft_option_y,
        )

        # Draw the deletion boxes around both aircraft options.
        aircraft_option_width = transport_column_width / 2
        box_canvas.rect(
            box_left,
            aircraft_option_y - y_padding,
            aircraft_option_width,
            passenger_cargo_height + y_padding * 2,
            stroke=1,
            fill=passenger_cargo_deleted,
        )
        box_canvas.rect(
            box_left + aircraft_option_width,
            aircraft_option_y - y_padding,
            aircraft_option_width,
            cargo_only_height + y_padding * 2,
            stroke=1,
            fill=cargo_only_deleted,
        )

        # Airport of departure occupies the upper-right transport cell.
        departure_label, departure_label_height = _measure_paragraph(
            "Airport of Departure (optional)",
            self.address_text_style, 
            content_width/2
        )
        departure_cursor_y = cursor_y - departure_label_height
        departure_label.drawOn(
            box_canvas,
            box_left + transport_column_width + x_padding,
            departure_cursor_y,
        )
        departure_cursor_y -= y_padding * 2

        if self.declaration_data.departure_airport:
            departure_paragraph, departure_height = _measure_value(
                self.declaration_data.departure_airport, 
                self.address_text_style, 
                content_width/2
            )

            available_height = departure_cursor_y - (cursor_y - 1*inch)
            if departure_height > available_height:
                raise BoxOverflowError(
                    box_name="Airport of departure",
                    required=departure_height,
                    available=available_height,
                )

            departure_paragraph.drawOn(
                box_canvas,
                box_left + transport_column_width + x_padding,
                departure_cursor_y - departure_height,
            )

        cursor_y -= 1 * inch

        destination_label, destination_label_height = _measure_paragraph(
            "Airport of Destination (optional)",
            self.address_text_style, 
            content_width
        )
        cursor_y -= destination_label_height
        destination_label.drawOn(box_canvas, box_left + x_padding, cursor_y)
        cursor_y -= y_padding*2

        if self.declaration_data.destination_airport:
            destination_paragraph, destination_height = _measure_value(
                self.declaration_data.destination_airport, 
                self.address_text_style, 
                content_width
            )

            available_height = cursor_y - box_bottom
            if destination_height > available_height:
                raise BoxOverflowError(
                    box_name="Airport of destination",
                    required=destination_height,
                    available=available_height,
                )

            destination_paragraph.drawOn(
                box_canvas,
                box_left + x_padding,
                cursor_y - destination_height,
            )

        box_canvas.restoreState()

    def draw_shipment_type_box(self, box_canvas, box_left, box_bottom, box_width, box_height):
        """Draw the regulatory warning and radioactive shipment choice."""
        box_canvas.saveState()
                    
        x_padding = BOX_X_PADDING
        y_padding = BOX_Y_PADDING
        content_width = box_width - (2 * x_padding)
        content_top = box_bottom + box_height - y_padding

        # Draw content top-down
        cursor_y = content_top - y_padding

        # Draw box border
        box_canvas.rect(box_left, box_bottom, box_width, box_height, stroke=1, fill=0)

        # Regulatory warning.
        warning_paragraph, warning_height = _measure_paragraph(
            "WARNING<br/><br/>Failure to comply in all respects with the applicable Dangerous Goods Regulations may be in breach of the applicable law, subject to legal penalties.", 
            self.box_title_style, 
            content_width
        )
        cursor_y -= warning_height
        warning_paragraph.drawOn(box_canvas, box_left + x_padding, cursor_y)
        cursor_y -= 0.695*inch

        # Draw line under warning statement
        box_canvas.line(box_left, cursor_y, box_width+box_left, cursor_y)

        cursor_y -= y_padding*2

        # Shipment-type selection.
        shipment_type_label, shipment_type_label_height = _measure_paragraph(
            "Shipment type: (delete non-applicable)", 
            self.address_text_style, 
            content_width
        )
        cursor_y -= shipment_type_label_height
        shipment_type_label.drawOn(box_canvas, box_left + x_padding, cursor_y)
        cursor_y -= y_padding*3


        non_radioactive_paragraph, non_radioactive_height = _measure_paragraph(
            "NON-RADIOACTIVE", 
            self.enum_style, 
            content_width/2
        )
        cursor_y -= non_radioactive_height
        non_radioactive_paragraph.drawOn(
            box_canvas,
            box_left + x_padding,
            cursor_y,
        )

        radioactive_paragraph, radioactive_height = _measure_paragraph(
            "RADIOACTIVE", 
            self.enum_style, 
            content_width/2
        )
        radioactive_paragraph.drawOn(
            box_canvas,
            box_left + (box_width / 2) + x_padding,
            cursor_y,
        )

        # As with aircraft limitations, filling deletes the non-applicable
        # option and leaves the selected shipment type visible.
        shipment_type_width = box_width / 2
        box_canvas.rect(
            box_left,
            cursor_y - y_padding,
            shipment_type_width,
            non_radioactive_height + y_padding * 2,
            stroke=1,
            fill=self.declaration_data.is_radioactive,
        )
        box_canvas.rect(
            box_left + shipment_type_width,
            cursor_y - y_padding,
            shipment_type_width,
            radioactive_height + y_padding * 2,
            stroke=1,
            fill=not self.declaration_data.is_radioactive,
        )

        box_canvas.restoreState()
