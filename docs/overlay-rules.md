# Overlay Rules — RuleCraft Invest 룰 병합 헌법

## 1. 문서의 목적

이 문서는 RuleCraft Invest의 룰 병합 정책을 단일 출처(single source of truth)로 정의합니다. 룰 엔진을 구현하는 개발자, 새 자산군 Skills 파일을 추가하는 사용자, 시연 중 충돌 케이스를 설명해야 하는 발표자가 동일한 규칙을 참조할 수 있도록 작성되었습니다. 본 문서는 [CLAUDE.md](../CLAUDE.md)의 설계 원칙(특히 3절의 "룰 병합 우선순위"와 "룰 엔진 파이프라인")을 운영 수준으로 구체화하며, [skills/base.md](../skills/base.md), [skills/asset_crypto.md](../skills/asset_crypto.md), [skills/asset_stock_kr.md](../skills/asset_stock_kr.md)가 참조하는 공통 정책을 모아 둡니다.

---

## 2. 시스템 정책 요약 (machine-readable)

이 시스템의 자산군 감지 정책과 오버레이 적용 정책은 다음과 같이 정의됩니다. 룰 엔진은 시작 시 이 블록을 로딩하여 동작 모드를 결정합니다.

```yaml
asset_type_detection:
  mode: ai_recommend_user_confirm
  fallback: base_only
  description: "자산군은 AI가 데이터로부터 추천하고 사용자가 확인하는 방식으로 결정된다. 추천 실패 또는 사용자가 '기타/모름'을 선택한 경우 base 룰만 적용한다."

overlay_application:
  mode: single_primary_asset_type
  applied_rules:
    - base
    - selected_asset_overlay
  description: "한 데이터에는 단일 자산군 오버레이만 적용된다. base 룰과 선택된 자산군의 오버레이가 결합된다."

multi_asset_overlay:
  status: not_supported_in_mvp
  rationale: "복수 자산군 동시 적용은 룰 충돌 해결의 복잡도를 크게 증가시키므로 현 버전에서는 지원하지 않는다."
  future_extension: "향후 한국 상장 ETF, 해외 상장 한국 기업 등 복합 성격 자산을 위한 다중 태그 지원을 검토할 수 있다."
```

각 키의 의미는 다음과 같습니다.

- `asset_type_detection.mode: ai_recommend_user_confirm` — 룰 엔진이 데이터의 컬럼·값 분포·메타데이터를 AI에 전달하여 자산군 후보를 추천받고, 사용자가 확인 또는 수정하는 단계를 거친 뒤에야 자산군이 확정됩니다. 사용자 확인 없이 자동 적용되지 않습니다.
- `asset_type_detection.fallback: base_only` — AI 추천이 실패하거나 사용자가 "기타/모름"을 선택한 경우 어떤 자산군 오버레이도 적용하지 않고 [skills/base.md](../skills/base.md)의 룰만 평가합니다.
- `overlay_application.mode: single_primary_asset_type` — 입력 데이터 한 건에 대해 정확히 하나의 자산군 오버레이만 base 룰과 결합됩니다. 동시에 두 자산군 오버레이가 적용되지 않습니다.
- `overlay_application.applied_rules` — 최종 평가 대상 룰 집합은 `base` 룰과 확정된 자산군의 오버레이(`selected_asset_overlay`) 두 출처로 한정됩니다.
- `multi_asset_overlay.status: not_supported_in_mvp` — 본 MVP 범위에서 복수 자산군 동시 오버레이는 지원하지 않으며, 향후 확장 방향은 `future_extension` 항목에 명시합니다.

---

## 3. 룰의 4가지 병합 정책

각 정책은 `merge_policy` 값으로 식별되며, 자산군 Skills 파일의 헤더 태그로 사람이 읽는 형태로도 표시됩니다.

### 3.1 override

