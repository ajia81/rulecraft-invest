# RuleCraft Invest

해커톤 제출용 금융 투자 대시보드 생성 시스템.

## 1. 시스템 정의

Skills.md 한 파일에 정의된 투자 분석 기준을 결정론적 룰 엔진이 해석하여, 사용자가 업로드한 시계열 데이터에 대해 자산군별 인사이트와 대시보드를 자동 생성한다.

- 입력: Skills.md (분석 기준), 사용자 데이터 (CSV/Parquet 시계열)
- 출력: 인사이트 텍스트, 시각화가 포함된 대시보드
- 지원 자산군: 한국 주식, 미국 ETF, 코인 (3종)

## 2. 핵심 컨셉

| 구성요소 | 역할 |
|----------|------|
| Skills.md | 사람이 읽는 설명 + 기계가 읽는 YAML 룰 + 인사이트 템플릿 + 시각화 지정 |
| AI 컬럼 매퍼 | 사용자 데이터의 컬럼을 룰이 요구하는 표준 필드에 매핑 추천 |
| 룰 엔진 | 자산군 감지 → 룰 병합 → 지표 계산 → 조건 평가 → 인사이트 렌더링 |
| LLM 다듬기 | 룰 엔진이 산출한 인사이트 문장의 자연어 표현만 다듬음 |

## 3. 설계 원칙 (변경 금지)

1. **Skills.md 구조 4분할**: 사람 설명 / YAML 룰 블록 / 인사이트 템플릿 / 시각화 지정
2. **룰 병합 우선순위**: `asset rule override > asset rule extend > base rule inherit`
3. **룰 엔진 파이프라인**: `load_skills → parse_yaml_blocks → detect_asset_type → merge_rules → calculate_indicators → evaluate_conditions → render_insight_template → choose_visualization`
4. **LLM은 투자 판단자가 아니다**. 모든 매수/매도/리스크 판단은 결정론적 코드가 수행한다. LLM은 인사이트 문장의 자연스러움만 보조한다.
5. **컬럼 매핑은 AI 추천 + 사용자 확인**. 자동 적용 금지.
6. **해커톤 범위 밖 기능 금지**.

## 4. Skills.md 형식 명세

Skills.md는 다음 4개 섹션을 포함한다. 모든 YAML 블록은 코드 파서가 읽을 수 있도록 표준 키를 사용한다.

### 4.1 사람용 설명 (Markdown)
분석 의도, 자산군별 차이, 룰 변경 시 결과가 어떻게 달라지는지 서술.

### 4.2 룰 정의 (YAML 블록)
```yaml
rules:
  - id: <rule_id>
    scope: base | korean_stock | us_etf | crypto
    mode: inherit | extend | override
    requires: [<column_name>, ...]   # 표준 필드 목록
    indicators:
      - name: <indicator_name>
        type: sma | ema | rsi | volatility | drawdown | ...
        params: { window: 20, ... }
    conditions:
      - when: "<expression on indicators>"
        emit: <insight_template_id>
        severity: info | warn | alert
```

### 4.3 인사이트 템플릿
```yaml
insights:
  - id: <insight_template_id>
    text: "지난 {window}일 변동성이 {volatility:.2%}로 평균 대비 {ratio:.1f}배입니다."
    variables: [window, volatility, ratio]
```

### 4.4 시각화 지정
```yaml
visualizations:
  - id: <viz_id>
    bind_to: <rule_id>
    chart: line | bar | candlestick | heatmap
    series: [{ field: <indicator_name>, label: "..." }]
```

## 5. 룰 엔진 동작 (결정론적)

```
load_skills(Skills.md)
  → parse_yaml_blocks()         # rules / insights / visualizations 분리
  → detect_asset_type(data)     # 컬럼/메타데이터로 자산군 추정
  → merge_rules(asset_type)     # base ⊂ extend ⊂ override 순으로 병합
  → calculate_indicators(data, merged_rules)
  → evaluate_conditions()       # when 표현식 평가
  → render_insight_template()   # 변수 바인딩
  → choose_visualization()      # bind_to 매칭으로 차트 선택
```

각 단계는 입력/출력이 명확한 순수 함수로 구현한다. LLM 호출은 마지막 인사이트 문장 다듬기에서만 발생한다.

## 6. 컬럼 매핑 흐름

1. 사용자가 데이터 업로드
2. AI가 각 컬럼을 표준 필드(`date`, `open`, `high`, `low`, `close`, `volume` 등)에 매핑 추천
3. 사용자가 매핑 확인/수정
4. 확정된 매핑을 룰 엔진에 전달

자동 적용은 절대 하지 않는다.

## 7. 만들지 않을 것

- 거시경제 예측
- 뉴스 감성 분석
- 실시간 시세 API 의존
- 화려한 애니메이션
- 차트 종류 과다 추가
- 복잡한 백테스트 엔진
- LLM 기반 투자 판단

## 8. 시연 시나리오

동일한 시스템에 같은 Skills.md를 적용하여 3개 자산군에서 서로 다른 결과가 나오는 것을 보여준다.

1. 한국 주식 데이터 업로드 → 컬럼 매핑 확인 → 한국 주식 룰 적용 결과 표시
2. 미국 ETF 데이터로 교체 → 동일 Skills.md, 다른 룰 분기 결과
3. 코인 데이터로 교체 → 동일 Skills.md, 또 다른 룰 분기 결과
4. Skills.md의 임계값 한 줄 수정 → 결과가 즉시 바뀌는 것을 시연

## 9. 코드 작성 규칙

- 모든 룰은 YAML 파서가 읽을 수 있는 형식으로 작성한다.
- 룰 엔진 함수는 단일 책임. 각 단계가 독립적으로 테스트 가능해야 한다.
- LLM 호출은 단 한 곳(인사이트 문장 다듬기)에서만 발생한다. 다른 단계에 LLM을 끼워 넣지 않는다.
- 자산군 분기는 `merge_rules` 안에서만 처리한다. 비즈니스 로직 곳곳에 if asset_type 분기를 흩뿌리지 않는다.
- 해커톤 범위 밖 기능을 추가하기 전에 반드시 확인을 받는다.
