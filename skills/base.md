# Skills: Base Rules

모든 자산군(한국 주식, 미국 ETF, 코인)에 공통 적용되는 기본 투자 분석 룰 정의.

이 문서의 룰은 `merge_policy: base`로 설정되며, 자산군별 룰(`asset_stock_kr.md`, `asset_etf_us.md`, `asset_crypto.md`)에서 `extend` 또는 `override`로 재정의될 수 있습니다.

## 문서 구조 규칙

각 룰은 아래 4개 섹션을 순서대로 가집니다.

1. **사람이 읽는 설명** — 룰의 의도와 동작 요약
2. **YAML 룰 블록** — 룰 엔진이 파싱하는 표준 구조
3. **인사이트 템플릿** — 조건 충족 시 출력할 문장 템플릿
4. **추천 행동** — 신호 발생 시 사용자가 검토할 수 있는 후속 행동

YAML 블록의 변수명과 인사이트 템플릿의 변수명은 정확히 일치해야 합니다. 룰 엔진은 `template_variables` 키에 선언된 이름만 바인딩합니다.

---

## Rule 1. momentum_overheating

### 1) 사람이 읽는 설명

단기 모멘텀이 과열 구간에 진입했을 가능성을 감지하는 룰입니다.

다음 세 조건이 동시에 충족될 때 신호를 발생시킵니다.

- RSI(14)가 70을 초과
- 종가가 20일 이동평균(MA20) 위에 위치
- 최근 거래량이 20일 평균 거래량 대비 20% 이상 증가

세 조건이 함께 충족되면 단기적으로 가격이 평균 회귀할 가능성이 높아진 상태로 해석할 수 있습니다. 이 룰은 매도 신호가 아니라 과열 가능성에 대한 주의 환기에 가깝습니다.

### 2) YAML 룰 블록

```yaml
- rule_id: momentum_overheating
  rule_name: "단기 모멘텀 과열"
  scope: base
  asset_types: ["stock_kr", "etf_us", "crypto"]
  merge_policy: base
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
      - "rsi_14 > 70"
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
- template_id: insight_momentum_overheating
  bind_to: momentum_overheating
  text: "RSI(14)가 {rsi_14:.1f}로 과열 구간에 있고, 종가 {close}가 MA20({ma_20:.2f}) 위에 있으며, 거래량은 20일 평균 대비 {volume_ratio:.2f}배입니다. 단기 평균 회귀 가능성을 검토할 수 있습니다."
  variables: [rsi_14, close, ma_20, volume_ratio]
```

### 4) 추천 행동

- 신규 진입 비중을 줄이고 분할 진입으로 전환하는 방안을 검토할 수 있습니다.
- 보유 종목의 경우 일부 수익 실현 또는 손절 라인 재설정을 고려할 수 있습니다.
- 자산군별 룰에서 RSI 임계값이 재정의될 수 있으므로 병합된 최종 룰을 함께 확인하시기 바랍니다.

---

## Rule 2. momentum_oversold

### 1) 사람이 읽는 설명

단기 모멘텀이 침체 구간에 진입한 상태를 감지하는 룰입니다.

다음 두 조건이 동시에 충족될 때 신호를 발생시킵니다.

- RSI(14)가 30 미만
- 종가가 20일 이동평균(MA20) 아래에 위치

두 조건이 충족되는 구간은 단기 반등 후보 구간으로 분류됩니다. 다만 추세 자체가 하락 전환된 경우 추가 하락이 이어질 가능성도 있으므로, 본 룰은 반등 가능성에 대한 관찰 신호로만 활용합니다.

### 2) YAML 룰 블록

```yaml
- rule_id: momentum_oversold
  rule_name: "단기 모멘텀 침체"
  scope: base
  asset_types: ["stock_kr", "etf_us", "crypto"]
  merge_policy: base
  required_indicators:
    - name: rsi_14
      type: rsi
      params: { window: 14, source: close }
    - name: ma_20
      type: sma
      params: { window: 20, source: close }
  conditions:
    all_of:
      - "rsi_14 < 30"
      - "close < ma_20"
  signal: momentum_oversold
  severity: info
  visualization: viz_momentum_oversold
  template_variables:
    - rsi_14
    - close
    - ma_20
```

### 3) 인사이트 템플릿

```yaml
- template_id: insight_momentum_oversold
  bind_to: momentum_oversold
  text: "RSI(14)가 {rsi_14:.1f}로 침체 구간에 있고, 종가 {close}가 MA20({ma_20:.2f}) 아래에 있습니다. 단기 반등 후보 구간으로 관찰할 수 있습니다."
  variables: [rsi_14, close, ma_20]
```

### 4) 추천 행동

- 분할 매수 관점에서 진입 시점 후보로 검토할 수 있습니다.
- 추세가 명확한 하락장인지 여부를 `trend_cross_signal` 룰의 결과와 함께 확인하시기 바랍니다.
- 거래량 동반 여부를 별도로 확인하면 신호의 신뢰도를 보강할 수 있습니다.

---

## Rule 3. trend_cross_signal

### 1) 사람이 읽는 설명

20일 이동평균(MA20)과 60일 이동평균(MA60)의 교차를 감지하여 추세 전환 신호를 발생시키는 룰입니다.

