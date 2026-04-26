"""인사이트 템플릿 텍스트 치환.

Stage 1 한정: LLM 호출 없이 Python str.format으로 단순 치환만 수행한다.
템플릿 변수의 포맷 스펙({var:.2f} 등)은 str.format이 그대로 처리한다.
"""

from __future__ import annotations

from typing import Any


def render_insight(template_text: str, values: dict[str, Any]) -> str:
    """템플릿의 {var} 또는 {var:format}을 values dict 값으로 치환."""
    return template_text.format(**values)


def find_template(
    templates: list[dict],
    rule_id: str,
    available_keys: set[str] | None = None,
) -> dict | None:
    """rule_id에 bind_to된 템플릿을 찾는다.

    같은 rule_id에 여러 템플릿이 바인딩된 경우(base + asset 양쪽 정의, 또는
    override + extend 템플릿이 공존), 다음 두 단계로 선택한다.

    1. 역순 탐색으로 뒤에 로드된 자산군 전용 템플릿을 우선한다.
    2. `available_keys`가 주어지면, 템플릿의 `variables` 전부가 해당 집합의
       부분집합인 경우만 선택한다. Stage 1에서 extend 템플릿(예: dispersion)을
       자연스럽게 건너뛰기 위함이다.
    """
    for tpl in reversed(templates):
        if tpl.get("bind_to") != rule_id:
            continue
        if available_keys is None:
            return tpl
        tpl_vars = tpl.get("variables") or []
        if all(v in available_keys for v in tpl_vars):
            return tpl
    return None
