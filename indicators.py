import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volume import VolumeWeightedAveragePrice
from ta.volatility import AverageTrueRange


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds technical indicators to OHLCV dataframe.
    Requires columns: Open, High, Low, Close, Volume
    """

    df = df.copy()

    close = df["Close"].squeeze()
    high = df["High"].squeeze()
    low = df["Low"].squeeze()
    volume = df["Volume"].squeeze()

    # EMA (Trend)
    df["EMA_20"] = EMAIndicator(
        close=close,
        window=20
    ).ema_indicator()

    # RSI (Momentum)
    df["RSI_14"] = RSIIndicator(
        close=close,
        window=14
    ).rsi()

    # VWAP (Institutional fair price)
    vwap = VolumeWeightedAveragePrice(
        high=high,
        low=low,
        close=close,
        volume=volume
    )
    df["VWAP"] = vwap.volume_weighted_average_price()

    # ATR (Risk / volatility)
    atr = AverageTrueRange(
        high=high,
        low=low,
        close=close,
        window=14
    )
    df["ATR"] = atr.average_true_range()

    return df