- **의미**: base 룰의 정의를 통째로 자산군 룰로 교체합니다. 교체된 후에는 base의 원본 정의가 평가되지 않습니다.
- **선언 파일**: 자산군 Skills 파일 (`skills/asset_*.md`)에서만 선언 가능합니다.
- **YAML 키 표현**: `merge_policy: override`. `rule_id`는 교체 대상 base 룰의 `rule_id`와 동일하게 지정합니다.
- **헤더 태그**: `[override]`
- **사용 예시**: [skills/asset_crypto.md](../skills/asset_crypto.md)의 `momentum_overheating` — base의 `rsi_14 > 70`을 `rsi_14 > 80`으로 상향 조정.

### 3.2 extend

- **의미**: base 룰을 보존한 채 `required_indicators`, `conditions`, `template_variables`를 합집합으로 확장합니다. base의 조건은 모두 그대로 평가되고 extend의 조건이 추가됩니다.
- **선언 파일**: 자산군 Skills 파일 (`skills/asset_*.md`)에서만 선언 가능합니다.
- **YAML 키 표현**: `merge_policy: extend`, `extends: <base_rule_id>`. `rule_id`는 base의 `rule_id`와 동일하게 지정합니다.
- **헤더 태그**: `[extend]`
- **사용 예시**: [skills/asset_stock_kr.md](../skills/asset_stock_kr.md)의 `momentum_overheating` — base 조건에 외국인 5일 평균 순매수 < 0 조건 추가.

### 3.3 inherit

- **의미**: base 룰을 변경 없이 그대로 상속합니다. 자산군에서 추가 조건이나 임계값 조정이 필요 없는 경우에 명시적으로 선언합니다.
- **선언 파일**: 자산군 Skills 파일 (`skills/asset_*.md`)에서만 선언 가능합니다.
- **YAML 키 표현**: `merge_policy: inherit`, `inherit_from: base`. `rule_id`는 상속 대상 base 룰의 `rule_id`와 동일하게 지정합니다.
- **헤더 태그**: `[inherit]`
- **사용 예시**: [skills/asset_crypto.md](../skills/asset_crypto.md)의 `volatility_expansion`, [skills/asset_stock_kr.md](../skills/asset_stock_kr.md)의 `trend_cross_signal`.

### 3.4 asset_only

- **의미**: base에 대응 룰이 없고 해당 자산군 스코프에서만 평가되는 신규 룰입니다.
- **선언 파일**: 자산군 Skills 파일 (`skills/asset_*.md`)에서만 선언 가능합니다.
- **YAML 키 표현**: `merge_policy: asset_only`. `rule_id`는 base와 충돌하지 않는 신규 식별자를 사용합니다.
- **헤더 태그**: `[{자산군}-only]` 형식 — 예: `[crypto-only]`, `[stock-kr-only]`, `[etf-only]`.
- **사용 예시**: [skills/asset_crypto.md](../skills/asset_crypto.md)의 `funding_rate_abnormal`, [skills/asset_stock_kr.md](../skills/asset_stock_kr.md)의 `price_limit_proximity` 및 `foreign_net_buying_surge`.

---

## 4. 병합 우선순위

동일 자산군 내에서 같은 `rule_id`에 대해 여러 오버레이 정책이 선언된 경우, 다음 우선순위로 단 하나의 정책만 적용됩니다.

```text
override > extend > inherit
```

우선순위가 낮은 정책은 무시되며, 룰 엔진은 무시된 정책에 대한 정보 수준 로그를 남깁니다.

### 케이스 A — override와 extend 동시 선언

[skills/asset_crypto.md](../skills/asset_crypto.md)의 `momentum_overheating`에 `[override]`(RSI 임계값 80으로 교체)와 `[extend]`(거래소 간 가격 분산 조건 추가)가 동시에 선언되어 있습니다.

- 적용 결과: `override`만 적용되어 RSI 임계값 80, MA20, 거래량 조건만 평가됩니다.
- 무시되는 항목: `extend`가 추가하려던 거래소 가격 분산 조건은 평가되지 않습니다.
- 추가 조건을 살리려면: 거래소 가격 분산 조건을 `override` 룰 본문의 `conditions.all_of`에 직접 포함시키거나, `override` 선언을 제거하고 base + extend 조합으로 동작시켜야 합니다.

