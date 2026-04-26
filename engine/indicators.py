"""인디케이터 계산.

Stage 2-1A: 모든 Skills 파일의 required_indicators가 평가 가능하도록 type을 확장.

지원 type (compute_indicator의 디스패치 순서대로):
    rsi, sma, stddev, ratio, cross,
    bollinger_upper, bollinger_lower, bollinger_width, bollinger_width_ratio,
    passthrough, abs, lag, zscore, linear,
    limit_proximity, limit_side_label, dispersion

Stage 2-1A 미지원 type을 만나면 NotImplementedError를 발생시켜
matcher가 해당 룰을 silently skip하도록 한다.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


# === Primitive functions ===

def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """단순 평균 기반 RSI(window). 기본 14.

    경계 처리:
    - loss == 0, gain > 0  → RSI = 100 (단방향 강세).
    - loss == 0, gain == 0 → NaN.
    """
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=window, min_periods=window).mean()
    loss = (-delta).clip(lower=0).rolling(window=window, min_periods=window).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = gain / loss
        out = 100 - 100 / (1 + rs)
    return out


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def stddev(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).std()


def ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator / denominator.where(denominator != 0)


def cross(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """fast가 slow를 상향/하향 돌파한 시점을 +1/-1로 표시.

    -  +1: 직전에는 fast <= slow였고 당일 fast > slow가 된 골든크로스.
    -  -1: 직전에는 fast >= slow였고 당일 fast < slow가 된 데드크로스.
    -   0: 그 외 (교차 없음 또는 비교 불가한 첫 행).
    """
    above = (fast > slow).astype(int)
    diff = above.diff().fillna(0).astype(int)
    return diff


def bb_upper(series: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.Series:
    return sma(series, window) + num_std * stddev(series, window)


def bb_lower(series: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.Series:
    return sma(series, window) - num_std * stddev(series, window)


def bb_width(series: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.Series:
    return bb_upper(series, window, num_std) - bb_lower(series, window, num_std)


def bb_width_ratio_fn(
    series: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
    ratio_window: int = 60,
) -> pd.Series:
    """현재 밴드 폭 / 직전 ratio_window일 평균 밴드 폭."""
    width = bb_width(series, window, num_std)
    width_avg = width.rolling(ratio_window, min_periods=ratio_window).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        return width / width_avg.where(width_avg != 0)


def passthrough(series: pd.Series) -> pd.Series:
    return series.copy()


def abs_value(series: pd.Series) -> pd.Series:
    return series.abs()


def lag(series: pd.Series, periods: int = 1) -> pd.Series:
    return series.shift(periods)


def zscore(
    series: pd.Series,
    mean: pd.Series | None = None,
    std: pd.Series | None = None,
    window: int | None = None,
) -> pd.Series:
    """rolling z-score.

    두 가지 형식을 지원:
    - (mean, std) 명시: 외부에서 미리 계산된 평균/표준편차 사용.
    - window 명시: 내부에서 rolling mean/std 계산.
    """
    if mean is None or std is None:
        if window is None:
            raise ValueError("zscore requires either (mean, std) or (window)")
        mean = series.rolling(window, min_periods=window).mean()
        std = series.rolling(window, min_periods=window).std()
    with np.errstate(divide="ignore", invalid="ignore"):
        return (series - mean) / std.where(std != 0)


def linear(
    *,
    source: pd.Series | None = None,
    multiplier: float | None = None,
    source_a: pd.Series | None = None,
    source_b: pd.Series | None = None,
    coef_a: float = 1.0,
    coef_b: float = 1.0,
    intercept: float = 0.0,
) -> pd.Series:
    """선형 변환.

    두 가지 형식을 지원:
    - {source, multiplier, intercept}      → source × multiplier + intercept
    - {source_a, source_b, coef_a, coef_b, intercept}
                                            → coef_a×a + coef_b×b + intercept
    """
    if source is not None and multiplier is not None:
        return source * float(multiplier) + float(intercept)
    if source_a is not None and source_b is not None:
        return float(coef_a) * source_a + float(coef_b) * source_b + float(intercept)
    raise ValueError("linear requires {source, multiplier} or {source_a, source_b}")


def limit_proximity(close: pd.Series, upper: pd.Series, lower: pd.Series) -> pd.Series:
    """max(close/upper, lower/close). 1에 가까울수록 한쪽 제한가 근접."""
    upper_ratio = close / upper.where(upper != 0)
    lower_ratio = lower / close.where(close != 0)
    return pd.Series(
        np.maximum(upper_ratio.to_numpy(), lower_ratio.to_numpy()),
        index=close.index,
    )


def limit_side_label(
    close: pd.Series,
    upper: pd.Series,
    lower: pd.Series,
    threshold: float = 0.95,
) -> pd.Series:
    """근접 측면 레이블. dtype=object."""
    upper_ratio = close / upper.where(upper != 0)
    lower_ratio = lower / close.where(close != 0)
    result = pd.Series(["none"] * len(close), index=close.index, dtype=object)
    result[upper_ratio >= threshold] = "upper"
    result[lower_ratio >= threshold] = "lower"
    return result


def dispersion(source_data: Any, method: str = "stddev_over_mean") -> pd.Series:
    """다중 시계열 분산도. Stage 2-1A에서는 단일 시계열만 들어오므로 NaN 반환.

    향후 dict[str, Series] 또는 multi-column DataFrame이 들어오면
    method에 따라 row-wise 분산도를 계산한다.
    """
    if isinstance(source_data, pd.Series):
        return pd.Series([float("nan")] * len(source_data), index=source_data.index)
    if isinstance(source_data, dict):
        df = pd.DataFrame(source_data)
        if method == "stddev_over_mean":
            row_mean = df.mean(axis=1)
            return df.std(axis=1) / row_mean.where(row_mean != 0)
        raise ValueError(f"unsupported dispersion method: {method!r}")
    raise TypeError(
        f"dispersion expected Series or dict, got {type(source_data).__name__}"
    )


# === Dispatch ===

def compute_indicator(
    spec: dict,
    df: pd.DataFrame,
    computed: dict[str, pd.Series],
) -> pd.Series:
    """단일 인디케이터 spec을 평가하여 Series 반환.

    `computed`에 이미 계산된 인디케이터가 있으면 다른 인디케이터에서 참조 가능하다
    (예: cross의 fast/slow가 ma_20/ma_60을 참조).
    """
    indicator_type = spec.get("type")
    params = spec.get("params") or {}

    def _resolve(name: str) -> pd.Series:
        if name in computed:
            return computed[name]
        if name in df.columns:
            return df[name]
        raise KeyError(f"unknown source: {name!r}")

    if indicator_type == "rsi":
        return rsi(
            _resolve(params.get("source", "close")),
            int(params.get("window", 14)),
        )

    if indicator_type == "sma":
        if "window" not in params:
            raise ValueError("sma requires 'window' param")
        return sma(_resolve(params.get("source", "close")), int(params["window"]))

    if indicator_type == "stddev":
        if "window" not in params:
            raise ValueError("stddev requires 'window' param")
        return stddev(_resolve(params.get("source", "close")), int(params["window"]))

    if indicator_type == "ratio":
        return ratio(_resolve(params["numerator"]), _resolve(params["denominator"]))

    if indicator_type == "cross":
        return cross(_resolve(params["fast"]), _resolve(params["slow"]))

    if indicator_type == "bollinger_upper":
        return bb_upper(
            _resolve(params.get("source", "close")),
            int(params.get("window", 20)),
            float(params.get("num_std", 2.0)),
        )

    if indicator_type == "bollinger_lower":
        return bb_lower(
            _resolve(params.get("source", "close")),
            int(params.get("window", 20)),
            float(params.get("num_std", 2.0)),
        )

    if indicator_type == "bollinger_width":
        return bb_width(
            _resolve(params.get("source", "close")),
            int(params.get("window", 20)),
            float(params.get("num_std", 2.0)),
        )

    if indicator_type == "bollinger_width_ratio":
        return bb_width_ratio_fn(
            _resolve(params.get("source", "close")),
            int(params.get("window", 20)),
            float(params.get("num_std", 2.0)),
            int(params.get("ratio_window", 60)),
        )

    if indicator_type == "passthrough":
        return passthrough(_resolve(params.get("source", spec.get("name"))))

    if indicator_type == "abs":
        return abs_value(_resolve(params.get("source", spec.get("name"))))

    if indicator_type == "lag":
        return lag(_resolve(params["source"]), int(params.get("periods", 1)))

    if indicator_type == "zscore":
        src = _resolve(params["source"])
        mean_series = _resolve(params["mean"]) if "mean" in params else None
        std_series = _resolve(params["stddev"]) if "stddev" in params else None
        window = int(params["window"]) if "window" in params else None
        return zscore(src, mean=mean_series, std=std_series, window=window)

    if indicator_type == "linear":
        if "source" in params and "multiplier" in params:
            return linear(
                source=_resolve(params["source"]),
                multiplier=float(params["multiplier"]),
                intercept=float(params.get("intercept", 0)),
            )
        if "source_a" in params and "source_b" in params:
            return linear(
                source_a=_resolve(params["source_a"]),
                source_b=_resolve(params["source_b"]),
                coef_a=float(params.get("coef_a", 1.0)),
                coef_b=float(params.get("coef_b", 1.0)),
                intercept=float(params.get("intercept", 0)),
            )
        raise ValueError(
            "linear requires {source, multiplier} or {source_a, source_b, coef_a, coef_b}"
        )

    if indicator_type == "limit_proximity":
        return limit_proximity(
            _resolve(params["source"]),
            _resolve(params["upper_limit"]),
            _resolve(params["lower_limit"]),
        )

    if indicator_type == "limit_side_label":
        return limit_side_label(
            _resolve(params["source"]),
            _resolve(params["upper_limit"]),
            _resolve(params["lower_limit"]),
            float(params.get("threshold", 0.95)),
        )

    if indicator_type == "dispersion":
        source = params.get("source")
        try:
            src_data = _resolve(source)
        except KeyError:
            return pd.Series([float("nan")] * len(df), index=df.index)
        return dispersion(src_data, method=params.get("method", "stddev_over_mean"))

    raise NotImplementedError(f"indicator type not supported: {indicator_type!r}")


def compute_required_indicators(
    rule: dict, df: pd.DataFrame
) -> dict[str, pd.Series]:
    """룰의 required_indicators를 선언 순서대로 계산.

    이전에 계산된 인디케이터를 후속 인디케이터가 참조할 수 있다 (예: bb_width의
    sma → bb_width_ma_20 → ratio(bb_width, bb_width_ma_20) 체인).
    """
    computed: dict[str, pd.Series] = {}
    for spec in rule.get("required_indicators") or []:
        name = spec.get("name")
        if not name:
            continue
        computed[name] = compute_indicator(spec, df, computed)
    return computed
