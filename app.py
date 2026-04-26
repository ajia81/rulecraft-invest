"""RuleCraft Invest Streamlit 진입점.

Stage 2-2: 다중 자산군 지원 (crypto, stock_kr).
- 사이드바 selectbox로 자산군 선택
- 업로드 없을 시 자산군별 샘플(sample_btc.csv / sample_kospi.csv) 자동 매핑
- 룰 엔진은 base.md + 모든 asset_*.md를 자동 로드 (Stage 2-2 loader)
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

ASSET_TYPES = ["crypto", "stock_kr"]

SAMPLE_PATHS = {
    "crypto": DATA_DIR / "sample_btc.csv",
    "stock_kr": DATA_DIR / "sample_kospi.csv",
}

ASSET_NAME_OVERRIDES = {
    "sample_btc.csv": "BTC-Demo",
    "sample_kospi.csv": "DemoStock-A (KOSPI)",
}

REQUIRED_COLUMNS = ("date", "open", "high", "low", "close", "volume")

SEVERITY_COLORS = {
    "info": "#00d4ff",
    "warn": "#ffb454",
    "alert": "#ff5577",
}


def _resolve_asset_name(file_name: str) -> str:
    """CSV 파일명을 사용자에게 보여줄 자산명으로 변환."""
    if file_name in ASSET_NAME_OVERRIDES:
        return ASSET_NAME_OVERRIDES[file_name]
    return file_name.rsplit(".", 1)[0]


@st.cache_data
def _load_skills_cached(skills_path: str) -> dict:
    return load_skills(skills_path)


def _latest_values(df: pd.DataFrame, indicators: dict[str, pd.Series]) -> dict:
    """마지막 행의 컬럼 값과 인디케이터 값을 dict로 묶는다.

    문자열 인디케이터(limit_side 등)는 그대로 보존, 숫자는 float으로 정규화,
    NaN/Timestamp 등 비교 불가능한 값은 제외.
    """
    values: dict = {}
    for col in df.columns:
        last = df[col].iloc[-1]
        if isinstance(last, str):
            values[col] = last
            continue
        try:
            if pd.isna(last):
                continue
        except (TypeError, ValueError):
            pass
        try:
            values[col] = float(last)
        except (TypeError, ValueError):
            continue
    for name, series in indicators.items():
        last = series.iloc[-1]
        if isinstance(last, str):
            values[name] = last
            continue
        try:
            if pd.isna(last):
                continue
        except (TypeError, ValueError):
            pass
        try:
            values[name] = float(last)
        except (TypeError, ValueError):
            continue
    return values


def _evaluate_rule(
    rule: dict, df: pd.DataFrame
) -> tuple[bool, dict]:
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


def _render_header(
    asset_name: str, last_date: str, last_close: float, signals: list[str]
) -> None:
    left, right = st.columns([3, 2])
    with left:
        st.markdown(
            f"""
            <div style="padding: 6px 0;">
                <div style="color:#6c7080; font-size:12px; letter-spacing:0.06em; text-transform:uppercase;">자산 · 분석일</div>
                <div style="color:#fafafa; font-size:24px; font-weight:600; margin-top:2px;">{asset_name} · {last_date}</div>
                <div style="color:#d8dde6; font-size:14px; margin-top:4px;">최근 종가: {last_close:,.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        if signals:
            joined = ", ".join(
                f"<code style='background:#1e2029; padding:2px 8px; border-radius:4px; color:#00d4ff;'>{s}</code>"
                for s in signals[:2]
            )
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
        st.caption("Stage 2 — 다중 자산군 지원 (crypto, stock_kr)")

        uploaded = st.file_uploader("CSV 업로드", type=["csv"])
        asset_type = st.selectbox("자산군", options=ASSET_TYPES, index=0)
        run = st.button("분석 실행", type="primary", width="stretch")

        st.divider()
        sample_path = SAMPLE_PATHS.get(asset_type)
        if sample_path is not None and sample_path.exists():
            st.caption(f"업로드 없을 시 샘플 사용: `{sample_path.name}`")
        else:
            st.caption(f"샘플 데이터 미준비 (자산군: {asset_type})")

    if not run:
        st.markdown("### 분석 결과")
        st.info(
            "좌측 사이드바에서 자산군을 선택하고 CSV를 업로드한 뒤 **분석 실행**을 누르세요. "
            "업로드가 없으면 자산군에 맞는 샘플 데이터가 사용됩니다."
        )
        return

    if uploaded is not None:
        df = pd.read_csv(uploaded)
        source_name = uploaded.name
    else:
        sample_path = SAMPLE_PATHS.get(asset_type)
        if sample_path is None or not sample_path.exists():
            st.error(f"업로드된 파일도 없고, 자산군 '{asset_type}'에 대한 샘플 데이터도 없습니다.")
            return
        df = pd.read_csv(sample_path)
        source_name = sample_path.name

    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        st.error(f"필수 컬럼 누락: {sorted(missing)}. 표준 컬럼명만 지원합니다.")
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
    asset_name = _resolve_asset_name(source_name)

    _render_header(asset_name, last_date, last_close, signals)
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

    st.plotly_chart(_build_chart(df), width="stretch")


if __name__ == "__main__":
    main()
