"""data/sample_kospi.csv 생성기.

목적: 한국 주식 자산군 시연용 데이터. 다음 룰이 마지막 일봉에서 매칭/미매칭되도록 의도된 구조로 만든다.

매칭 보장:
- foreign_net_buying_surge (asset_only): 외국인 순매수 z-score > 2.0
- volatility_expansion (base inherit via stock_kr): bb_width / bb_width_ma_20 > 1.3

명시적 미매칭:
- momentum_overheating (extend, base + extend의 AND 결합):
    base 조건은 충족 가능하더라도 extend 조건 foreign_net_buy_ma_5 < 0이
    충족되지 않으므로(최근 외국인 순매수 우위) 전체 룰은 매칭되지 않는다.

설계:
- 영업일 기준 120일 (pd.bdate_range, end=2024-12-30)
- 가격: 시작 50,000원 근처에서 약한 양의 드리프트 → 마지막 15일 변동성 확대
- 거래량: 평소 100K~1.5M, 마지막 7일 2M~5M로 스파이크
- 외국인 순매수: 평소 ±5K 노이즈, 마지막 5일 단계적 상승
- SEED=42 고정 (foreign_net_buy는 SEED+2로 분리 스트림)

사용:
    python data/_generate_kospi_sample.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


SEED = 42
N_DAYS = 120
END_DATE = pd.Timestamp("2024-12-30")
START_PRICE = 50_000.0


def generate() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)

    dates = pd.bdate_range(end=END_DATE, periods=N_DAYS).strftime("%Y-%m-%d").tolist()

    # 가격 수익률: 처음 105일 매우 낮은 변동성, 마지막 15일 변동성 급격히 확대.
    # bb_width(20)이 직전 20일 평균 대비 1.3배를 넘어야 하므로 전환을 sharp하게.
    returns = np.zeros(N_DAYS)
    returns[:105] = rng.normal(0.0002, 0.008, 105)
    returns[105:] = rng.normal(0.0, 0.030, 15)
    closes = START_PRICE * np.exp(np.cumsum(returns))

    opens = np.empty(N_DAYS)
    opens[0] = START_PRICE
    opens[1:] = closes[:-1]

    high_noise = np.abs(rng.normal(0.002, 0.003, N_DAYS))
    low_noise = np.abs(rng.normal(0.002, 0.003, N_DAYS))
    highs = np.maximum(opens, closes) * (1 + high_noise)
    lows = np.minimum(opens, closes) * (1 - low_noise)

    # 거래량: 평소 100K~1.5M, 마지막 7일 2M~5M
    volumes = rng.integers(100_000, 1_500_000, N_DAYS)
    volumes[-7:] = rng.integers(2_000_000, 5_000_000, 7)

    # 외국인 순매수: 평소 ±5K 노이즈, 마지막 5일 단계적 상승
    rng_foreign = np.random.default_rng(SEED + 2)
    foreign_net_buy = rng_foreign.normal(0, 5_000, N_DAYS).round(0).astype(int)
    foreign_net_buy[-5:] = np.array([60_000, 90_000, 130_000, 200_000, 280_000])

    return pd.DataFrame(
        {
            "date": dates,
            "open": opens.round(0).astype(int),
            "high": highs.round(0).astype(int),
            "low": lows.round(0).astype(int),
            "close": closes.round(0).astype(int),
            "volume": volumes.astype(int),
            "foreign_net_buy": foreign_net_buy,
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
    bb_width = 4 * std_20  # (sma + 2*std) - (sma - 2*std)
    bb_width_ma_20 = bb_width.rolling(20, min_periods=20).mean()
    bb_width_ratio = bb_width / bb_width_ma_20

    fnb = df["foreign_net_buy"].astype(float)
    fnb_ma_5 = fnb.rolling(5, min_periods=5).mean()
    fnb_ma_20 = fnb.rolling(20, min_periods=20).mean()
    fnb_std_20 = fnb.rolling(20, min_periods=20).std()
    fnb_zscore = (fnb - fnb_ma_20) / fnb_std_20

    rsi_last = float(rsi_14.iloc[-1])
    close_last = float(close.iloc[-1])
    ma_20_last = float(ma_20.iloc[-1])
    vol_ratio_last = float(vol_ratio.iloc[-1])
    bb_width_ratio_last = float(bb_width_ratio.iloc[-1])
    fnb_ma_5_last = float(fnb_ma_5.iloc[-1])
    fnb_zscore_last = float(fnb_zscore.iloc[-1])

    overheat_base = (
        rsi_last > 70 and close_last > ma_20_last and vol_ratio_last > 1.2
    )
    overheat_extend = fnb_ma_5_last < 0
    matches_overheating = bool(overheat_base and overheat_extend)

    return {
        "rsi_14": rsi_last,
        "close": close_last,
        "ma_20": ma_20_last,
        "volume_ratio": vol_ratio_last,
        "bb_width": float(bb_width.iloc[-1]),
        "bb_width_ma_20": float(bb_width_ma_20.iloc[-1]),
        "bb_width_ratio": bb_width_ratio_last,
        "foreign_net_buy_last": int(fnb.iloc[-1]),
        "foreign_net_buy_ma_5": fnb_ma_5_last,
        "foreign_net_buy_zscore": fnb_zscore_last,
        "matches_foreign_net_buying_surge": bool(fnb_zscore_last > 2.0),
        "matches_volatility_expansion_kr": bool(bb_width_ratio_last > 1.3),
        "matches_momentum_overheating_kr": matches_overheating,
    }


if __name__ == "__main__":
    df = generate()
    out = Path(__file__).parent / "sample_kospi.csv"
    df.to_csv(out, index=False)
    diag = _verify(df)
    print(f"Generated {len(df)} rows -> {out}")
    print("Last row:", df.iloc[-1].to_dict())
    print("Verification:")
    for k, v in diag.items():
        print(f"  {k}: {v}")
    print("Last 5 foreign_net_buy:", df["foreign_net_buy"].tail(5).to_list())

    assert diag["matches_foreign_net_buying_surge"], "foreign_net_buying_surge must match"
    assert diag["matches_volatility_expansion_kr"], "volatility_expansion (kr) must match"
    assert not diag["matches_momentum_overheating_kr"], "momentum_overheating must NOT match"
    print("All required matches OK.")
