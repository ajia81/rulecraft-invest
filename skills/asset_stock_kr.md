# Skills: Korean Stock Rules

한국 주식 자산군 전용 룰 정의. [base.md](base.md)에 정의된 공통 룰을 `override`, `extend`, `inherit`으로 오버레이하고, 한국 주식 시장에서만 의미를 가지는 신규 룰을 추가한다.

## 자산군 특성 요약

- 정규 거래 시간이 09:00 ~ 15:30 (KST)으로 제한되며, 시간외 거래는 별도 세션으로 운영됩니다.
- 일일 가격 변동 제한폭 상한가/하한가 ±30%가 존재하여 가격이 일정 구간을 벗어나지 못합니다.
- 외국인 / 기관 / 개인 투자자별 일별 수급 데이터가 거래소 단위로 공개됩니다.
- KOSPI(시가총액 대형주 중심)와 KOSDAQ(중소형주 중심)으로 시장이 구분되며, 두 시장의 평균 변동성이 다릅니다.
- 시가/종가 단일가 매매(동시호가) 구간이 존재하여 장 시작과 마감 직전 가격 형성 메커니즘이 일중과 다릅니다.

## 문서 구조 규칙

각 룰 헤더에 사람이 읽는 태그를 부여하여 base 룰에 대한 오버레이 의미를 표시합니다. 사람이 읽는 태그는 YAML의 `merge_policy` 값과 1:1로 대응되며, 매핑은 다음과 같습니다.

| 헤더 태그 | YAML `merge_policy` | 의미 |
|----------|---------------------|------|
| `[override]` | `override` | base 룰의 정의를 통째로 자산군 룰로 교체 |
| `[extend]` | `extend` | base 룰을 보존한 채 인디케이터·조건·템플릿 변수를 합집합으로 확장 |
| `[inherit]` | `inherit` | base 룰을 변경 없이 그대로 상속 |
| `[stock-kr-only]` | `asset_only` | base에 대응 룰이 없고 해당 자산군 스코프에서만 평가되는 룰 |

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

base의 `momentum_overheating` 룰에 외국인 매도 우위 조건을 추가합니다.

한국 시장은 외국인 수급 비중이 크고 기관·개인과 매매 패턴이 구조적으로 다릅니다. 단기 과열 구간에서 외국인이 매도 우위 상태를 유지하고 있는 경우, 매수 주체가 개인·기관 일부에 한정되었을 가능성이 있어 단기 평균 회귀 가능성이 추가로 높아진 상태로 해석할 수 있습니다.

`override`가 아닌 `extend`를 선택한 이유는, base의 RSI(14) / MA20 / 거래량 조건이 한국 주식에도 그대로 유효하기 때문입니다. 한국 시장 특성을 보강하는 외국인 수급 조건만 추가하는 방식이 더 자연스럽습니다.

추가 조건의 임계값으로 직전 5거래일 외국인 순매수 평균(`foreign_net_buy_ma_5`)이 0보다 작은 상태(누적 매도 우위)를 사용합니다. 5일 평균 외국인 순매수가 0 미만이라는 조건은 외국인 수급이 매수 우위에서 매도 우위로 전환된 상태로 볼 수 있으며, 0은 매수와 매도의 부호가 갈리는 자연스러운 기준점입니다. 단일 거래일이 아니라 5일 평균을 사용하는 이유는 일중 변동에 의한 노이즈를 줄이기 위함입니다.

본 룰은 단독으로 매매 판단의 근거가 되지 않으며, 병합된 base 조건과 함께 평가된 결과만 의미를 가집니다.

extend 병합 시 항목별 병합 의미론은 [asset_crypto.md](asset_crypto.md)의 Rule 2에 정의된 규칙을 그대로 따릅니다.

### 2) YAML 룰 블록

