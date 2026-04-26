# Skills: US ETF Rules

미국 ETF 자산군 전용 룰 정의. [base.md](base.md)에 정의된 공통 룰을 `override`, `extend`, `inherit`으로 오버레이하고, 미국 ETF에서만 의미를 가지는 신규 룰을 추가한다.

## 자산군 특성 요약

- 미국 ETF는 거래소에서 거래되는 가격(close)과 순자산가치(NAV)가 분리되어 있습니다.
- 둘의 차이는 NAV 괴리율(premium/discount)이라 부르며, 정상 ETF는 ±0.5% 이내로 유지됩니다.
- 정규 거래 시간은 09:30 ~ 16:00 ET (한국 시간 23:30 ~ 06:00).
- 거래량 급감은 유동성 위험 신호로 해석될 수 있습니다.
- 추적 오차(tracking error)가 ETF 품질의 핵심 지표 중 하나로, ETF 수익률과 추종 지수 수익률의 괴리를 측정합니다.

ETF 데이터는 실존 ETF가 아니라 DemoETF (S&P 500-like) 더미 데이터이며, NAV 괴리율 시연을 위한 구조화된 샘플입니다.

## 문서 구조 규칙

각 룰 헤더에 사람이 읽는 태그를 부여하여 base 룰에 대한 오버레이 의미를 표시합니다. 사람이 읽는 태그는 YAML의 `merge_policy` 값과 1:1로 대응되며, 매핑은 다음과 같습니다.

| 헤더 태그 | YAML `merge_policy` | 의미 |
|----------|---------------------|------|
| `[override]` | `override` | base 룰의 정의를 통째로 자산군 룰로 교체 |
| `[extend]` | `extend` | base 룰을 보존한 채 인디케이터·조건·템플릿 변수를 합집합으로 확장 |
| `[inherit]` | `inherit` | base 룰을 변경 없이 그대로 상속 |
| `[etf-us-only]` | `asset_only` | base에 대응 룰이 없고 해당 자산군 스코프에서만 평가되는 룰 |

YAML의 `template_variables` 리스트는 룰 엔진이 인사이트 템플릿에 바인딩 가능한 변수의 전체 집합을 의미합니다. 인사이트 템플릿의 `text` 안에 placeholder로 등장하는 변수는 이 집합의 부분집합입니다. 즉, `template_variables`에 선언되었으나 `text`에서 사용되지 않은 변수가 존재할 수 있으며, 이는 인사이트 템플릿을 사용자가 커스터마이즈하거나 추가 템플릿을 등록할 때 사용할 수 있도록 미리 바인딩되는 변수임을 의미합니다. 이 디자인은 [base.md](base.md)를 포함한 모든 Skills 파일에 동일하게 적용됩니다.

`asset_only`는 base에 대응 룰이 없고 해당 자산군 스코프에서만 평가되는 룰을 의미합니다. 자산군에 따라 `[crypto-only]`, `[etf-only]`, `[stock-kr-only]` 등 자산군 이름을 붙인 태그로 표시합니다.

룰 본문은 [base.md](base.md)와 동일하게 4개 섹션을 가집니다.

1. 사람이 읽는 설명
2. YAML 룰 블록
3. 인사이트 템플릿
4. 추천 행동

`inherit` 태그가 붙은 룰은 base 룰을 그대로 상속하므로 YAML 블록은 최소 구조만 명시하고, 인사이트 템플릿과 추천 행동은 base의 것을 그대로 사용합니다.

---

## Rule 1. [extend] momentum_overheating

### 1) 사람이 읽는 설명

base의 `momentum_overheating` 룰에 추적 오차 z-score 조건을 추가합니다.

ETF의 단기 과열이 발생할 때 추적 오차도 함께 비정상적으로 커진다면, 단순한 가격 모멘텀을 넘어 ETF의 추종 메커니즘 자체가 일시적으로 흔들리고 있을 가능성을 시사합니다. 본 룰은 이 결합 신호를 관찰하기 위한 것입니다.

`override`가 아닌 `extend`를 선택한 이유는 base의 RSI(14) / MA20 / 거래량 조건이 ETF에도 그대로 유효하고, ETF 특유의 추적 오차 조건만 보강하는 방식이 자연스럽기 때문입니다.

