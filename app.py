"""RuleCraft Invest Streamlit 진입점 (Stage 1 MVP).

스코프:
- 코인 단일 자산군
- CSV 1개 업로드 → base + crypto override 병합 → 인사이트 1개 + 차트 1개
- LLM 호출 없음, 컬럼 자동 매핑 없음 (CSV는 표준 컬럼명 가정)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from engine.indicators import compute_required_indicators
from engine.loader import load_skills
from engine.matcher import evaluate_conditions, merge_rules
from engine.renderer import find_template, render_insight


PROJECT_ROOT = Path(__file__).parent
SKILLS_DIR = PROJECT_ROOT / "skills"
DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_PATH = DATA_DIR / "sample_btc.csv"

REQUIRED_COLUMNS = ("date", "open", "high", "low", "close", "volume")

SEVERITY_COLORS = {
    "info": "#00d4ff",
    "warn": "#ffb454",
    "alert": "#ff5577",
}


@st.cache_data
def _load_skills_cached(skills_path: str) -> dict:
    return load_skills(skills_path)


def _latest_values(df: pd.DataFrame, indicators: dict[str, pd.Series]) -> dict:
    """마지막 행의 컬럼 값과 인디케이터 값을 dict로 묶는다.

    Stage 2-1A: 문자열 인디케이터(limit_side 등)도 그대로 보존한다.
    숫자는 float으로 정규화하고, NaN은 제외한다.
    """
    values: dict = {}
    for col in df.columns:
        last = df[col].iloc[-1]
        if isinstance(last, str):
            values[col] = last
        elif isinstance(last, (int, float)) and not pd.isna(last):
            values[col] = float(last)
    for name, series in indicators.items():
        last = series.iloc[-1]
        if isinstance(last, str):
            values[name] = last
        else:
            try:
                if pd.isna(last):
                    continue
            except (TypeError, ValueError):
                continue
            values[name] = float(last)
    return values


def _evaluate_rule(
    rule: dict, df: pd.DataFrame
) -> tuple[bool, dict[str, float]]:
    """단일 룰을 데이터에 대해 평가. 인디케이터/조건 오류는 미매칭으로 처리."""
    try:
        indicators = compute_required_indicators(rule, df)
    except (NotImplementedError, KeyError, ValueError):
        return False, {}

    values = _latest_values(df, indicators)
    try:
        matched = evaluate_conditions(rule, values)
    except (KeyError, ValueError):
        return False, values
    return matched, values


def _build_chart(df: pd.DataFrame) -> go.Figure:
    ma_20 = df["close"].rolling(window=20, min_periods=20).mean()

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.72, 0.28],
        vertical_spacing=0.04,
    )
    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="가격",
            increasing_line_color="#00d4ff",
            decreasing_line_color="#ff5577",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=ma_20,
            mode="lines",
            name="MA20",
            line=dict(color="#ffb454", width=1.5),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["volume"],
            name="거래량",
            marker_color="#3a4150",
        ),
        row=2,
        col=1,
    )
    fig.update_layout(
        template="plotly_dark",
        showlegend=True,
        legend=dict(orientation="h", y=1.05, x=0),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_rangeslider_visible=False,
        height=460,
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#2a2e39")
    return fig


def _render_insight_card(rule: dict, text: str) -> None:
    severity = rule.get("severity", "info")
    color = SEVERITY_COLORS.get(severity, "#00d4ff")
    signal = rule.get("signal", "")
    rule_name = rule.get("rule_name", rule.get("rule_id", ""))

    st.markdown(
        f"""
        <div style="
            background: #1e2029;
            border-left: 4px solid {color};
            border-radius: 6px;
            padding: 18px 22px;
            margin: 8px 0 16px 0;
        ">
            <div style="display:flex; align-items:center; gap:14px; margin-bottom:10px; flex-wrap:wrap;">
                <span style="
                    color: {color};
                    font-weight: 700;
                    font-size: 12px;
                    letter-spacing: 0.08em;
                    text-transform: uppercase;
                ">{severity}</span>
                <span style="color: #fafafa; font-weight: 600; font-size: 16px;">{rule_name}</span>
                <span style="color: #6c7080; font-size: 13px;">signal: {signal}</span>
            </div>
            <div style="color: #d8dde6; font-size: 15px; line-height: 1.65;">
                {text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_header(source_name: str, last_date: str, last_close: float, signals: list[str]) -> None:
    left, right = st.columns([3, 2])
    with left:
        st.markdown(
            f"""
            <div style="padding: 6px 0;">
                <div style="color:#6c7080; font-size:12px; letter-spacing:0.06em; text-transform:uppercase;">자산 · 분석일</div>
                <div style="color:#fafafa; font-size:24px; font-weight:600; margin-top:2px;">{source_name} · {last_date}</div>
                <div style="color:#d8dde6; font-size:14px; margin-top:4px;">최근 종가: {last_close:,.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        if signals:
            joined = ", ".join(f"<code style='background:#1e2029; padding:2px 8px; border-radius:4px; color:#00d4ff;'>{s}</code>" for s in signals[:2])
            inner = f"<div style='color:#fafafa; font-size:18px; font-weight:600;'>{joined}</div>"
        else:
            inner = "<div style='color:#6c7080; font-size:18px;'>현재 매칭된 신호 없음</div>"
        st.markdown(
            f"""
            <div style="padding: 6px 0; text-align:right;">
                <div style="color:#6c7080; font-size:12px; letter-spacing:0.06em; text-transform:uppercase;">핵심 신호</div>
                {inner}
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    st.set_page_config(page_title="RuleCraft Invest", layout="wide")

    with st.sidebar:
        st.title("RuleCraft Invest")
        st.caption("Stage 1 MVP — crypto 단일 자산군")

        uploaded = st.file_uploader("CSV 업로드", type=["csv"])
        asset_type = st.selectbox("자산군", options=["crypto"], index=0)
        run = st.button("분석 실행", type="primary", use_container_width=True)

        st.divider()
        if SAMPLE_PATH.exists():
            st.caption(f"업로드 없을 시 샘플 사용: `{SAMPLE_PATH.name}`")
        else:
            st.caption("샘플 데이터 미준비 (data/sample_btc.csv 없음)")

    if not run:
        st.markdown("### 분석 결과")
        st.info(
            "좌측 사이드바에서 CSV를 업로드하고 **분석 실행** 버튼을 눌러주세요. "
            "업로드가 없으면 샘플 BTC 일봉 데이터가 사용됩니다."
        )
        return

    if uploaded is not None:
        df = pd.read_csv(uploaded)
        source_name = uploaded.name
    else:
        if not SAMPLE_PATH.exists():
            st.error("업로드된 파일도, 샘플 데이터도 없습니다.")
            return
        df = pd.read_csv(SAMPLE_PATH)
        source_name = SAMPLE_PATH.name

    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        st.error(f"필수 컬럼 누락: {sorted(missing)}. Stage 1은 표준 컬럼명만 지원합니다.")
        return

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    skills = _load_skills_cached(str(SKILLS_DIR))
    merged = merge_rules(skills["rules"], asset_type=asset_type)
    templates = skills["templates"]

    matches: list[tuple[dict, str]] = []
    for rule in merged:
        matched, values = _evaluate_rule(rule, df)
        if not matched:
            continue
        tpl = find_template(templates, rule["rule_id"], available_keys=set(values))
        if tpl is None:
            continue
        try:
            text = render_insight(tpl["text"], values)
        except (KeyError, ValueError):
            continue
        matches.append((rule, text))

    last_date = df["date"].iloc[-1].strftime("%Y-%m-%d")
    last_close = float(df["close"].iloc[-1])
    signals = [r.get("signal", "") for r, _ in matches]

    _render_header(source_name, last_date, last_close, signals)
    st.divider()

    if matches:
        rule, text = matches[0]
        _render_insight_card(rule, text)
    else:
        st.markdown(
            """
            <div style="
                background:#1e2029; border-radius:6px; padding:18px 22px;
                color:#6c7080; font-size:14px; text-align:center; margin: 8px 0 16px 0;
            ">
                현재 룰에 매칭된 신호가 없습니다. 데이터 범위 또는 Skills 룰의 임계값을 조정해 보세요.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.plotly_chart(_build_chart(df), use_container_width=True)


if __name__ == "__main__":
    main()
