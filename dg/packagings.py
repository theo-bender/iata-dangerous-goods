"""Known physical packaging configurations used by this application.

A catalog entry describes packaging the shipper owns or intends to use. It is
not permission to use that packaging for dangerous goods. A verified
``TransportRule`` must separately include the entry in its
``permitted_packagings``.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class PackagingDefinition:
    """One stable, human-readable physical packaging configuration."""

    code: str
    display_name: str
    outer_packaging: str
    inner_packaging: str | None
    protective_materials: tuple[str, ...]
    description: str
    dgd_packaging_description: str | None
    verified_against_dgr: bool = False
    source_references: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _CODE_PATTERN.fullmatch(self.code):
            raise ValueError(
                "Packaging code must use lowercase letters, numbers, and underscores"
            )
        required_text = (self.display_name, self.outer_packaging, self.description)
        if any(not value.strip() for value in required_text):
            raise ValueError("Packaging name, outer packaging, and description are required")
        if self.inner_packaging is not None and not self.inner_packaging.strip():
            raise ValueError("Inner packaging cannot be blank")
        if any(not material.strip() for material in self.protective_materials):
            raise ValueError("Protective materials cannot be blank")
        if (
            self.dgd_packaging_description is not None
            and not self.dgd_packaging_description.strip()
        ):
            raise ValueError("DGD packaging description cannot be blank")
        if self.verified_against_dgr and not self.source_references:
            raise ValueError("Verified packaging requires a DGR source reference")
        if self.verified_against_dgr and self.dgd_packaging_description is None:
            raise ValueError("Verified packaging requires a DGD packaging description")


PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE = PackagingDefinition(
    code="plastic_bottle_in_4g_box_with_vermiculite",
    display_name="Plastic bottle in 4G box with vermiculite",
    outer_packaging="4G UN specification fiberboard box",
    inner_packaging="Plastic bottle",
    protective_materials=("Vermiculite",),
    description=(
        "Plastic bottle packed in a 4G UN specification fiberboard box with vermiculite surrounding the bottle."
    ),
    dgd_packaging_description="Fibreboard Box",
    notes=(
        "Ensure box is completely filled with vermiculite and that total packed box weight does not exceed 5 KG. See spec box SOP for more details",
    ),
)


EQUIPMENT_IN_HARD_SHELL_CASE_WITH_FOAM = PackagingDefinition(
    code="equipment_in_hard_shell_case_with_foam",
    display_name="Laptop or equipment in hard-shell case with foam",
    outer_packaging="Hard-shell Pelican-style case",
    inner_packaging="Laptop or other equipment",
    protective_materials=("Fitted protective foam",),
    description=(
        "Laptop or other equipment secured inside a hard-shell Pelican-style case with fitted protective foam."
    ),
    dgd_packaging_description=None,
)


BOTTLE_OR_CARTRIDGE_IN_ABSORBENT_MAT_AND_BAG = PackagingDefinition(
    code="bottle_or_cartridge_in_absorbent_mat_and_bag",
    display_name="Bottle or cartridge in absorbent mat and plastic bag",
    outer_packaging="Plastic bag",
    inner_packaging="Bottle or cartridge",
    protective_materials=("Absorbent mat",),
    description=(
        "Bottle or cartridge wrapped in absorbent mat and enclosed in a plastic bag. Plastic bag is then packed inside cardboard box."
    ),
    dgd_packaging_description="Fibreboard Box",
    notes=(
        "Use only branded boxes as these boxes have been stack-and-drop tested."
    ),
)


PACKAGING_DEFINITIONS: dict[str, PackagingDefinition] = {
    definition.code: definition
    for definition in (
        PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE,
        EQUIPMENT_IN_HARD_SHELL_CASE_WITH_FOAM,
        BOTTLE_OR_CARTRIDGE_IN_ABSORBENT_MAT_AND_BAG,
    )
}


def get_packaging(code: str) -> PackagingDefinition | None:
    return PACKAGING_DEFINITIONS.get(code)
