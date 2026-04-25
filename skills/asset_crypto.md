# Skills: Crypto Rules

암호화폐 자산군 전용 룰 정의. [base.md](base.md)에 정의된 공통 룰을 `override`, `extend`, `inherit`으로 오버레이하고, crypto에서만 의미를 가지는 신규 룰을 추가한다.

## 자산군 특성 요약

- 거래는 24시간 7일 연속 발생하며, 전통 금융 시장의 영업일 캘린더가 적용되지 않습니다.
- 거래소(Binance, Coinbase, Upbit 등) 사이의 가격이 같은 시점에도 다를 수 있고, 그 분산이 변동성 신호로 활용될 수 있습니다.
- 일반적인 일중 변동폭이 전통 자산보다 크기 때문에 RSI 임계값이나 변동성 배수 등을 조정합니다.
- 무기한 선물 시장이 활성화되어 있어 펀딩비(funding rate)와 같은 파생 지표를 함께 관찰할 수 있습니다.

## 문서 구조 규칙

각 룰 헤더에 사람이 읽는 태그를 부여하여 base 룰에 대한 오버레이 의미를 표시합니다. 사람이 읽는 태그는 YAML의 `merge_policy` 값과 1:1로 대응되며, 매핑은 다음과 같습니다.

| 헤더 태그 | YAML `merge_policy` | 의미 |
|----------|---------------------|------|
| `[override]` | `override` | base 룰의 정의를 통째로 자산군 룰로 교체 |
| `[extend]` | `extend` | base 룰을 보존한 채 인디케이터·조건·템플릿 변수를 합집합으로 확장 |
| `[inherit]` | `inherit` | base 룰을 변경 없이 그대로 상속 |
| `[crypto-only]` | `asset_only` | base에 대응 룰이 없고 해당 자산군 스코프에서만 평가되는 룰 |

`asset_only`는 base에 대응 룰이 없고 해당 자산군 스코프에서만 평가되는 룰을 의미합니다. 자산군에 따라 `[crypto-only]`, `[etf-only]`, `[stock-kr-only]` 등 자산군 이름을 붙인 태그로 표시합니다.

룰 본문은 [base.md](base.md)와 동일하게 4개 섹션을 가집니다.

1. 사람이 읽는 설명
2. YAML 룰 블록
3. 인사이트 템플릿
4. 추천 행동

`inherit` 태그가 붙은 룰은 base 룰을 그대로 상속하므로 YAML 블록은 최소 구조만 명시하고, 인사이트 템플릿과 추천 행동은 base의 것을 그대로 사용합니다.

---

## Rule 1. [override] momentum_overheating

### 1) 사람이 읽는 설명

base의 `momentum_overheating` 룰에서 RSI 과열 기준을 `rsi_14 > 70`에서 `rsi_14 > 80`으로 상향 조정합니다.

코인은 일중 변동성이 전통 자산보다 크기 때문에 RSI 70대는 일상적인 강세 구간일 가능성이 높습니다. 80을 초과하는 구간에서 비로소 단기 과열로 분류하는 것이 자산군 특성에 더 부합합니다.

`merge_policy: override`이므로 base 룰의 정의 전체가 본 룰로 교체됩니다. 즉, 오버라이드된 후에는 base의 `rsi_14 > 70` 조건은 더 이상 평가되지 않습니다.

### 2) YAML 룰 블록

```yaml
- rule_id: momentum_overheating
  rule_name: "단기 모멘텀 과열 (crypto)"
  scope: asset
  asset_types: ["crypto"]
  merge_policy: override
  required_indicators:
    - name: rsi_14
      type: rsi
      params: { window: 14, source: close }
    - name: ma_20
      type: sma
      params: { window: 20, source: close }
    - name: volume_ma_20
      type: sma
      params: { window: 20, source: volume }
    - name: volume_ratio
      type: ratio
      params: { numerator: volume, denominator: volume_ma_20 }
  conditions:
    all_of:
      - "rsi_14 > 80"
      - "close > ma_20"
      - "volume_ratio > 1.2"
  signal: momentum_overheated
  severity: warn
  visualization: viz_momentum_overheating
  template_variables:
    - rsi_14
    - close
    - ma_20
    - volume_ratio
```

### 3) 인사이트 템플릿