- MA20이 MA60을 상향 돌파(`+1`): 골든크로스
- MA20이 MA60을 하향 돌파(`-1`): 데드크로스
- 교차 없음(`0`): 신호 없음

본 룰은 추세 전환 가능성에 대한 관찰 신호이며, 단독으로 매매 판단의 근거로 사용하지 않습니다.

### 2) YAML 룰 블록

```yaml
- rule_id: trend_cross_signal
  rule_name: "이동평균 교차 신호"
  scope: base
  asset_types: ["stock_kr", "etf_us", "crypto"]
  merge_policy: base
  required_indicators:
    - name: ma_20
      type: sma
      params: { window: 20, source: close }
    - name: ma_60
      type: sma
      params: { window: 60, source: close }
    - name: cross_20_60
      type: cross
      params: { fast: ma_20, slow: ma_60 }
  conditions:
    any_of:
      - "cross_20_60 == 1"
      - "cross_20_60 == -1"
  signal: trend_cross_detected
  severity: info
  visualization: viz_trend_cross_signal
  template_variables:
    - cross_type
    - ma_20
    - ma_60
    - close
```

`cross_type`은 룰 엔진이 `cross_20_60` 값에서 파생합니다. `+1`이면 `"golden_cross"`, `-1`이면 `"dead_cross"`로 바인딩됩니다.

### 3) 인사이트 템플릿

```yaml
- template_id: insight_trend_cross_signal
  bind_to: trend_cross_signal
  text: "MA20({ma_20:.2f})과 MA60({ma_60:.2f})에서 {cross_type} 신호가 감지되었습니다. 추세 전환 가능성을 검토할 수 있습니다."
  variables: [cross_type, ma_20, ma_60, close]
```

### 4) 추천 행동

- 골든크로스 발생 시 추세 추종 전략의 진입 후보로 검토할 수 있습니다.
- 데드크로스 발생 시 보유 비중 축소 또는 손절 기준 재점검을 검토할 수 있습니다.
- 거래량 증가가 동반되지 않은 교차는 단기 노이즈일 가능성이 있으므로 `momentum_overheating` 또는 `volatility_expansion` 룰의 결과와 교차 검증하시기 바랍니다.

---

## Rule 4. volatility_expansion

### 1) 사람이 읽는 설명

볼린저 밴드(20일, 표준편차 2배) 폭이 최근 평균 대비 확대된 구간을 감지하는 룰입니다.

다음 조건이 충족될 때 신호를 발생시킵니다.

- 현재 볼린저 밴드 폭(`bb_width`)이 20일 평균 밴드 폭의 1.3배를 초과

변동성 확대는 추세 전환 또는 가속 구간에서 자주 관측됩니다. 방향성 정보는 포함하지 않으며, 변동성 자체가 평소 대비 커진 상태를 알리는 신호입니다.

### 2) YAML 룰 블록

```yaml
- rule_id: volatility_expansion
  rule_name: "변동성 확대"
  scope: base
  asset_types: ["stock_kr", "etf_us", "crypto"]
  merge_policy: base
  required_indicators:
    - name: bb_upper
      type: bollinger_upper
      params: { window: 20, num_std: 2, source: close }
    - name: bb_lower
      type: bollinger_lower
      params: { window: 20, num_std: 2, source: close }
    - name: bb_width
      type: bollinger_width
      params: { window: 20, num_std: 2, source: close }
    - name: bb_width_ma_20
      type: sma
      params: { window: 20, source: bb_width }
    - name: bb_width_ratio
      type: ratio
      params: { numerator: bb_width, denominator: bb_width_ma_20 }
  conditions:
    all_of:
      - "bb_width_ratio > 1.3"
  signal: volatility_expanded
  severity: warn
  visualization: viz_volatility_expansion
  template_variables:
    - bb_width
    - bb_width_ma_20
    - bb_width_ratio
    - close
```

### 3) 인사이트 템플릿

```yaml
- template_id: insight_volatility_expansion
  bind_to: volatility_expansion
  text: "볼린저 밴드 폭이 {bb_width:.2f}로 20일 평균({bb_width_ma_20:.2f}) 대비 {bb_width_ratio:.2f}배 확대되었습니다. 변동성이 평소보다 커진 구간으로 해석할 수 있습니다."
  variables: [bb_width, bb_width_ma_20, bb_width_ratio, close]
```

### 4) 추천 행동

- 포지션 크기를 평소보다 보수적으로 조정하는 방안을 검토할 수 있습니다.
- 손절 폭(stop loss)을 변동성에 맞춰 재계산하시기 바랍니다.
- 추세 방향은 본 룰만으로 판단할 수 없으므로 `trend_cross_signal` 또는 `momentum_overheating` 룰의 결과와 함께 해석하시기 바랍니다.

---

## 병합 규칙 요약

- 본 문서의 모든 룰은 `merge_policy: base`입니다.
- 자산군별 문서에서 동일한 `rule_id`를 가진 룰이 `extend`로 선언되면 `required_indicators`, `conditions`, `template_variables` 등 일부 키가 추가/덮어쓰기 됩니다.
- 동일한 `rule_id`가 `override`로 선언되면 base 룰 전체가 자산군 룰로 교체됩니다.
- 병합 우선순위: `override > extend > base inherit`.
