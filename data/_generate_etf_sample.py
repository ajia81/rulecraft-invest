"""data/sample_etf.csv 생성기.

목적: ETF 자산군 시연용 데이터 (DemoETF, S&P 500-like). 다음 룰이 마지막 일봉에서
매칭/미매칭되도록 의도된 구조로 만든다.

매칭 보장:
- nav_premium_anomaly (asset_only): abs((close - nav) / nav) > 0.005
- volatility_expansion (base inherit via etf_us): bb_width / bb_width_ma_20 > 1.3

명시적 미매칭:
- momentum_overheating (extend): base 조건 (rsi_14 > 70)에서 자연 차단.
    가격 변동을 last-20일 양/음 균형으로 두어 RSI를 50~60에서 유지.
    추적 오차도 평소 노이즈만 → extend 조건도 함께 미매칭.

설계:
- 영업일 기준 120일 (pd.bdate_range, end=2024-12-30)
- 가격: 시작 450 (S&P 500 ETF 모방), 처음 100일 std=0.005, 마지막 20일 std=0.015 (방향성 X)
- nav: 평소 close ± 0.001 (정상 범위), 마지막 5일 close 대비 단계적으로 낮아져 +0.5% 초과
- volume: 1M ~ 5M 범위
- tracking_error: 평소 ±0.001 노이즈 유지 (extend 조건 비매칭 보장)
- SEED=45 (42 + 3) 고정

사용:
    python data/_generate_etf_sample.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


SEED = 45
N_DAYS = 120
END_DATE = pd.Timestamp("2024-12-30")
START_PRICE = 450.0


def generate() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)

    dates = pd.bdate_range(end=END_DATE, periods=N_DAYS).strftime("%Y-%m-%d").tolist()

    # 가격 수익률: 처음 110일 매우 안정(std=0.004), 마지막 10일 변동성 sharp 확대(std=0.025).
    # mean=0으로 두어 마지막 일자 RSI가 50-60대에 머물도록 (momentum_overheating 미매칭).
    # bb_width(20)이 직전 20일 평균 대비 1.3배 초과하도록 전환을 sharp하게.
    returns = np.zeros(N_DAYS)
    returns[:110] = rng.normal(0.0002, 0.004, 110)
    returns[110:] = rng.normal(0.0, 0.025, 10)
    closes = START_PRICE * np.exp(np.cumsum(returns))

    opens = np.empty(N_DAYS)
    opens[0] = START_PRICE
    opens[1:] = closes[:-1]

    high_noise = np.abs(rng.normal(0.001, 0.002, N_DAYS))
    low_noise = np.abs(rng.normal(0.001, 0.002, N_DAYS))
    highs = np.maximum(opens, closes) * (1 + high_noise)
    lows = np.minimum(opens, closes) * (1 - low_noise)

    # 거래량: 1M ~ 5M 범위, 균일 분포
    volumes = rng.integers(1_000_000, 5_000_000, N_DAYS)

    # NAV: 평소 close ± 0.001 (정상 범위)
    nav_noise = rng.normal(0, 0.001, N_DAYS)
    nav = closes * (1 + nav_noise)
    # 마지막 5일: nav가 close보다 낮아져 premium > +0.5% 형성
    # close/nav - 1 = -nav_factor + 1 → nav_factor 작을수록 premium 큼
    nav_factors = np.array([0.998, 0.996, 0.994, 0.992, 0.991])
    nav[-5:] = closes[-5:] * nav_factors

    # 추적 오차: 평소 ±0.001 노이즈 (extend 조건 미매칭 보장)
    tracking_error = rng.normal(0, 0.001, N_DAYS)

    return pd.DataFrame(
        {
            "date": dates,
            "open": opens.round(2),
            "high": highs.round(2),
            "low": lows.round(2),
            "close": closes.round(2),
            "volume": volumes.astype(int),
            "nav": nav.round(2),
            "tracking_error": tracking_error.round(5),
        }
    )


def _verify(df: pd.DataFrame) -> dict:
    close = df["close"].astype(float)

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    loss = (-delta).clip(lower=0).rolling(14, min_periods=14).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = gain / loss
        rsi_14 = 100 - 100 / (1 + rs)

    ma_20 = close.rolling(20, min_periods=20).mean()
    vol_ma_20 = df["volume"].rolling(20, min_periods=20).mean()
    vol_ratio = df["volume"] / vol_ma_20

    sma_20 = close.rolling(20, min_periods=20).mean()
    std_20 = close.rolling(20, min_periods=20).std()
    bb_width = 4 * std_20
    bb_width_ma_20 = bb_width.rolling(20, min_periods=20).mean()
    bb_width_ratio = bb_width / bb_width_ma_20

    nav = df["nav"].astype(float)
    nav_premium = (close - nav) / nav
    abs_nav_premium = nav_premium.abs()

    te = df["tracking_error"].astype(float)
    te_ma_20 = te.rolling(20, min_periods=20).mean()
    te_std_20 = te.rolling(20, min_periods=20).std()
    with np.errstate(divide="ignore", invalid="ignore"):
        te_zscore = (te - te_ma_20) / te_std_20

    rsi_last = float(rsi_14.iloc[-1])
    close_last = float(close.iloc[-1])
    ma_20_last = float(ma_20.iloc[-1])
    vol_ratio_last = float(vol_ratio.iloc[-1])
    bb_width_ratio_last = float(bb_width_ratio.iloc[-1])
    nav_last = float(nav.iloc[-1])
    nav_premium_last = float(nav_premium.iloc[-1])
    abs_nav_premium_last = float(abs_nav_premium.iloc[-1])
    te_zscore_last = float(te_zscore.iloc[-1])

    overheat_base = (
        rsi_last > 70 and close_last > ma_20_last and vol_ratio_last > 1.2
    )
    overheat_extend = te_zscore_last > 1.5
    matches_overheating_etf = bool(overheat_base and overheat_extend)

    return {
        "rsi_14": rsi_last,
        "close": close_last,
        "ma_20": ma_20_last,
        "volume_ratio": vol_ratio_last,
        "bb_width": float(bb_width.iloc[-1]),
        "bb_width_ma_20": float(bb_width_ma_20.iloc[-1]),
        "bb_width_ratio": bb_width_ratio_last,
        "nav_last": nav_last,
        "nav_premium_last": nav_premium_last,
        "abs_nav_premium_last": abs_nav_premium_last,
        "tracking_error_zscore_last": te_zscore_last,
        "matches_volatility_expansion_etf": bool(bb_width_ratio_last > 1.3),
        "matches_nav_premium_anomaly": bool(abs_nav_premium_last > 0.005),
        "matches_momentum_overheating_etf": matches_overheating_etf,
    }


if __name__ == "__main__":
    df = generate()
    out = Path(__file__).parent / "sample_etf.csv"
    df.to_csv(out, index=False)
    diag = _verify(df)
    print(f"Generated {len(df)} rows -> {out}")
    print("Last row:", df.iloc[-1].to_dict())
    print("Verification:")
    for k, v in diag.items():
        print(f"  {k}: {v}")
    print("Last 5 (close, nav, premium):")
    for i in range(-5, 0):
        c = float(df["close"].iloc[i])
        n = float(df["nav"].iloc[i])
        p = (c - n) / n
        print(f"  day {i}: close={c:.2f}, nav={n:.2f}, premium={p:+.4f}")

    assert diag["matches_nav_premium_anomaly"], "nav_premium_anomaly must match"
    assert diag["matches_volatility_expansion_etf"], "volatility_expansion (etf) must match"
    assert not diag["matches_momentum_overheating_etf"], "momentum_overheating must NOT match"
    print("All required matches OK.")