### 케이스 B — extend만 선언

[skills/asset_stock_kr.md](../skills/asset_stock_kr.md)의 `momentum_overheating`은 `[extend]`로만 선언되어 있습니다.

- 적용 결과: base의 정의(RSI 70, MA20, 거래량 조건)가 모두 유지되고 extend의 외국인 매도 우위 조건이 합집합으로 결합되어 모두 AND로 평가됩니다.

### 케이스 C — inherit만 선언

[skills/asset_stock_kr.md](../skills/asset_stock_kr.md)의 `trend_cross_signal`은 `[inherit]`로만 선언되어 있습니다.

- 적용 결과: base의 `trend_cross_signal` 정의가 변경 없이 그대로 사용됩니다. inherit 룰은 자체 조건이나 인디케이터를 추가하지 않습니다.

---

## 5. extend 병합 의미론

`extend` 정책으로 선언된 룰을 base와 결합할 때 항목별 병합 규칙은 다음과 같습니다. 본 의미론은 [skills/asset_crypto.md](../skills/asset_crypto.md)의 Rule 2(`[extend] momentum_overheating`)에서 처음 정의되었으며, 본 문서가 통합 정리합니다.

| 항목 | 병합 방식 |
|------|-----------|
| `conditions` | 합집합 (base와 extend의 모든 조건이 AND로 결합) |
| `required_indicators` | 합집합 (동일 `name`은 중복 제거) |
| `template_variables` | 합집합 (중복 제거) |
| `signal` | base와 동일해야 함, 다르면 검증 에러 |
| `severity` | base와 동일해야 함, 다르면 검증 에러 |
| `visualization` | base와 동일해야 함, 다르면 검증 에러 |
| 인사이트 템플릿 | base 템플릿과 extend 템플릿이 모두 순차 렌더링 |

검증 에러가 발생한 경우 룰 엔진은 해당 룰 전체를 적용 대상에서 제외하고 사용자에게 에러를 보고합니다. 부분 적용은 허용하지 않습니다.

---

## 6. 같은 rule_id의 자산군 간 분리

동일한 `rule_id`가 여러 자산군 파일(`asset_crypto.md`, `asset_stock_kr.md`, `asset_etf_us.md` 등)에서 다르게 정의될 수 있습니다. 룰 엔진은 `detect_asset_type` 단계에서 결정된 단일 자산군에 해당하는 오버레이만 base와 병합합니다. 다른 자산군의 오버레이는 평가하지 않습니다.

구체 예시: `momentum_overheating`이 [skills/asset_crypto.md](../skills/asset_crypto.md)에서는 `[override]`(RSI 80), [skills/asset_stock_kr.md](../skills/asset_stock_kr.md)에서는 `[extend]`(외국인 매도 우위 조건 추가)로 선언되어 있습니다.

- 입력 데이터가 한국 주식으로 분류된 경우: `stock_kr`의 `[extend]`만 base에 결합됩니다. `crypto`의 `[override]`는 평가 대상에서 완전히 제외됩니다.
- 입력 데이터가 코인으로 분류된 경우: `crypto`의 `[override]`만 적용됩니다. `stock_kr`의 `[extend]`는 평가 대상에서 완전히 제외됩니다.

이 분리 원칙은 2절의 `overlay_application.mode: single_primary_asset_type` 정책에서 파생됩니다.

---

## 7. template_variables 디자인 정책

YAML의 `template_variables` 리스트는 룰 엔진이 인사이트 템플릿에 바인딩 가능한 변수의 전체 집합을 의미합니다. 인사이트 템플릿의 `text` 안에 placeholder로 등장하는 변수는 이 집합의 부분집합입니다. `template_variables`에 선언되었으나 `text`에서 사용되지 않은 변수가 존재할 수 있으며, 이는 인사이트 템플릿을 사용자가 커스터마이즈하거나 추가 템플릿을 등록할 때 사용할 수 있도록 미리 바인딩되는 변수임을 의미하는 의도적 디자인입니다.

