"""ReportLab canvas support for final declaration page counts."""

from reportlab.pdfgen import canvas


class DangerousGoodsCanvas(canvas.Canvas):
    """Canvas that adds final page counts after all pages are known."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        # Defer emitting the page so save() can replay it with "Page X of Y".
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
            # This coordinate is part of the established form layout.
            309,
            720,
            f"Page {self._pageNumber} of {page_count} Pages",
        )