```yaml
- template_id: insight_momentum_overheating_crypto
  bind_to: momentum_overheating
  text: "RSI(14)가 {rsi_14:.1f}로 코인 기준 과열 구간(80 초과)에 진입했고, 종가 {close}가 MA20({ma_20:.2f}) 위에 있으며, 거래량은 20일 평균 대비 {volume_ratio:.2f}배입니다. 코인의 일중 변동성을 감안해도 단기 평균 회귀 가능성을 검토할 수 있습니다."
  variables: [rsi_14, close, ma_20, volume_ratio]
```

### 4) 추천 행동

- 신규 진입 비중을 줄이고 분할 진입으로 전환하는 방안을 검토할 수 있습니다.
- 무기한 선물 포지션이 있다면 청산가 거리를 함께 점검하시기 바랍니다.
- 동일 시점에 `funding_rate_abnormal` 신호가 발생했는지 함께 확인하면 과열 정도의 신뢰도를 보강할 수 있습니다.

---

## Rule 2. [extend] momentum_overheating

### 1) 사람이 읽는 설명

base의 `momentum_overheating` 룰에 거래소 간 가격 분산(`exchange_price_dispersion`) 조건을 추가합니다.

크립토는 거래소 간 가격이 동일 시점에도 분산되며, 그 분산이 일정 수준을 초과하면 단기 변동성이 확대될 가능성이 높아집니다. 본 룰은 `merge_policy: extend`로 base 룰을 보존한 채 조건과 인디케이터, 템플릿 변수를 추가합니다.

`extends: momentum_overheating` 키는 본 오버레이가 어느 base 룰에 결합되는지를 명시합니다. 동일 자산군에서 같은 `rule_id`에 대해 `override`와 `extend`가 동시에 선언된 경우, 병합 우선순위(`override > extend > inherit`)에 따라 override가 우선 적용되며 extend는 무시됩니다. 이 경우 본 룰의 추가 조건을 적용하려면 override 룰 본문에 직접 포함시키거나, override를 제거해야 합니다.

extend 병합 시 항목별 병합 의미론은 다음과 같습니다.

- `conditions`: 합집합으로 결합되며 모든 조건이 AND로 평가됩니다.
- `required_indicators`: 합집합으로 병합되며 동일 `name`은 중복 제거됩니다.
- `template_variables`: 합집합으로 병합되며 중복 제거됩니다.
- `signal`, `severity`, `visualization`: extend 룰은 base 룰과 동일한 값을 지정해야 합니다. 다른 값이 지정된 경우 룰 엔진은 검증 단계에서 에러를 발생시킵니다.
- 인사이트 템플릿: base 템플릿과 extend 템플릿이 순차적으로 모두 렌더링됩니다.

### 2) YAML 룰 블록

```yaml
- rule_id: momentum_overheating
  rule_name: "단기 모멘텀 과열 (거래소 분산 추가)"
  scope: asset
  asset_types: ["crypto"]
  merge_policy: extend
  extends: momentum_overheating
  required_indicators:
    - name: exchange_price_dispersion
      type: dispersion
      params: { source: exchange_prices, method: stddev_over_mean }
  conditions:
    all_of:
      - "exchange_price_dispersion > 0.015"
  signal: momentum_overheated
  severity: warn
  visualization: viz_momentum_overheating
  template_variables:
    - exchange_price_dispersion
```

병합 결과로 최종 적용되는 조건은 base의 `all_of` 항목과 본 룰의 `all_of` 항목이 합쳐진 형태입니다. `required_indicators`와 `template_variables`도 동일하게 합집합으로 병합됩니다.

### 3) 인사이트 템플릿

```yaml
- template_id: insight_momentum_overheating_dispersion
  bind_to: momentum_overheating
  text: "기존 과열 조건과 함께 거래소 간 가격 분산이 {exchange_price_dispersion:.4f}로 0.015를 초과했습니다. 단기 변동성 확대 가능성을 함께 관찰할 수 있습니다."
  variables: [exchange_price_dispersion]
```

본 템플릿은 base의 `insight_momentum_overheating` 템플릿과 함께 출력되도록 설계되었습니다. 즉, 두 문장이 순서대로 렌더링됩니다.

### 4) 추천 행동

- 거래소 간 가격 차이가 평소보다 클 때는 차익거래 시도가 발생할 가능성이 있으므로 단기 변동성에 대비한 포지션 크기 조정을 검토할 수 있습니다.
- 사용 중인 거래소 한 곳의 가격만 보고 의사결정하지 말고, 가능한 경우 복수 거래소의 가격을 함께 확인하시기 바랍니다.

