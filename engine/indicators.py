# -*- coding: utf-8 -*-
"""
Module d'indicateurs techniques et statistiques de marché :
- Momentum composite (Tendance SMA20, variation 5 jours, Breakout, Volume Spike)
- Volatilité historique (20 jours et annualisée)
- RSI (Relative Strength Index 14 jours)
- Moyennes mobiles (SMA 20, SMA 50)
"""

import pandas as pd
import numpy as np


def compute_rsi(series: pd.Series, period: int = 14) -> float:
    """Calcule le RSI (Relative Strength Index) sur une période donnée."""
    if len(series) < period + 1:
        return 50.0

    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    last_loss = loss.iloc[-1]
    if last_loss == 0 or np.isnan(last_loss):
        return 100.0 if (gain.iloc[-1] > 0) else 50.0

    rs = gain.iloc[-1] / last_loss
    rsi = 100 - (100 / (1 + rs))
    return float(np.clip(rsi, 0.0, 100.0))


def compute_momentum(df: pd.DataFrame) -> float:
    """
    Calcule le score de momentum composite selon la formule Alpha Scanner :
    momentum = trend*0.3 + momentum_5d*5 + breakout*0.3 + (volume_spike - 1)*0.2
    """
    if df is None or len(df) < 20:
        return 0.0

    close = df["Close"]
    volume = df["Volume"]

    # 1. Tendance SMA20
    sma_20 = close.rolling(20).mean().iloc[-1]
    current_close = close.iloc[-1]
    trend = 1.0 if current_close > sma_20 else -1.0

    # 2. Momentum court terme 5 jours
    p_5d = close.iloc[-5] if len(close) >= 5 else close.iloc[0]
    momentum_5d = (current_close / p_5d) - 1.0 if p_5d > 0 else 0.0

    # 3. Breakout 20 jours
    max_20 = close.iloc[-21:-1].max() if len(close) >= 21 else close.iloc[:-1].max()
    breakout = 1.0 if current_close > max_20 else 0.0

    # 4. Volume Spike
    avg_vol = volume.rolling(20).mean().iloc[-1]
    curr_vol = volume.iloc[-1]
    vol_spike = (curr_vol / avg_vol) if avg_vol > 0 else 1.0

    # Score final pondéré
    score = (
        trend * 0.3 +
        momentum_5d * 5.0 +
        breakout * 0.3 +
        (vol_spike - 1.0) * 0.2
    )

    return float(round(score, 3))


def compute_indicators(df: pd.DataFrame) -> dict:
    """
    Calcule l'ensemble complet des métriques techniques et statistiques pour un DataFrame de prix.
    """
    if df is None or df.empty or len(df) < 5:
        return {
            "current_price": 0.0,
            "change_1d": 0.0,
            "change_5d": 0.0,
            "momentum": 0.0,
            "volatility_20d": 0.0,
            "volatility_annualized": 0.0,
            "rsi_14": 50.0,
            "sma_20": 0.0,
            "sma_50": 0.0,
        }

    close = df["Close"]
    current_price = float(close.iloc[-1])

    # Variation 1j
    prev_close = float(close.iloc[-2]) if len(close) >= 2 else current_price
    change_1d = ((current_price / prev_close) - 1.0) * 100.0 if prev_close > 0 else 0.0

    # Variation 5j
    close_5d = float(close.iloc[-5]) if len(close) >= 5 else float(close.iloc[0])
    change_5d = ((current_price / close_5d) - 1.0) * 100.0 if close_5d > 0 else 0.0

    # Moyennes mobiles
    sma_20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else current_price
    sma_50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else sma_20

    # Volatilité
    daily_returns = close.pct_change().dropna()
    if len(daily_returns) >= 10:
        vol_window = daily_returns.tail(20)
        daily_vol = float(vol_window.std())
        vol_annualized = float(daily_vol * np.sqrt(252) * 100.0)
    else:
        daily_vol = 0.0
        vol_annualized = 0.0

    # RSI
    rsi_14 = compute_rsi(close, period=14)

    # Momentum
    momentum = compute_momentum(df)

    return {
        "current_price": round(current_price, 2),
        "change_1d": round(change_1d, 2),
        "change_5d": round(change_5d, 2),
        "momentum": momentum,
        "volatility_20d": round(daily_vol * 100, 2),
        "volatility_annualized": round(vol_annualized, 1),
        "rsi_14": round(rsi_14, 1),
        "sma_20": round(sma_20, 2),
        "sma_50": round(sma_50, 2),
    }