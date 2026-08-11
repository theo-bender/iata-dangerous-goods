"""Compatibility exports for the dangerous-goods declaration PDF renderer.

The implementation lives in :mod:`dg._pdf`; keeping this module preserves the
original import path for applications that imported the renderer directly.
"""

from ._pdf import (
    BOX_X_PADDING,
    BOX_Y_PADDING,
    BoxOverflowError,
    COLUMNS,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    TEXT_COLUMN_PADDING,
    TITLE_TEXT,
    ColumnLayout,
    DangerousGoodsCanvas,
    DangerousGoodsDeclaration,
    DocumentLayoutError,
    FieldWrapError,
    HeaderLayout,
    _hazard_text,
    _measure_paragraph,
    _measure_value,
    _value_paragraph,
)

__all__ = [
    "BoxOverflowError",
    "COLUMNS",
    "ColumnLayout",
    "DangerousGoodsCanvas",
    "DangerousGoodsDeclaration",
    "DocumentLayoutError",
    "FieldWrapError",
    "HeaderLayout",
]