추가 조건의 임계값으로 직전 20거래일 추적 오차의 z-score가 1.5를 초과하는 상태를 사용합니다. z-score 1.5는 정규분포 가정 시 상위 약 6.7%에 해당하며, 직전 20거래일 패턴 대비 추적 오차가 통계적으로 비정상적으로 커진 구간을 식별합니다. 1.5를 임계값으로 선택한 이유는 추적 오차 자체가 평소에도 ±수십 bp 수준의 변동성을 가지므로 2.0보다 약간 완화된 기준이 시연 시 신호 누락을 줄이기 때문입니다.

extend 병합 시 항목별 병합 의미론은 [asset_crypto.md](asset_crypto.md)의 Rule 2에 정의된 규칙을 그대로 따릅니다.

본 룰은 단독으로 매매 판단의 근거가 되지 않으며, 병합된 base 조건과 함께 평가된 결과만 의미를 가집니다.

### 2) YAML 룰 블록

```yaml
- rule_id: momentum_overheating
  rule_name: "단기 모멘텀 과열 (추적오차 z-score 추가)"
  scope: asset
  asset_types: ["etf_us"]
  merge_policy: extend
  extends: momentum_overheating
  required_indicators:
    - name: tracking_error
      type: passthrough
      params: { source: tracking_error }
    - name: tracking_error_ma_20
      type: sma
      params: { window: 20, source: tracking_error }
    - name: tracking_error_std_20
      type: stddev
      params: { window: 20, source: tracking_error }
    - name: tracking_error_zscore
      type: zscore
      params:
        source: tracking_error
        mean: tracking_error_ma_20
        stddev: tracking_error_std_20
  conditions:
    all_of:
      - "tracking_error_zscore > 1.5"
  signal: momentum_overheated
  severity: warn
  visualization: viz_momentum_overheating
  template_variables:
    - tracking_error
    - tracking_error_zscore
```

병합 결과로 최종 적용되는 조건은 base의 `all_of`(RSI / MA20 / 거래량) 항목과 본 룰의 `all_of`(추적 오차 z-score) 항목이 합쳐진 형태입니다.

### 3) 인사이트 템플릿

```yaml
- template_id: insight_momentum_overheating_etf_tracking_error
  bind_to: momentum_overheating
  text: "기존 과열 조건과 함께 추적 오차 z-score가 {tracking_error_zscore:.2f}로 비정상 구간(>1.5)에 있습니다. ETF의 추종 안정성이 저하된 구간으로 함께 관찰할 수 있습니다."
  variables: [tracking_error, tracking_error_zscore]
```

본 템플릿은 base의 `insight_momentum_overheating` 템플릿과 함께 출력되도록 설계되었습니다. 즉, 두 문장이 순서대로 렌더링됩니다.

### 4) 추천 행동

- 추적 오차가 비정상적으로 큰 상태는 ETF의 시장가와 NAV가 일시적으로 어긋나거나 운용사의 리밸런싱 지연이 발생했을 가능성을 시사하므로, 단기 매수 시 시장가보다 지정가 주문을 검토할 수 있습니다.
- ETF의 일반적인 추적 오차 수준을 운용사 공시(보통 KIID 또는 fact sheet)에서 함께 확인하시기 바랍니다.
- 본 룰은 단독으로 매매 판단의 근거가 되지 않으며, 추적 오차 외부 원인(시장 마감 직전 호가 불균형 등) 가능성을 함께 고려하시기 바랍니다.

---

## Rule 2. [inherit] volatility_expansion

### 1) 사람이 읽는 설명

base의 `volatility_expansion` 룰을 미국 ETF 자산군에서도 변경 없이 그대로 상속합니다.

볼린저 밴드 폭 확대는 자산군에 관계없이 변동성 증가의 일반적인 신호로 해석할 수 있으므로, ETF 전용 임계값 조정이나 추가 조건을 적용하지 않습니다.

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

## Rule 3. [inherit] trend_cross_signal

### 1) 사람이 읽는 설명

base의 `trend_cross_signal` 룰을 미국 ETF 자산군에서도 변경 없이 그대로 상속합니다.

20일/60일 이동평균 교차는 자산군에 관계없이 추세 전환의 일반적 관찰 신호이며, ETF 전용 임계값 조정이 필요하지 않습니다.

### 2) YAML 룰 블록

```yaml
- rule_id: trend_cross_signal
  merge_policy: inherit
  inherit_from: base
```

### 3) 인사이트 템플릿

base의 `insight_trend_cross_signal` 템플릿을 그대로 사용합니다.