---

## Rule 3. [inherit] volatility_expansion

### 1) 사람이 읽는 설명

base의 `volatility_expansion` 룰을 코인 자산군에서도 변경 없이 그대로 상속합니다.

볼린저 밴드 폭 확대는 자산군에 관계없이 변동성 증가의 일반적인 신호로 해석할 수 있으므로, 코인 전용 임계값 조정이나 추가 조건을 적용하지 않습니다.

### 2) YAML 룰 블록

```yaml
- rule_id: volatility_expansion
  merge_policy: inherit
  inherit_from: base
```

`inherit` 룰은 본 키 외의 정의를 가지지 않습니다. 룰 엔진은 `inherit_from`에 지정된 스코프(`base`)에서 동일 `rule_id`의 룰을 그대로 가져와 자산군에 적용합니다.

### 3) 인사이트 템플릿

base의 `insight_volatility_expansion` 템플릿을 그대로 사용합니다. 별도 템플릿 정의가 없습니다.

### 4) 추천 행동

base의 추천 행동을 그대로 따릅니다.

---

## Rule 4. [crypto-only] funding_rate_abnormal

### 1) 사람이 읽는 설명

무기한 선물 시장의 펀딩비 절댓값이 0.03(3%)을 초과하는 비정상 구간을 감지하는 코인 전용 룰입니다.

펀딩비 절댓값이 비정상적으로 커진 상태는 선물 시장의 한쪽 방향(롱 또는 숏)에 포지션이 과도하게 쏠려 있을 가능성을 시사하며, 단기 청산 캐스케이드(연쇄 청산) 위험이 증가하는 구간으로 해석할 수 있습니다.

본 룰은 base에 대응되는 룰이 없는 신규 룰로, 자산군 스코프에서만 평가됩니다.

### 2) YAML 룰 블록

```yaml
- rule_id: funding_rate_abnormal
  rule_name: "펀딩비 비정상 구간"
  scope: asset
  asset_types: ["crypto"]
  merge_policy: asset_only
  required_indicators:
    - name: funding_rate
      type: passthrough
      params: { source: funding_rate }
    - name: abs_funding_rate
      type: abs
      params: { source: funding_rate }
  conditions:
    all_of:
      - "abs_funding_rate > 0.03"
  signal: funding_rate_abnormal
  severity: warn
  visualization: funding_rate_line
  template_variables:
    - funding_rate
    - abs_funding_rate
```

### 3) 인사이트 템플릿

```yaml
- template_id: insight_funding_rate_abnormal
  bind_to: funding_rate_abnormal
  text: "펀딩비가 {funding_rate:+.4f}(절댓값 {abs_funding_rate:.4f})로 0.03을 초과했습니다. 선물 시장 한 방향 쏠림에 따른 단기 청산 위험 가능성을 검토할 수 있습니다."
  variables: [funding_rate, abs_funding_rate]
```

### 4) 추천 행동

- 무기한 선물 포지션이 있다면 레버리지를 낮추거나 일부 포지션 정리를 검토할 수 있습니다.
- 펀딩비 부호가 양(+)이면 롱 쏠림, 음(-)이면 숏 쏠림으로 해석할 수 있습니다.
- 펀딩비 비정상 구간이 `momentum_overheating` 또는 `volatility_expansion` 신호와 동시에 발생하는 경우, 청산 위험이 더 높아진 상태로 볼 수 있으므로 함께 확인하시기 바랍니다.

---

## 병합 결과 요약

| rule_id | base 적용 | crypto override | crypto extend | crypto only | 최종 결과 |
|---------|----------|-----------------|---------------|-------------|-----------|
| momentum_overheating | yes | yes (RSI>80) | yes (분산 조건) | — | override 우선 적용, extend는 무시됨 |
| momentum_oversold | yes | — | — | — | base 그대로 |
| trend_cross_signal | yes | — | — | — | base 그대로 |
| volatility_expansion | yes | — | — | — | base 그대로 (명시적 inherit 선언) |
| funding_rate_abnormal | — | — | — | yes | crypto에서만 평가 |

병합 우선순위: `override > extend > base inherit`. 같은 `rule_id`에 여러 오버레이가 있을 때 우선순위가 높은 정책 하나만 적용됩니다.
