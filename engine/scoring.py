# -*- coding: utf-8 -*-
"""
Calculateur du Score Alpha global et générateur de signaux de trading.
Combine les trois piliers du Projet Alpha :
1. Fondamentaux (Scoring ALPHA 0-100)
2. Momentum technique (Prix, SMA20, Breakout, Volume)
3. Sentiment des marchés (Actualités financières)
"""

from typing import Dict, Any


def determine_signal(alpha_score: float, fund_score: float = None, momentum: float = None) -> str:
    """
    Détermine le signal d'action recommandé.
    Exige une convergence entre fondamentaux et dynamique de marché pour les signaux forts.
    """
    if alpha_score >= 1.5:
        if fund_score is not None and fund_score >= 65:
            return "STRONG BUY"
        return "BUY"
    elif alpha_score >= 0.4:
        return "BUY"
    elif alpha_score <= -1.5:
        if fund_score is not None and fund_score < 40:
            return "STRONG SELL"
        return "SELL"
    elif alpha_score <= -0.4:
        return "SELL"
    else:
        return "HOLD"


def calculate_alpha_score(momentum: float, sentiment: float, fundamental_score: float = None) -> float:
    """
    Calcule le score Alpha composite.
    Si le score fondamental est disponible :
        - Fondamentaux : 40% (centré sur 0 : (fund - 50) / 25)
        - Momentum : 40%
        - Sentiment : 20%
    Sinon (fallback V3) :
        - Momentum : 70%
        - Sentiment : 30%
    """
    if fundamental_score is not None:
        fund_normalized = (fundamental_score - 50.0) / 25.0
        score = (momentum * 0.40) + (fund_normalized * 0.40) + (sentiment * 0.20)
    else:
        score = (momentum * 0.70) + (sentiment * 0.30)

    return round(float(score), 2)


def compute_composite_alpha(
    ticker: str,
    momentum: float,
    sentiment: float,
    fundamental_data: Dict[str, Any] = None,
    technical_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Génère la fiche de scoring complète pour un ticker.
    """
    fund_score = fundamental_data.get("fundamental_score") if fundamental_data else None
    alpha = calculate_alpha_score(momentum, sentiment, fund_score)
    signal = determine_signal(alpha, fund_score, momentum)

    return {
        "ticker": ticker,
        "alpha_score": alpha,
        "signal": signal,
        "momentum": round(momentum, 2),
        "sentiment": round(sentiment, 2),
        "fundamental_score": round(fund_score, 1) if fund_score is not None else None,
        "completeness_rate": fundamental_data.get("completeness_rate") if fundamental_data else 0.0,
        "sub_scores": fundamental_data.get("sub_scores", {}) if fundamental_data else {},
        "raw_metrics": fundamental_data.get("raw_metrics", {}) if fundamental_data else {},
        "technical": technical_data or {},
    }