"""Skills 파일 로드와 YAML 룰 블록 파싱.

Stage 2-2: skills/ 디렉터리 안의 모든 *.md 파일을 자동 로드한다.
- base.md는 항상 가장 먼저 로드되어 병합 우선순위(base → asset overlay)를 보장.
- 그 외 파일은 파일명 알파벳 순서로 일관되게 로드 (asset_crypto.md, asset_etf_us.md,
  asset_stock_kr.md ...).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


_YAML_BLOCK_PATTERN = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)

_BASE_FILENAME = "base.md"


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


def _ordered_skill_files(skills_dir: Path) -> list[Path]:
    """skills 디렉터리의 *.md 파일을 base.md 우선 + 알파벳 순서로 정렬해 반환."""
    md_files = sorted(p for p in skills_dir.glob("*.md") if p.is_file())
    base = [p for p in md_files if p.name == _BASE_FILENAME]
    rest = [p for p in md_files if p.name != _BASE_FILENAME]
    return base + rest


def load_skills(skills_dir: str | Path) -> dict[str, list[dict]]:
    """Skills 디렉터리의 모든 *.md 파일을 로드.

    Returns:
        {
            "rules":     룰 dict 목록 (각각 rule_id 보유),
            "templates": 인사이트 템플릿 dict 목록 (각각 template_id 보유),
        }
    """
    skills_path = Path(skills_dir)

    rules: list[dict] = []
    templates: list[dict] = []

    if not skills_path.is_dir():
        return {"rules": rules, "templates": templates}

    for path in _ordered_skill_files(skills_path):
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
