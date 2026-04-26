"""Skills 파일 로드와 YAML 룰 블록 파싱.

Stage 1 한정: skills/base.md와 skills/asset_crypto.md만 로드한다.
asset_stock_kr.md, asset_etf_us.md는 다음 단계에서 처리한다.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


_YAML_BLOCK_PATTERN = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)

_STAGE1_SKILLS = ["base.md", "asset_crypto.md"]


def parse_yaml_blocks(markdown_text: str) -> list[Any]:
    """마크다운 텍스트에서 ```yaml 코드 블록만 추출하여 파싱한다.

    각 블록은 yaml.safe_load로 파싱되어 dict 또는 list로 반환된다.
    파싱 실패 또는 빈 블록은 건너뛴다.
    """
    parsed: list[Any] = []
    for match in _YAML_BLOCK_PATTERN.finditer(markdown_text):
        block_text = match.group(1)
        try:
            data = yaml.safe_load(block_text)
        except yaml.YAMLError:
            continue
        if data is None:
            continue
        parsed.append(data)
    return parsed


def load_skills(skills_dir: str | Path) -> dict[str, list[dict]]:
    """Skills 디렉터리에서 Stage 1 대상 파일을 로드.

    Returns:
        {
            "rules":     룰 dict 목록 (각각 rule_id 보유),
            "templates": 인사이트 템플릿 dict 목록 (각각 template_id 보유),
        }
    """
    skills_path = Path(skills_dir)

    rules: list[dict] = []
    templates: list[dict] = []

    for filename in _STAGE1_SKILLS:
        path = skills_path / filename
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for block in parse_yaml_blocks(text):
            items = block if isinstance(block, list) else [block]
            for item in items:
                if not isinstance(item, dict):
                    continue
                if "rule_id" in item:
                    rules.append(item)
                elif "template_id" in item:
                    templates.append(item)

    return {"rules": rules, "templates": templates}
