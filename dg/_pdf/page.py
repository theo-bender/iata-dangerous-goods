"""Compose page decorations, header, table rules, and footer."""

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Frame, PageTemplate

from .footer import FooterRendererMixin
from .header import HeaderRendererMixin
from .layout import COLUMNS, PAGE_HEIGHT


HATCH_BAND_WIDTH = 0.18 * inch
HATCH_BLOCK_HEIGHT = 0.32 * inch
HATCH_BLOCK_GAP = 0.08 * inch


class DeclarationPageRenderer(HeaderRendererMixin, FooterRendererMixin):
    """Coordinate the independently implemented form sections."""

    def draw_hatched_margins(self, page_canvas, doc):
        """Draw IATA-style red hatching in both page margins."""

        page_canvas.saveState()
        page_canvas.setFillColor(colors.red)

        page_width, page_height = doc.pagesize
        band_left_edges = (
            (doc.leftMargin - HATCH_BAND_WIDTH) / 2,
            page_width - (doc.rightMargin + HATCH_BAND_WIDTH) / 2,
        )

        # Begin below the page so the first pair of blocks is clipped cleanly
        # at the bottom edge. ReportLab also clips the final pair at the top.
        block_y = -HATCH_BAND_WIDTH
        block_pitch = HATCH_BLOCK_HEIGHT + HATCH_BLOCK_GAP
        while block_y < page_height:
            for band_x in band_left_edges:
                path = page_canvas.beginPath()
                path.moveTo(band_x, block_y)
                path.lineTo(
                    band_x + HATCH_BAND_WIDTH,
                    block_y + HATCH_BAND_WIDTH,
                )
                path.lineTo(
                    band_x + HATCH_BAND_WIDTH,
                    block_y + HATCH_BAND_WIDTH + HATCH_BLOCK_HEIGHT,
                )
                path.lineTo(band_x, block_y + HATCH_BLOCK_HEIGHT)
                path.close()
                page_canvas.drawPath(path, stroke=0, fill=1)
            block_y += block_pitch

        page_canvas.restoreState()

    def draw_story_vertical_rules(self, page_canvas, doc):
        """Draw continuous table rules behind the flowing story rows."""

        page_canvas.saveState()

        x_left = doc.leftMargin
        x_right = doc.leftMargin + doc.width
        y_bottom = doc.bottomMargin
        y_top = PAGE_HEIGHT - doc.topMargin

        column_widths = COLUMNS.widths(doc.width)

        # Left outer border
        page_canvas.line(x_left, y_bottom, x_left, y_top)

        # Internal separators
        separator_x = x_left
        for column_width in column_widths[:-1]:
            separator_x += column_width
            page_canvas.line(separator_x, y_bottom, separator_x, y_top)

        # Right outer border
        page_canvas.line(x_right, y_bottom, x_right, y_top)

        page_canvas.restoreState()

    def draw_page(self, page_canvas, doc):
        # onPage runs before ReportLab places the flowing story, leaving the
        # fixed form and its rules behind the table-cell text.
        self.draw_header(page_canvas, doc)
        self.draw_story_vertical_rules(page_canvas, doc)
        self.draw_footer(page_canvas, doc)

    def draw_page_with_hatched_margins(self, page_canvas, doc):
        """Draw the optional margins and the established declaration form."""

        self.draw_hatched_margins(page_canvas, doc)
        self.draw_page(page_canvas, doc)

    def _build_page_template(self, doc, *, hatched_margins=False):
        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id="content",
        )
        # Keep ReportLab's default frame padding. It is already reflected in
        # the established table position and therefore part of the output.
        on_page = (
            self.draw_page_with_hatched_margins
            if hatched_margins
            else self.draw_page
        )
        return PageTemplate(
            id="main",
            frames=[frame],
            onPage=on_page,
        )