```yaml
- rule_id: momentum_overheating
  rule_name: "단기 모멘텀 과열 (외국인 매도 우위 추가)"
  scope: asset
  asset_types: ["stock_kr"]
  merge_policy: extend
  extends: momentum_overheating
  required_indicators:
    - name: foreign_net_buy
      type: passthrough
      params: { source: foreign_net_buy }
    - name: foreign_net_buy_ma_5
      type: sma
      params: { window: 5, source: foreign_net_buy }
  conditions:
    all_of:
      - "foreign_net_buy_ma_5 < 0"
  signal: momentum_overheated
  severity: warn
  visualization: viz_momentum_overheating
  template_variables:
    - foreign_net_buy
    - foreign_net_buy_ma_5
```

병합 결과로 최종 적용되는 조건은 base의 `all_of`(RSI / MA20 / 거래량) 항목과 본 룰의 `all_of`(외국인 매도 우위) 항목이 합쳐진 형태입니다.

### 3) 인사이트 템플릿

```yaml
- template_id: insight_momentum_overheating_foreign_selling
  bind_to: momentum_overheating
  text: "기존 과열 조건과 함께 직전 5거래일 외국인 순매수 평균이 {foreign_net_buy_ma_5}로 매도 우위 상태입니다. 매수 주체가 제한된 단기 과열 구간으로 관찰할 수 있습니다."
  variables: [foreign_net_buy, foreign_net_buy_ma_5]
```

본 템플릿은 base의 `insight_momentum_overheating` 템플릿과 함께 출력되도록 설계되었습니다. 즉, 두 문장이 순서대로 렌더링됩니다.

### 4) 추천 행동

- 외국인 매도가 누적되는 구간의 단기 강세는 매수 주체가 제한적일 가능성이 있으므로 신규 진입 시 분할 진입을 검토할 수 있습니다.
- 기관 수급이 같은 방향(매도)인지 별도로 확인하면 신호의 신뢰도를 보강할 수 있습니다.
- 외국인 수급은 환율, 외국 지수 변동 등 외부 요인의 영향을 함께 받으므로 단일 지표로 단정하지 않도록 유의하시기 바랍니다.

---

## Rule 2. [inherit] trend_cross_signal

### 1) 사람이 읽는 설명

base의 `trend_cross_signal` 룰을 한국 주식 자산군에서도 변경 없이 그대로 상속합니다.

20일/60일 이동평균 교차는 자산군에 관계없이 추세 전환의 일반적 관찰 신호로 활용 가능하며, 한국 주식 특유의 임계값 조정이나 추가 조건이 필요하지 않습니다.

### 2) YAML 룰 블록

```yaml
- rule_id: trend_cross_signal
  merge_policy: inherit
  inherit_from: base
```

`inherit` 룰은 본 키 외의 정의를 가지지 않습니다. 룰 엔진은 `inherit_from`에 지정된 스코프(`base`)에서 동일 `rule_id`의 룰을 그대로 가져와 자산군에 적용합니다.

### 3) 인사이트 템플릿

base의 `insight_trend_cross_signal` 템플릿을 그대로 사용합니다. 별도 템플릿 정의가 없습니다.

### 4) 추천 행동

base의 추천 행동을 그대로 따릅니다.

---

## Rule 3. [stock-kr-only] price_limit_proximity

### 1) 사람이 읽는 설명

종가가 일일 가격 제한폭(상한가 +30% 또는 하한가 -30%)에 근접한 상태를 감지하는 한국 주식 전용 룰입니다.

다음 두 신규 인디케이터를 정의합니다.

- `limit_upper`: 직전 거래일 종가의 1.30배 (상한가)
- `limit_lower`: 직전 거래일 종가의 0.70배 (하한가)
- `limit_proximity_ratio`: 어느 한쪽 제한가까지의 근접도. `max(close / limit_upper, limit_lower / close)`로 계산되며, 값이 1에 가까울수록 가격이 제한가에 근접한 상태입니다.

신호 발생 조건은 `limit_proximity_ratio >= 0.95`이며, 이는 종가가 상한가 대비 95% 이상 도달했거나 하한가 대비 105% 이내(즉 하한가의 1.05배 이내)에 위치한 경우를 포괄합니다. 임계값 0.95는 한쪽 제한가의 5% 이내 구간을 비정상 가격 형성 가능 구간으로 분류한다는 단순한 정책에 근거합니다.