본 디자인은 [skills/base.md](../skills/base.md)를 포함한 모든 Skills 파일에 동일하게 적용됩니다. 예를 들어 base의 `trend_cross_signal` 룰은 `template_variables`에 `close`를 선언하고 있으나 기본 인사이트 템플릿의 `text`에서는 사용하지 않습니다. 사용자가 추가 템플릿을 작성할 때 `close`를 placeholder로 활용할 수 있습니다.

---

## 8. inherit 룰의 최소 YAML 구조

`merge_policy: inherit`로 선언된 룰은 다음 3개 키만 가집니다.

```yaml
- rule_id: <base의 rule_id>
  merge_policy: inherit
  inherit_from: base
```

다른 키(`scope`, `asset_types`, `conditions`, `signal`, `severity`, `visualization`, `template_variables`, `required_indicators`, `rule_name`)는 명시하지 않습니다. 룰 엔진은 `inherit_from`에 지정된 스코프(현 시점에서는 `base`만 허용)에서 동일한 `rule_id`의 룰을 그대로 가져와 해당 자산군에 적용합니다.

3개 키 외의 항목이 함께 선언된 경우, 룰 엔진은 해당 inherit 룰을 검증 단계에서 무효 처리하고 사용자에게 에러를 보고합니다.

---

## 9. 룰 엔진 처리 흐름

본 흐름은 [CLAUDE.md](../CLAUDE.md) 5절의 결정론적 파이프라인을 운영 수준으로 분해한 것입니다. 각 단계는 입력과 출력이 명확한 순수 함수로 구현됩니다.

1. **`load_skills`** — `skills/base.md`와 모든 `skills/asset_*.md`를 로드하고 마크다운 본문에서 YAML 룰 블록을 분리합니다.
2. **`detect_asset_type`** — 입력 데이터의 컬럼·값 분포·메타데이터를 AI에 전달하여 자산군을 추천하고, 사용자가 확인 또는 수정합니다. `asset_type_detection.mode: ai_recommend_user_confirm` 정책에 따라 사용자 확인 없이 자동 확정되지 않습니다.
3. **`select_asset_overlay`** — 확정된 자산군에 해당하는 단일 `asset_*.md`만 오버레이 후보로 선택합니다. 다른 자산군 오버레이는 평가 대상에서 제외됩니다.
4. **`merge_rules`** — base 룰과 선택된 자산군 오버레이를 정책별 우선순위(`override > extend > inherit`)에 따라 병합합니다. `asset_only` 룰은 base와 무관하게 그대로 추가됩니다.
5. **`validate_merged_rules`** — extend 룰의 `signal`/`severity`/`visualization`이 base와 일치하는지, inherit 룰이 3개 키 제약을 지키는지 등 본 문서의 정책을 검증합니다. 위반 시 해당 룰을 적용 대상에서 제외하고 사용자에게 보고합니다.
6. **`calculate_indicators`** — 병합된 룰의 `required_indicators`를 모두 계산합니다. 동일 `name`의 인디케이터는 한 번만 계산됩니다.
7. **`evaluate_conditions`** — 각 룰의 `conditions`(`all_of` 또는 `any_of`)를 평가하여 매칭된 룰 집합을 결정합니다.
8. **`render_insight_template`** — 매칭된 룰의 `template_variables`를 데이터 값으로 바인딩하여 인사이트 텍스트를 생성합니다. extend 룰이 매칭된 경우 base 템플릿과 extend 템플릿이 순차로 렌더링됩니다.
9. **`choose_visualization`** — 매칭된 룰의 `visualization` 키에 따라 차트 타입과 시리즈를 선택합니다.

LLM 호출은 `render_insight_template` 단계의 출력 문장을 자연스럽게 다듬는 보조 단계에서만 발생합니다. 다른 단계에는 LLM이 개입하지 않습니다.
