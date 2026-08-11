"""Compose header, flowing table rules, and footer into a page template."""

from reportlab.platypus import Frame, PageTemplate

from .footer import FooterRendererMixin
from .header import HeaderRendererMixin
from .layout import COLUMNS, PAGE_HEIGHT


class DeclarationPageRenderer(HeaderRendererMixin, FooterRendererMixin):
    """Coordinate the independently implemented form sections."""

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

    def _build_page_template(self, doc):
        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id="content",
        )
        # Keep ReportLab's default frame padding. It is already reflected in
        # the established table position and therefore part of the output.
        return PageTemplate(
            id="main",
            frames=[frame],
            onPage=self.draw_page,
        )