가격 제한가 부근에서는 정상적인 호가 형성이 어려워질 가능성이 있고, 익일 갭(gap) 발생 가능성도 함께 높아집니다. 본 룰은 매매 판단이 아니라 거래 환경 자체에 대한 주의 환기 신호로 활용합니다.

### 2) YAML 룰 블록

```yaml
- rule_id: price_limit_proximity
  rule_name: "가격 제한가 근접"
  scope: asset
  asset_types: ["stock_kr"]
  merge_policy: asset_only
  required_indicators:
    - name: prev_close
      type: lag
      params: { source: close, periods: 1 }
    - name: limit_upper
      type: linear
      params: { source: prev_close, multiplier: 1.30 }
    - name: limit_lower
      type: linear
      params: { source: prev_close, multiplier: 0.70 }
    - name: limit_proximity_ratio
      type: limit_proximity
      params:
        source: close
        upper_limit: limit_upper
        lower_limit: limit_lower
        method: max_normalized
    - name: limit_side
      type: limit_side_label
      params:
        source: close
        upper_limit: limit_upper
        lower_limit: limit_lower
  conditions:
    all_of:
      - "limit_proximity_ratio >= 0.95"
  signal: price_limit_near
  severity: warn
  visualization: viz_price_limit_proximity
  template_variables:
    - close
    - limit_upper
    - limit_lower
    - limit_proximity_ratio
    - limit_side
```

`limit_side`는 룰 엔진이 `close`와 두 제한가의 위치 관계에서 파생합니다. 종가가 상한가에 가까우면 `"upper"`, 하한가에 가까우면 `"lower"`, 어느 쪽도 아니면 `"neutral"`로 바인딩됩니다.

### 3) 인사이트 템플릿

```yaml
- template_id: insight_price_limit_proximity
  bind_to: price_limit_proximity
  text: "종가 {close}가 {limit_side} 제한가에 근접한 상태이며, 근접 비율은 {limit_proximity_ratio:.3f}입니다. 상한가 {limit_upper:.2f}, 하한가 {limit_lower:.2f} 기준입니다. 가격 제한 영향으로 인한 비정상적 가격 형성 가능성을 관찰할 수 있습니다."
  variables: [close, limit_upper, limit_lower, limit_proximity_ratio, limit_side]
```

### 4) 추천 행동

- 상한가 근접 시 익일 시초가 갭다운, 하한가 근접 시 익일 시초가 갭업 가능성을 함께 검토할 수 있습니다.
- 제한가 부근에서는 호가 매매가 비대칭적으로 형성될 수 있으므로 시장가 주문보다 지정가 주문을 검토하시기 바랍니다.
- 본 룰은 거래 환경에 대한 주의 환기 신호이며, 단독으로 매매 판단의 근거로 사용하지 않습니다.

---

## Rule 4. [stock-kr-only] foreign_net_buying_surge

### 1) 사람이 읽는 설명

외국인 일별 순매수 금액이 직전 20거래일 분포 대비 비정상적으로 큰 양의 값을 기록한 상태를 감지하는 한국 주식 전용 룰입니다.

신규 인디케이터 `foreign_net_buy_zscore`는 직전 20거래일 외국인 순매수의 평균 및 표준편차를 사용한 z-score(`(현재값 - 평균) / 표준편차`)로 정의됩니다.

신호 발생 조건은 `foreign_net_buy_zscore > 2.0`입니다. 임계값 2.0은 정규분포 가정 시 상위 약 2.3%에 해당하는 구간으로, 직전 20거래일 패턴 대비 통계적으로 비정상적인 외국인 매수 유입 구간으로 분류한다는 근거에 기반합니다. 정규분포 가정이 완전히 성립하지 않더라도, 일관된 통계적 기준으로 비정상 구간을 식별할 수 있다는 운영상의 단순성 때문에 z-score를 사용합니다.

