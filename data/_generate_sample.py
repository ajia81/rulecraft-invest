"""data/sample_btc.csv 생성기.

목적: 다음 3개 룰이 마지막 일봉에서 모두 매칭되도록 의도된 BTC-like 일봉 시계열을 만든다.

- momentum_overheating (crypto override): rsi_14 > 80, close > ma_20, volume_ratio > 1.2
- volatility_expansion (base): bb_width / bb_width_ma_20 > 1.3
- funding_rate_abnormal (crypto-only): abs(funding_rate) > 0.03

설계:
- 120 거래일
- 처음 105일: 약한 양의 드리프트가 있는 랜덤 워크
- 마지막 15일: 모두 양의 일일 수익률 + 거래량 1.5~2x 스파이크
- funding_rate: 평소 ±0.012 노이즈, 마지막 5일 순차적 상승하여 -1일 ≈ 0.042
- 시드 고정으로 재현 가능

사용:
    python data/_generate_sample.py
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 42
N_DAYS = 120
END_DATE = datetime(2024, 12, 31)
START_PRICE = 30_000.0
BASE_VOLUME = 1_000_000


def generate() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    dates = [
        (END_DATE - timedelta(days=N_DAYS - 1 - i)).strftime("%Y-%m-%d")
        for i in range(N_DAYS)
    ]

    returns = np.zeros(N_DAYS)
    returns[:105] = rng.normal(0.0008, 0.022, 105)
    returns[105:] = np.abs(rng.normal(0.024, 0.010, 15))  # 마지막 15일 모두 양

    closes = START_PRICE * np.exp(np.cumsum(returns))

    opens = np.empty(N_DAYS)
    opens[0] = START_PRICE
    opens[1:] = closes[:-1]

    high_noise = np.abs(rng.normal(0.003, 0.004, N_DAYS))
    low_noise = np.abs(rng.normal(0.003, 0.004, N_DAYS))
    highs = np.maximum(opens, closes) * (1 + high_noise)
    lows = np.minimum(opens, closes) * (1 - low_noise)

    vol_normal = BASE_VOLUME * np.maximum(0.55, 1.0 + 0.25 * rng.standard_normal(105))
    vol_spike = BASE_VOLUME * np.maximum(1.4, 1.7 + 0.25 * rng.standard_normal(15))
    volumes = np.concatenate([vol_normal, vol_spike]).astype(int)

    # funding_rate: 평소 작은 변동, 마지막 5일은 가격 모멘텀과 동행하여 단계적 상승.
    # 별도 RNG 스트림으로 가격/거래량과 독립.
    rng_funding = np.random.default_rng(SEED + 1)
    funding_rate = rng_funding.normal(0.000, 0.010, N_DAYS)
    funding_rate[-5:] = np.array([0.018, 0.025, 0.030, 0.038, 0.042])
    funding_rate = np.clip(funding_rate, -0.05, 0.05).round(4)

    return pd.DataFrame(
        {
            "date": dates,
            "open": opens.round(2),
            "high": highs.round(2),
            "low": lows.round(2),
            "close": closes.round(2),
            "volume": volumes,
            "funding_rate": funding_rate,
        }
    )


def _verify(df: pd.DataFrame) -> dict:
    """매칭 조건이 마지막 행에서 충족되는지 확인.

    검증 대상 (Stage 2-1A 기준):
    - momentum_overheating (crypto override): rsi_14 > 80, close > ma_20, volume_ratio > 1.2
    - volatility_expansion (base): bb_width / bb_width_ma_20 > 1.3
    """
    close = df["close"]

    # momentum_overheating
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    loss = (-delta).clip(lower=0).rolling(14, min_periods=14).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = gain / loss
        rsi_14 = 100 - 100 / (1 + rs)
    ma_20 = close.rolling(20, min_periods=20).mean()
    vol_ma_20 = df["volume"].rolling(20, min_periods=20).mean()
    vol_ratio = df["volume"] / vol_ma_20

    # volatility_expansion (bb_width = upper - lower with window=20, num_std=2)
    sma_20 = close.rolling(20, min_periods=20).mean()
    std_20 = close.rolling(20, min_periods=20).std()
    bb_width = (sma_20 + 2 * std_20) - (sma_20 - 2 * std_20)
    bb_width_ma_20 = bb_width.rolling(20, min_periods=20).mean()
    bb_width_ratio = bb_width / bb_width_ma_20

    funding_last = float(df["funding_rate"].iloc[-1]) if "funding_rate" in df.columns else float("nan")

    return {
        "rsi_14": float(rsi_14.iloc[-1]),
        "close": float(close.iloc[-1]),
        "ma_20": float(ma_20.iloc[-1]),
        "volume_ratio": float(vol_ratio.iloc[-1]),
        "bb_width": float(bb_width.iloc[-1]),
        "bb_width_ma_20": float(bb_width_ma_20.iloc[-1]),
        "bb_width_ratio": float(bb_width_ratio.iloc[-1]),
        "funding_rate_last": funding_last,
        "abs_funding_rate_last": abs(funding_last),
        "matches_overheating_crypto": bool(
            rsi_14.iloc[-1] > 80
            and close.iloc[-1] > ma_20.iloc[-1]
            and vol_ratio.iloc[-1] > 1.2
        ),
        "matches_volatility_expansion": bool(bb_width_ratio.iloc[-1] > 1.3),
        "matches_funding_rate_abnormal": bool(abs(funding_last) > 0.03),
    }


if __name__ == "__main__":
    df = generate()
    out = Path(__file__).parent / "sample_btc.csv"
    df.to_csv(out, index=False)
    diag = _verify(df)
    print(f"Generated {len(df)} rows -> {out}")
    print("Last row:", df.iloc[-1].to_dict())
    print("Verification:")
    for k, v in diag.items():
        print(f"  {k}: {v}")
    print("Last 5 funding_rate:", df["funding_rate"].tail(5).to_list())
    assert diag["matches_overheating_crypto"], "momentum_overheating must match"
    assert diag["matches_volatility_expansion"], "volatility_expansion must match"
    assert diag["matches_funding_rate_abnormal"], "funding_rate_abnormal must match"
    print("All required matches OK.")
