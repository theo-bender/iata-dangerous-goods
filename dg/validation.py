"""Validation engine for matching a shipment to an encoded transport rule."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .models import (
    AircraftType,
    PackingInstructionSection,
    Shipment,
    TransportMode,
)
from .regulations import (
    DangerousGoodsDefinition,
    RuleAvailability,
    SectionDeterminationMethod,
    TransportRule,
)
from .un_numbers import DefinitionKey, UN_DEFINITIONS


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: Severity = Severity.ERROR
    path: str | None = None


@dataclass(frozen=True)
class RuleEvaluation:
    rule: TransportRule
    issues: tuple[ValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return not any(issue.severity is Severity.ERROR for issue in self.issues)


@dataclass(frozen=True)
class ValidationReport:
    shipment: Shipment
    definition: DangerousGoodsDefinition | None
    selected_rule: TransportRule | None
    evaluations: tuple[RuleEvaluation, ...]
    issues: tuple[ValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return self.selected_rule is not None and not any(
            issue.severity is Severity.ERROR for issue in self.issues
        )

    @property
    def declaration_required(self) -> bool:
        return bool(self.selected_rule and self.selected_rule.declaration_required)


MODE_PREFERENCE = (
    TransportMode.DE_MINIMIS,
    TransportMode.EXCEPTED_QUANTITY,
    TransportMode.LIMITED_QUANTITY,
    TransportMode.PASSENGER_AND_CARGO,
    TransportMode.CARGO_AIRCRAFT_ONLY,
)


def _resolve_definition(
    shipment: Shipment,
    definitions: Mapping[DefinitionKey, DangerousGoodsDefinition],
) -> tuple[DangerousGoodsDefinition | None, ValidationIssue | None]:
    exact = definitions.get((shipment.un_number, shipment.definition_variant))
    if exact is not None:
        return exact, None

    candidates = tuple(
        definition
        for (un_number, _), definition in definitions.items()
        if un_number == shipment.un_number
    )
    if shipment.definition_variant is not None:
        return None, ValidationIssue(
            code="unknown_definition_variant",
            message=(
                f"{shipment.formatted_un_number} has no verified "
                f"'{shipment.definition_variant}' variant."
            ),
            path="definition_variant",
        )
    if len(candidates) == 1:
        return candidates[0], None
    if len(candidates) > 1:
        variants = ", ".join(
            sorted(
                definition.variant or "default"
                for definition in candidates
            )
        )
        return None, ValidationIssue(
            code="definition_variant_required",
            message=(
                f"{shipment.formatted_un_number} has multiple proper shipping "
                f"name variants; choose one of: {variants}."
            ),
            path="definition_variant",
        )
    return None, ValidationIssue(
        code="unknown_un_number",
        message=f"{shipment.formatted_un_number} is not in the verified registry.",
        path="un_number",
    )


def validate_shipment(
    shipment: Shipment,
    definitions: Mapping[DefinitionKey, DangerousGoodsDefinition] = UN_DEFINITIONS,
) -> ValidationReport:
    definition, resolution_issue = _resolve_definition(shipment, definitions)
    if definition is None:
        assert resolution_issue is not None
        return ValidationReport(shipment, None, None, (), (resolution_issue,))

    common_issues: list[ValidationIssue] = []
    if not definition.edition.is_effective_on(shipment.ship_date):
        common_issues.append(
            ValidationIssue(
                code="regulatory_edition_not_effective",
                message=(
                    f"IATA DGR edition {definition.edition.edition} is not effective "
                    f"on {shipment.ship_date.isoformat()}."
                ),
                path="ship_date",
            )
        )
    if definition.technical_name_required and not shipment.technical_names:
        common_issues.append(
            ValidationIssue(
                code="technical_name_required",
                message=(
                    f"{shipment.formatted_un_number} requires at least one "
                    "technical or chemical name."
                ),
                path="technical_names",
            )
        )
    resolved_section = shipment.packing_instruction_section
    if (
        definition.section_determination
        is SectionDeterminationMethod.LITHIUM_ION_BATTERY_WATT_HOURS
    ):
        common_issues.append(
            ValidationIssue(
                code="battery_level_below_25_percent",
                message="Indicated battery level must be below 25%.",
                severity=Severity.WARNING,
                path="lithium_ion_batteries",
            )
        )
        if not shipment.lithium_ion_batteries:
            common_issues.append(
                ValidationIssue(
                    code="battery_details_required",
                    message=(
                        "At least one lithium-ion battery Watt-hour rating is "
                        "required to determine Section I or Section II."
                    ),
                    path="lithium_ion_batteries",
                )
            )
            resolved_section = None
        else:
            determined_section = (
                PackingInstructionSection.SECTION_II
                if all(
                    battery.watt_hour_rating <= 100
                    for battery in shipment.lithium_ion_batteries
                )
                else PackingInstructionSection.SECTION_I
            )
            if (
                shipment.packing_instruction_section is not None
                and shipment.packing_instruction_section is not determined_section
            ):
                common_issues.append(
                    ValidationIssue(
                        code="packing_instruction_section_mismatch",
                        message=(
                            f"Battery Watt-hour ratings require Section "
                            f"{determined_section.value}, not Section "
                            f"{shipment.packing_instruction_section.value}."
                        ),
                        path="packing_instruction_section",
                    )
                )
            resolved_section = determined_section
    elif (
        any(rule.packing_instruction_section is not None for rule in definition.rules)
        and resolved_section is None
    ):
        common_issues.append(
            ValidationIssue(
                code="packing_instruction_section_required",
                message=(
                    f"{shipment.formatted_un_number} requires a packing "
                    "instruction section selection."
                ),
                path="packing_instruction_section",
            )
        )

    modes = (
        (shipment.requested_mode,)
        if shipment.requested_mode is not None
        else MODE_PREFERENCE
    )
    rules = [
        definition.rule_for(mode, resolved_section)
        for mode in modes
    ]
    evaluations = tuple(
        _evaluate_rule(shipment, rule)
        for rule in rules
        if rule is not None
    )

    selected = None
    has_common_errors = any(
        issue.severity is Severity.ERROR for issue in common_issues
    )
    if not has_common_errors:
        selected = next(
            (evaluation.rule for evaluation in evaluations if evaluation.is_valid),
            None,
        )

    issues = list(common_issues)
    if selected is None and not has_common_errors:
        if resolved_section is not None and not evaluations:
            issues.append(
                ValidationIssue(
                    code="packing_instruction_section_not_defined",
                    message=(
                        f"No Section {resolved_section.value} "
                        f"rule is encoded for {shipment.formatted_un_number}."
                    ),
                    path="packing_instruction_section",
                )
            )
        elif shipment.requested_mode is not None and not evaluations:
            issues.append(
                ValidationIssue(
                    code="mode_not_defined",
                    message=(
                        f"No {shipment.requested_mode.value} rule is encoded for "
                        f"{shipment.formatted_un_number}."
                    ),
                    path="requested_mode",
                )
            )
        else:
            issues.extend(
                issue
                for evaluation in evaluations
                for issue in evaluation.issues
            )
            issues.append(
                ValidationIssue(
                    code="no_permitted_transport_mode",
                    message="The shipment does not satisfy any evaluated transport mode.",
                )
            )

    return ValidationReport(
        shipment=shipment,
        definition=definition,
        selected_rule=selected,
        evaluations=evaluations,
        issues=tuple(issues),
    )


def _evaluate_rule(shipment: Shipment, rule: TransportRule) -> RuleEvaluation:
    issues: list[ValidationIssue] = []
    if rule.availability is RuleAvailability.FORBIDDEN:
        issues.append(
            ValidationIssue(
                code="mode_forbidden",
                message=f"The {rule.mode.value} mode is forbidden for this entry.",
            )
        )
        return RuleEvaluation(rule, tuple(issues))

    if (
        shipment.aircraft_type is AircraftType.PASSENGER_AND_CARGO
        and rule.mode is TransportMode.CARGO_AIRCRAFT_ONLY
    ):
        issues.append(
            ValidationIssue(
                code="cargo_aircraft_only",
                message="This rule cannot be used on a passenger aircraft.",
                path="aircraft_type",
            )
        )

    for package_index, package in enumerate(shipment.packages):
        package_path = f"packages[{package_index}]"
        if (
            rule.max_package_quantity is not None
            and package.net_quantity > rule.max_package_quantity
        ):
            issues.append(
                ValidationIssue(
                    code="package_quantity_exceeded",
                    message=(
                        f"Package quantity {package.net_quantity} exceeds the "
                        f"{rule.max_package_quantity} limit."
                    ),
                    path=f"{package_path}.net_quantity",
                )
            )
        if (
            rule.permitted_packagings
            and package.packaging not in rule.permitted_packagings
        ):
            issues.append(
                ValidationIssue(
                    code="packaging_not_permitted",
                    message=(
                        f"Packaging '{package.packaging.display_name}' is not permitted."
                    ),
                    path=f"{package_path}.packaging",
                )
            )
        if rule.max_inner_quantity is not None:
            for inner_index, inner in enumerate(package.inner_receptacles):
                if inner.quantity > rule.max_inner_quantity:
                    issues.append(
                        ValidationIssue(
                            code="inner_quantity_exceeded",
                            message=(
                                f"Inner quantity {inner.quantity} exceeds the "
                                f"{rule.max_inner_quantity} limit."
                            ),
                            path=(
                                f"{package_path}.inner_receptacles"
                                f"[{inner_index}].quantity"
                            ),
                        )
                    )

    return RuleEvaluation(rule, tuple(issues))