20거래일 윈도우는 약 1개월의 영업일에 해당하며, 단기 노이즈가 충분히 평탄화되면서도 분기 단위 추세가 과도하게 섞이지 않는 균형점으로 활용합니다. 윈도우를 더 짧게 잡으면 단기 변동에 민감해지고, 더 길게 잡으면 최근 수급 변화의 감지가 늦어질 수 있습니다.

본 룰은 외국인 매수 유입의 비정상성만을 신호로 발생시키며, 매도 방향의 비정상성(z-score < -2.0)은 다루지 않습니다. 매도 방향이 필요한 경우 별도 룰로 분리하여 정의해야 합니다.

본 룰은 단독으로 매수 판단의 근거가 되지 않으며, 추세·모멘텀 룰의 결과와 함께 해석합니다.

### 2) YAML 룰 블록

```yaml
- rule_id: foreign_net_buying_surge
  rule_name: "외국인 순매수 급증"
  scope: asset
  asset_types: ["stock_kr"]
  merge_policy: asset_only
  required_indicators:
    - name: foreign_net_buy
      type: passthrough
      params: { source: foreign_net_buy }
    - name: foreign_net_buy_ma_20
      type: sma
      params: { window: 20, source: foreign_net_buy }
    - name: foreign_net_buy_std_20
      type: stddev
      params: { window: 20, source: foreign_net_buy }
    - name: foreign_net_buy_zscore
      type: zscore
      params:
        source: foreign_net_buy
        mean: foreign_net_buy_ma_20
        stddev: foreign_net_buy_std_20
  conditions:
    all_of:
      - "foreign_net_buy_zscore > 2.0"
  signal: foreign_net_buying_surge
  severity: info
  visualization: viz_foreign_net_buying_surge
  template_variables:
    - foreign_net_buy
    - foreign_net_buy_ma_20
    - foreign_net_buy_zscore
```

### 3) 인사이트 템플릿

```yaml
- template_id: insight_foreign_net_buying_surge
  bind_to: foreign_net_buying_surge
  text: "외국인 순매수가 {foreign_net_buy}로 직전 20거래일 평균({foreign_net_buy_ma_20}) 대비 z-score {foreign_net_buy_zscore:.2f}를 기록했습니다. 통계적으로 비정상적인 매수 유입 구간으로 관찰할 수 있습니다."
  variables: [foreign_net_buy, foreign_net_buy_ma_20, foreign_net_buy_zscore]
```

### 4) 추천 행동

- 외국인 매수 유입의 지속성 여부를 익일 이후 수급 데이터로 함께 확인하시기 바랍니다.
- 동일 시점에 `momentum_overheating` 신호가 함께 발생한 경우, 단기 강세의 주된 매수 주체가 외국인일 가능성을 함께 해석할 수 있습니다.
- 외국인 수급은 환율 변동, 외국 지수 변동, MSCI 리밸런싱 등 외부 이벤트의 영향을 받을 수 있으므로 본 룰만으로 매수 판단을 단정하지 않도록 유의하시기 바랍니다.

---

## 병합 결과 요약

| rule_id | base 적용 | stock_kr override | stock_kr extend | stock_kr only | 최종 결과 |
|---------|----------|-------------------|-----------------|---------------|-----------|
| momentum_overheating | yes | — | yes (외국인 매도 우위) | — | base 조건 + extend 조건 합집합 적용 |
| momentum_oversold | yes | — | — | — | base 그대로 |
| trend_cross_signal | yes | — | — | — | base 그대로 (명시적 inherit 선언) |
| volatility_expansion | yes | — | — | — | base 그대로 |
| price_limit_proximity | — | — | — | yes | stock_kr에서만 평가 |
| foreign_net_buying_surge | — | — | — | yes | stock_kr에서만 평가 |

병합 우선순위: `override > extend > base inherit`. 같은 `rule_id`에 여러 오버레이가 있을 때 우선순위가 높은 정책 하나만 적용됩니다.
