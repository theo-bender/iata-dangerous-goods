import unittest

from dg.packagings import (
    BOTTLE_OR_CARTRIDGE_IN_ABSORBENT_MAT_AND_BAG,
    EQUIPMENT_IN_HARD_SHELL_CASE_WITH_FOAM,
    PACKAGING_DEFINITIONS,
    PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE,
    PackagingDefinition,
    get_packaging,
)


class PackagingCatalogTests(unittest.TestCase):
    def test_contains_the_three_starter_configurations(self) -> None:
        self.assertEqual(
            set(PACKAGING_DEFINITIONS),
            {
                PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE.code,
                EQUIPMENT_IN_HARD_SHELL_CASE_WITH_FOAM.code,
                BOTTLE_OR_CARTRIDGE_IN_ABSORBENT_MAT_AND_BAG.code,
            },
        )

    def test_catalog_entries_are_not_regulatory_approvals(self) -> None:
        self.assertTrue(
            all(
                not definition.verified_against_dgr
                for definition in PACKAGING_DEFINITIONS.values()
            )
        )

    def test_looks_up_packaging_by_stable_code(self) -> None:
        definition = get_packaging(
            PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE.code
        )

        self.assertIs(definition, PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE)
        self.assertIsNone(get_packaging("unknown_packaging"))

    def test_verified_packaging_requires_a_source_reference(self) -> None:
        with self.assertRaisesRegex(ValueError, "source reference"):
            PackagingDefinition(
                code="test_packaging",
                display_name="Test packaging",
                outer_packaging="Test box",
                inner_packaging=None,
                protective_materials=(),
                description="Test-only packaging.",
                dgd_packaging_description="Test Box",
                verified_against_dgr=True,
            )


if __name__ == "__main__":
    unittest.main()
