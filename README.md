# IATA dangerous-goods validator

A deliberately small Python validator for a shipper who handles a known set of
dangerous goods. It checks package and inner-receptacle quantities, approved
packaging configurations, aircraft limitations, and whether the selected rule
requires a Shipper's Declaration.

> [!IMPORTANT]
> This project is decision support, not a replacement for the current IATA DGR,
> its addenda, applicable national rules, operator variations, or trained-person
> review.

## Installation

`iata-dangerous-goods` requires Python 3.11 or later. ReportLab is installed as
a runtime dependency for rendering Shipper's Declaration PDFs.

```console
python -m pip install iata-dangerous-goods
```

The PyPI distribution is named `iata-dangerous-goods`; the Python import package
is named `dg`:

```python
from dg import Shipment, validate_shipment
```

## Design

- `dg/models.py` contains facts about a proposed shipment.
- `dg/regulations.py` defines versioned regulatory records and transport rules.
- `dg/packagings.py` catalogs the physical packaging configurations in use.
- `dg/un_numbers.py` is the manually verified registry for the supported
  UN numbers.
- `dg/validation.py` evaluates eligible modes and returns an explainable report.
- `dg/declarations.py` builds structured declaration fields only after a
  shipment passes validation.

Regulatory data is rejected outside its encoded effective dates. Forbidden
transport is represented explicitly rather than as a zero quantity.

`Shipment` does not require the caller to choose an aircraft category. After
validation, `ValidationReport.aircraft_limitation` is derived from the selected
transport rule and is used automatically when declaration data is generated.

## Add a UN number

Transcribe each definition from an authorized copy of the current IATA DGR and
check the List of Dangerous Goods entry, every referenced packing instruction,
special provisions, current addenda, and relevant operator/state variations.
Then create a `DangerousGoodsDefinition` in `dg/un_numbers.py` and register it.

When one UN number has multiple proper shipping names, give each definition a
stable `variant` and register both. UN3481 is represented by separate
`packed_with_equipment` (PI 966) and `contained_in_equipment` (PI 967)
definitions. A shipment selects the applicable entry:

```python
Shipment(
    un_number=3481,
    definition_variant="contained_in_equipment",
    lithium_ion_batteries=(
        LithiumIonBattery(watt_hour_rating=Decimal("95"), quantity=2),
    ),
    # ...
)
```

`TransportRule.packing_instruction_section` distinguishes Section I, IA, IB,
and II rules. Sectioned definitions must encode separate rules for their
different quantity, packaging, aircraft, and declaration requirements. For
UN3481, set `section_determination` to
`SectionDeterminationMethod.LITHIUM_ION_BATTERY_WATT_HOURS`. Every battery at
or below 100 Wh then selects Section II; any battery above 100 Wh selects
Section I. This simplified application accepts batteries only, not individual
cells. Battery reports also warn that the indicated battery level must be below
25%; that warning does not collect or verify the actual level.

Packaging is represented by stable application-owned codes. Each code should
describe one exact configuration you actually use; for example, outer package,
inner receptacles, closures, absorbent material, and performance standard.

The starter catalog contains:

- Plastic bottle in a 4G UN specification box with vermiculite
- Laptop or equipment in a hard-shell Pelican-style case with foam
- Bottle or cartridge wrapped in absorbent mat inside a plastic bag

Cataloging a configuration does not approve it for dangerous-goods transport.
After checking the applicable packing instruction, reference the catalog entry
from the corresponding rule:

```python
from .packagings import PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE

TransportRule(
    # ...
    permitted_packagings=(
        PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE,
    ),
)
```

Shipment packages also use the catalog object directly:

```python
Package(
    packaging=PLASTIC_BOTTLE_IN_4G_BOX_WITH_VERMICULITE,
    # ...
)
```

`Package.packaging_code` remains available when a stable string identifier is
needed for JSON, forms, or database storage.

## Group packages in overpacks