### 4) 추천 행동

base의 추천 행동을 그대로 따릅니다.

---

## Rule 4. [etf-us-only] nav_premium_anomaly

### 1) 사람이 읽는 설명

거래소 가격(close)과 순자산가치(NAV)의 괴리율 절댓값이 0.5%(0.005)를 초과하는 비정상 구간을 감지하는 ETF 전용 룰입니다.

NAV 괴리율은 다음과 같이 정의됩니다.

- `nav_premium = (close - nav) / nav`
- 양수: 거래소 가격이 NAV보다 높음 (premium 상태)
- 음수: 거래소 가격이 NAV보다 낮음 (discount 상태)

정상 ETF의 일중 NAV 괴리율은 일반적으로 ±0.5% 이내로 유지됩니다. 시장가가 NAV에서 크게 벗어난 경우 차익거래(arbitrage)가 발생하여 가격이 NAV로 수렴하는 것이 일반적입니다. 따라서 절댓값 0.5%를 초과한 상태는 단기적 유동성 부족, 시장 마감 직전 호가 왜곡, 또는 일시적 차익거래 비효율 등을 시사합니다.

본 룰은 base에 대응되는 룰이 없는 신규 룰로, ETF 자산군 스코프에서만 평가됩니다.

본 룰은 단독으로 매매 판단의 근거가 되지 않으며, 일시적 NAV 괴리는 시장 정상화 과정에서 자동 해소될 수 있음을 함께 고려하시기 바랍니다.

### 2) YAML 룰 블록

```yaml
- rule_id: nav_premium_anomaly
  rule_name: "NAV 괴리율 비정상"
  scope: asset
  asset_types: ["etf_us"]
  merge_policy: asset_only
  required_indicators:
    - name: nav
      type: passthrough
      params: { source: nav }
    - name: nav_diff
      type: linear
      params:
        source_a: close
        source_b: nav
        coef_a: 1
        coef_b: -1
    - name: nav_premium
      type: ratio
      params:
        numerator: nav_diff
        denominator: nav
    - name: abs_nav_premium
      type: abs
      params: { source: nav_premium }
    - name: nav_premium_pct
      type: linear
      params: { source: nav_premium, multiplier: 100 }
  conditions:
    all_of:
      - "abs_nav_premium > 0.005"
  signal: nav_premium_anomaly
  severity: warn
  visualization: viz_nav_premium_anomaly
  template_variables:
    - nav
    - close
    - nav_premium
    - abs_nav_premium
    - nav_premium_pct
```

### 3) 인사이트 템플릿

```yaml
- template_id: insight_nav_premium_anomaly
  bind_to: nav_premium_anomaly
  text: "NAV 괴리율이 {nav_premium:+.4f}({nav_premium_pct:+.2f}%)로 정상 범위(±0.5%)를 초과했습니다. 거래소 가격이 순자산가치와 분리된 비정상 구간으로 관찰할 수 있습니다."
  variables: [nav, close, nav_premium, abs_nav_premium, nav_premium_pct]
```

### 4) 추천 행동

- NAV 괴리율이 큰 ETF는 매수/매도 시점에 따라 실제 자산 가치 대비 손실 또는 이익이 발생할 수 있습니다. 거래 전 NAV 추정치(iNAV)를 함께 확인하시기 바랍니다.
- 시장가 주문보다 NAV에 가까운 가격대로 지정가 주문을 검토할 수 있습니다.
- 괴리가 일시적인지 구조적인지 판별하기 위해 직전 며칠의 괴리율 추이도 함께 관찰하시기 바랍니다.

---

## 병합 결과 요약

| rule_id | base 적용 | etf_us override | etf_us extend | etf_us only | 최종 결과 |
|---------|----------|-----------------|---------------|-------------|-----------|
| momentum_overheating | yes | — | yes (추적오차 z-score) | — | base 조건 + extend 조건 합집합 적용 |
| momentum_oversold | yes | — | — | — | base 그대로 |
| trend_cross_signal | yes | — | — | — | base 그대로 (명시적 inherit 선언) |
| volatility_expansion | yes | — | — | — | base 그대로 (명시적 inherit 선언) |
| nav_premium_anomaly | — | — | — | yes | etf_us에서만 평가 |

병합 우선순위: `override > extend > base inherit`. 같은 `rule_id`에 여러 오버레이가 있을 때 우선순위가 높은 정책 하나만 적용됩니다.
