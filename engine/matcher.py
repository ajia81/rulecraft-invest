"""룰 병합과 조건 평가.

Stage 2-1B 동작:
- merge_rules: 4가지 병합 정책(override / extend / inherit / asset_only)을 모두 처리.
  우선순위: override > extend > inherit (docs/overlay-rules.md 섹션 4).
- evaluate_conditions: all_of(AND) + any_of(OR) 결합 평가.
- evaluate_expression: ast 모듈 기반 안전 평가 (eval 미사용). NaN/None 좌·우변은
  표현식을 즉시 False로 처리한다.
"""

from __future__ import annotations

import ast
import operator
from typing import Any

import pandas as pd


_COMPARE_OPS = {
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
}

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _is_nan_like(value: Any) -> bool:
    """NaN / None 통합 체크. 문자열은 항상 non-NaN으로 간주."""
    if isinstance(value, str):
        return False
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    if isinstance(result, bool):
        return result
    try:
        return bool(result)
    except (TypeError, ValueError):
        return False


def _eval_node(node: ast.AST, values: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in values:
            raise KeyError(node.id)
        return values[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand, values)
    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"unsupported binary op: {type(node.op).__name__}")
        return op(_eval_node(node.left, values), _eval_node(node.right, values))
    raise ValueError(f"unsupported AST node: {type(node).__name__}")


def _evaluate_expression_bool(expr: str, values: dict[str, Any]) -> bool:
    """단일 비교식을 평가하여 bool 반환. trace 모드 없음."""
    tree = ast.parse(expr.strip(), mode="eval")
    body = tree.body
    if not isinstance(body, ast.Compare):
        raise ValueError(f"not a comparison expression: {expr!r}")

    left = _eval_node(body.left, values)
    if _is_nan_like(left):
        return False

    for op_node, comparator in zip(body.ops, body.comparators):
        op = _COMPARE_OPS.get(type(op_node))
        if op is None:
            raise ValueError(f"unsupported comparison op: {type(op_node).__name__}")
        right = _eval_node(comparator, values)
        if _is_nan_like(right):
            return False
        try:
            if not op(left, right):
                return False
        except TypeError:
            return False
        left = right
    return True


def evaluate_expression(
    expr: str, values: dict[str, Any], trace: bool = False
):
    """단일 비교식을 평가.

    예: "rsi_14 > 80", "close > ma_20", "limit_side == 'upper'", "abs_funding_rate > 0.03"

    NaN 처리 (Stage 2-1B):
    - 좌변 또는 우변이 NaN/None이면 즉시 False 반환.
    - 비교 자체가 TypeError(예: 문자열 vs 숫자)면 False 반환.

    trace 모드 (Stage 3-2):
    - trace=False (기본): bool 반환. 하위 호환.
    - trace=True: dict 반환. 다음 키:
        expression (str), passed (bool), bindings (dict[str, Any]),
        skip_reason (str | absent — KeyError 발생 시만)
    """
    if not trace:
        return _evaluate_expression_bool(expr, values)

    tree = ast.parse(expr.strip(), mode="eval")
    bindings: dict[str, Any] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in values:
            bindings[node.id] = values[node.id]

    try:
        passed = _evaluate_expression_bool(expr, values)
        return {
            "expression": expr,
            "passed": passed,
            "bindings": bindings,
        }
    except KeyError as e:
        return {
            "expression": expr,
            "passed": False,
            "bindings": bindings,
            "skip_reason": f"missing variable: {e}",
        }


def evaluate_conditions(
    rule: dict, values: dict[str, Any], trace: bool = False
):
    """rule['conditions']의 all_of(AND)와 any_of(OR)를 함께 평가.

    - all_of만 있으면: 모든 표현식이 True여야 True.
    - any_of만 있으면: 하나 이상의 표현식이 True면 True.
    - 둘 다 있으면: all_of AND any_of (둘 다 통과해야 True).
    - 둘 다 없으면: True (조건 없는 룰은 항상 매칭).

    trace 모드 (Stage 3-2):
    - trace=False (기본): bool 반환.
    - trace=True: dict 반환. 키:
        passed (bool),
        all_of_traces (list[expression trace dict]),
        any_of_traces (list[expression trace dict]),
        all_of_passed (bool),
        any_of_passed (bool | None — any_of가 없으면 None),
    """
    conditions = rule.get("conditions") or {}
    all_of = conditions.get("all_of") or []
    any_of = conditions.get("any_of") or []

    if not trace:
        if not all_of and not any_of:
            return True
        if all_of:
            for expr in all_of:
                if not evaluate_expression(expr, values):
                    return False
        if any_of:
            if not any(evaluate_expression(expr, values) for expr in any_of):
                return False
        return True

    # trace 모드
    all_of_traces = [evaluate_expression(e, values, trace=True) for e in all_of]
    any_of_traces = [evaluate_expression(e, values, trace=True) for e in any_of]

    all_of_passed = all(t["passed"] for t in all_of_traces) if all_of_traces else True
    any_of_passed: bool | None
    if any_of_traces:
        any_of_passed = any(t["passed"] for t in any_of_traces)
    else:
        any_of_passed = None

    if any_of_passed is None:
        passed = all_of_passed
    else:
        passed = all_of_passed and any_of_passed

    if not all_of and not any_of:
        passed = True  # 조건 없는 룰은 항상 매칭

    return {
        "passed": passed,
        "all_of_traces": all_of_traces,
        "any_of_traces": any_of_traces,
        "all_of_passed": all_of_passed,
        "any_of_passed": any_of_passed,
    }