An `Overpack` is a handling unit around one or more completed packages; it is
not a packaging configuration and does not belong in the packaging catalog.
Every enclosed `Package` is still checked independently against the selected
packing instruction, including its package and inner-receptacle quantities.

Import `Overpack` from the public package and place completed packages inside
it. `Shipment.packages` contains packages that remain loose:

```python
from dg import Overpack

loose_only = Shipment(
    un_number=3266,
    packages=(package_a,),
    # remaining shipment fields...
)

overpack_only = Shipment(
    un_number=3266,
    packages=(),
    overpacks=(
        Overpack(packages=(package_a, package_b), identifier="OP-1"),
    ),
    # remaining shipment fields...
)

mixed = Shipment(
    un_number=3266,
    packages=(package_a,),
    overpacks=(
        Overpack(packages=(package_b,), identifier="OP-1"),
    ),
    # remaining shipment fields...
)
```

A single overpack may omit its identifier. When a shipment contains multiple
overpacks, every overpack must have a unique, nonblank identifier matching its
physical identification mark. Declaration generation creates a separate line
for loose packages and for each overpack, adds `Overpack used`, and includes
the identifier and total dangerous-goods quantity. Packages in the same
overpack that have the same controlled DGD packaging description and
per-package quantity are consolidated.

Each overpack's declaration entry is displayed on separate lines, with the
identifier between the required overpack statement and package details:

```text
2 Fibreboard Boxes x 1 L
Overpack used
#OP-1
Net quantity 2 L
```

Overpack support is intentionally limited to the shipment's one dangerous-
goods definition. The library does not currently validate mixed-UN
compatibility or generate and inspect physical overpack marks and labels.

Each starter entry has `verified_against_dgr=False`. Set that flag and add its
packing-instruction source references only after checking the exact physical
configuration against the current DGR.

`PackagingDefinition.dgd_packaging_description` stores the controlled package
type wording required in the declaration's Quantity and Type of Packing field.
For example, the 4G box configurations use `Fibreboard Box`, producing output
such as `1 Fibreboard Box x 4 L`. Friendly display names and free-text packaging
instructions are never substituted into this DGD field. Declaration generation
stops if the selected packaging has no verified DGD wording.

For a generic or N.O.S. entry that requires a technical name, set
`technical_name_required=True` on its `DangerousGoodsDefinition`. Supply the
shipment-specific value when creating the shipment:

```python
Shipment(
    # ...
    technical_names=("chemical A", "chemical B"),
)
```

The declaration builder renders these immediately after the base proper
shipping name as `PROPER SHIPPING NAME (chemical A, chemical B)`.

Build the declaration PDF in memory when it is ready to return from an API,
attach to a message, or store in an object store:

```python
from dg import DangerousGoodsDeclaration

pdf_bytes = DangerousGoodsDeclaration(declaration).build()
```

To include the red diagonal hatching used in the left and right margins of
IATA-style declarations, enable it for that build:

```python
pdf_bytes = DangerousGoodsDeclaration(declaration).build(
    hatched_margins=True,
)
```

Passing a filename remains available when an explicit file copy is useful.
The same PDF bytes are returned in either case:

```python
pdf_bytes = DangerousGoodsDeclaration(declaration).build("declaration.pdf")
```

The option can also be used when writing a file:

```python
pdf_bytes = DangerousGoodsDeclaration(declaration).build(
    "declaration.pdf",
    hatched_margins=True,
)
```

## Run the tests

Install an editable development copy with the packaging tools:

```powershell
python -m pip install -e ".[dev]"
```

```powershell
python -m unittest discover -v
```

Build the same wheel and source archive that are published to PyPI:

```powershell
python -m build
python -m twine check dist/*
```

See the [release guide](https://github.com/theo-bender/iata-dangerous-goods/blob/main/RELEASING.md)
for the Trusted Publishing release process.

The test UN9999 entry is fictional and exists only inside the test suite.
