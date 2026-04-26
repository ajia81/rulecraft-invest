"""Skills 파일 검증 게이트 (Stage 3-3).

docs/overlay-rules.md 섹션 3, 5, 8의 정책에 따라 다음 5가지 위반을 사전에 차단한다.
검증은 load_skills() 후 merge_rules() 전 시점에 호출되어야 한다.

검증 항목:
1. extend 룰의 signal/severity/visualization이 base와 일치 (섹션 5)
2. inherit 룰의 최소 키 구조 (섹션 8) — rule_id, merge_policy, inherit_from 만 허용
   (rule_name은 메타로 warning만)
3. inherit_from 값이 'base'이고 rule_id가 base에 존재
4. extends 값이 base에 존재
5. asset_only 룰의 rule_id가 base와 충돌 시 warning
"""

from __future__ import annotations

from typing import Any


_INHERIT_REQUIRED_KEYS = {"rule_id", "merge_policy", "inherit_from"}
_INHERIT_SOFT_KEYS = {"rule_name"}

_EXTEND_INHERITED_FIELDS = ("signal", "severity", "visualization")


def _asset_label(rule: dict) -> str:
    asset_types = rule.get("asset_types") or []
    return ",".join(asset_types) if asset_types else ""


def _file_hint(rule: dict) -> str | None:
    """asset_types에서 추정한 Skills 파일 경로 (정확하지 않을 수 있음)."""
    if rule.get("merge_policy") == "base":
        return "skills/base.md"
    asset_types = rule.get("asset_types") or []
    if not asset_types:
        return None
    asset = asset_types[0]
    return f"skills/asset_{asset}.md"


def _make_violation(
    rule: dict,
    violation_type: str,
    message: str,
) -> dict:
    return {
        "rule_id": rule.get("rule_id", "?"),
        "asset_type": _asset_label(rule),
        "policy": rule.get("merge_policy", "?"),
        "violation_type": violation_type,
        "message": message,
        "file_hint": _file_hint(rule),
    }


def _validate_extend(
    rule: dict,
    base_by_id: dict[str, dict],
    errors: list[dict],
    warnings: list[dict],
) -> None:
    rule_id = rule.get("rule_id", "?")
    asset = _asset_label(rule)
    asset_label = f"({asset})" if asset else ""

    extends_val = rule.get("extends")
    target_rule: dict | None = None

    if extends_val is not None:
        # 검증 4: extends 참조 유효성
        if extends_val not in base_by_id:
            errors.append(_make_violation(
                rule,
                "extends_not_found",
                f"extend 룰 '{rule_id}'{asset_label}이 참조하는 extends='{extends_val}'이 base.md에 존재하지 않습니다.",
            ))
            return
        target_rule = base_by_id[extends_val]
    elif rule_id in base_by_id:
        target_rule = base_by_id[rule_id]
    else:
        errors.append(_make_violation(
            rule,
            "extend_target_missing",
            f"extend 룰 '{rule_id}'{asset_label}에 extends 키도 없고 같은 rule_id의 base 룰도 존재하지 않습니다.",
        ))
        return

    # 검증 1: signal/severity/visualization 일치
    for key in _EXTEND_INHERITED_FIELDS:
        ext_val = rule.get(key)
        base_val = target_rule.get(key)
        if ext_val is not None and ext_val != base_val:
            errors.append(_make_violation(
                rule,
                f"{key}_mismatch",
                f"extend 룰 '{rule_id}'{asset_label}의 {key} '{ext_val}'이 base의 '{base_val}'과 일치하지 않습니다.",
            ))


def _validate_inherit(
    rule: dict,
    base_by_id: dict[str, dict],
    errors: list[dict],
    warnings: list[dict],
) -> None:
    rule_id = rule.get("rule_id", "?")
    asset = _asset_label(rule)
    asset_label = f"({asset})" if asset else ""

    # 검증 2: 최소 키 구조
    actual_keys = set(rule.keys())
    extra_keys = actual_keys - _INHERIT_REQUIRED_KEYS - _INHERIT_SOFT_KEYS
    soft_extra = (actual_keys & _INHERIT_SOFT_KEYS)
    missing = _INHERIT_REQUIRED_KEYS - actual_keys

    for key in sorted(missing):
        errors.append(_make_violation(
            rule,
            "inherit_required_key_missing",
            f"inherit 룰 '{rule_id}'{asset_label}에 필수 키 '{key}'가 누락되었습니다.",
        ))

    for key in sorted(extra_keys):
        errors.append(_make_violation(
            rule,
            "inherit_extra_key",
            f"inherit 룰 '{rule_id}'{asset_label}에 허용되지 않은 키 '{key}'가 정의되어 있습니다.",
        ))

    for key in sorted(soft_extra):
        warnings.append(_make_violation(
            rule,
            "inherit_metadata_key",
            f"inherit 룰 '{rule_id}'{asset_label}에 메타 키 '{key}'가 포함되어 있습니다 (동작에는 영향 없음).",
        ))

    # 검증 3-1: inherit_from = 'base'
    inherit_from = rule.get("inherit_from")
    if "inherit_from" in actual_keys and inherit_from != "base":
        errors.append(_make_violation(
            rule,
            "inherit_from_invalid",
            f"inherit 룰 '{rule_id}'{asset_label}의 inherit_from='{inherit_from}'은 'base'여야 합니다.",
        ))

    # 검증 3-2: rule_id가 base 룰에 존재
    if rule_id not in base_by_id:
        errors.append(_make_violation(
            rule,
            "inherit_target_not_found",
            f"inherit 룰 '{rule_id}'{asset_label}이 참조하는 rule_id가 base.md에 존재하지 않습니다.",
        ))


def _validate_asset_only(
    rule: dict,
    base_by_id: dict[str, dict],
    errors: list[dict],
    warnings: list[dict],
) -> None:
    rule_id = rule.get("rule_id", "?")
    asset = _asset_label(rule)
    asset_label = f"({asset})" if asset else ""

    # 검증 5: base와 rule_id 충돌 (warning)
    if rule_id in base_by_id:
        warnings.append(_make_violation(
            rule,
            "asset_only_collision_with_base",
            f"asset_only 룰 '{rule_id}'{asset_label}의 rule_id가 base 룰과 중복됩니다. "
            f"base 룰이 자동으로 평가에 포함되므로 의도치 않은 중복 평가가 발생할 수 있습니다.",
        ))


def validate_skills(
    rules: list[dict],
    templates: list[dict] | None = None,
) -> dict[str, Any]:
    """Skills 룰 리스트를 검증하고 결과 dict를 반환.

    Returns:
        {
            "passed":   True | False (errors 없으면 True),
            "errors":   [violation dict, ...],
            "warnings": [violation dict, ...],
        }
    """
    errors: list[dict] = []
    warnings: list[dict] = []

    base_by_id: dict[str, dict] = {
        r["rule_id"]: r
        for r in rules
        if r.get("merge_policy") == "base" and r.get("rule_id")
    }

    for rule in rules:
        if not rule.get("rule_id"):
            continue
        policy = rule.get("merge_policy")

        if policy == "extend":
            _validate_extend(rule, base_by_id, errors, warnings)
        elif policy == "inherit":
            _validate_inherit(rule, base_by_id, errors, warnings)
        elif policy == "asset_only":
            _validate_asset_only(rule, base_by_id, errors, warnings)
        # base / override / 기타 정책은 별도 검증 없음 (Stage 3-3 범위 밖)

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