def _merge_extend(base_rule: dict, extend_rules: list[dict]) -> dict:
    """base 룰을 하나 이상의 extend 룰과 합쳐 새 룰 dict를 만든다.

    docs/overlay-rules.md 섹션 5의 항목별 병합 의미론을 따른다.

    - conditions.all_of: 단순 concat (중복 제거 없음)
    - conditions.any_of: 단순 concat
    - required_indicators: name 기준 중복 제거, base 우선
    - template_variables: 합집합 (중복 제거, base 순서 우선)
    - signal / severity / visualization: base 값 유지
    """
    out = dict(base_rule)

    base_conditions = out.get("conditions") or {}
    merged_all = list(base_conditions.get("all_of") or [])
    merged_any = list(base_conditions.get("any_of") or [])

    base_inds = list(out.get("required_indicators") or [])
    merged_inds = list(base_inds)
    seen_ind_names = {
        ind.get("name") for ind in base_inds if isinstance(ind, dict) and ind.get("name")
    }

    base_tvars = list(out.get("template_variables") or [])
    merged_tvars = list(base_tvars)
    seen_tvars = set(base_tvars)

    for ext in extend_rules:
        ext_conditions = ext.get("conditions") or {}
        merged_all.extend(ext_conditions.get("all_of") or [])
        merged_any.extend(ext_conditions.get("any_of") or [])

        for ind in ext.get("required_indicators") or []:
            if not isinstance(ind, dict):
                continue
            name = ind.get("name")
            if name and name not in seen_ind_names:
                merged_inds.append(ind)
                seen_ind_names.add(name)

        for v in ext.get("template_variables") or []:
            if v not in seen_tvars:
                merged_tvars.append(v)
                seen_tvars.add(v)

    new_conditions: dict[str, list] = {}
    if merged_all:
        new_conditions["all_of"] = merged_all
    if merged_any:
        new_conditions["any_of"] = merged_any

    out["conditions"] = new_conditions
    out["required_indicators"] = merged_inds
    out["template_variables"] = merged_tvars
    return out


def merge_rules(rules: list[dict], asset_type: str) -> list[dict]:
    """4가지 병합 정책을 모두 처리하여 최종 평가 대상 룰 리스트를 반환.

    동작 (Stage 2-1B, docs/overlay-rules.md 섹션 3·4 준수):

    - "base"        → base 룰 풀에 등록
    - "override"    → 같은 rule_id의 base 룰을 통째로 교체
                       (asset_types에 현재 asset_type 포함된 경우만)
    - "extend"      → base 룰의 conditions/required_indicators/template_variables를
                       합집합으로 확장 (asset_types 체크)
    - "inherit"     → 별도 동작 없음. base 룰이 이미 평가 대상에 있으므로
                       inherit 선언은 의도 표명에 그친다 (중복 평가 방지).
    - "asset_only"  → base 대응 없는 신규 룰. 그대로 평가 대상에 추가.

    우선순위: 같은 rule_id에 override와 extend가 동시 선언되면 override만 적용,
    extend는 무시된다.
    """
    base_by_id: dict[str, dict] = {}
    overrides_by_id: dict[str, dict] = {}
    extends_by_id: dict[str, list[dict]] = {}
    asset_only_rules: list[dict] = []

    for rule in rules:
        rule_id = rule.get("rule_id")
        if not rule_id:
            continue
        policy = rule.get("merge_policy")

        if policy == "base":
            base_by_id[rule_id] = rule
            continue

        if policy == "inherit":
            # inherit는 base 룰을 그대로 사용한다는 선언. base 룰이 이미
            # base_by_id에 있으므로 별도 처리 없이 통과.
            continue

        # 이하 정책은 asset_types 체크 필요
        asset_types = rule.get("asset_types") or []
        if asset_type not in asset_types:
            continue

        if policy == "override":
            overrides_by_id[rule_id] = rule
        elif policy == "extend":
            extends_by_id.setdefault(rule_id, []).append(rule)
        elif policy == "asset_only":
            asset_only_rules.append(rule)
        # 기타 알 수 없는 정책은 무시

    merged: list[dict] = []
    for rule_id, base_rule in base_by_id.items():
        if rule_id in overrides_by_id:
            # 우선순위: override가 extend를 무시
            merged.append(overrides_by_id[rule_id])
        elif rule_id in extends_by_id:
            merged.append(_merge_extend(base_rule, extends_by_id[rule_id]))
        else:
            merged.append(base_rule)

    merged.extend(asset_only_rules)
    return merged
