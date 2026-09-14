# -*- coding: utf-8 -*-
"""
Moteur d'analyse du sentiment des actualités financières.
Évalue le ton des titres et résumés avec un dictionnaire spécialisé marché financier.
"""

from typing import List, Dict, Tuple

POSITIVE_WORDS = {
    "growth": 1.0, "upgrade": 1.5, "record": 1.2, "beat": 1.5, "strong": 1.0,
    "ai": 0.8, "surge": 1.3, "breakout": 1.2, "profit": 1.0, "soar": 1.3,
    "bullish": 1.5, "outperform": 1.5, "dividend": 0.8, "expansion": 1.0,
    "partnership": 1.0, "success": 1.0, "rally": 1.2, "gain": 1.0,
    "jump": 1.0, "positive": 1.0, "accelerate": 1.2, "lead": 0.8
}

NEGATIVE_WORDS = {
    "risk": 1.0, "loss": 1.2, "drop": 1.2, "downgrade": 1.5, "lawsuit": 1.5,
    "decline": 1.0, "slump": 1.3, "warning": 1.5, "investigation": 1.5,
    "probe": 1.5, "penalty": 1.2, "debt": 1.0, "bearish": 1.5,
    "underperform": 1.5, "scandal": 1.8, "cut": 1.0, "fall": 1.0,
    "crash": 1.8, "plunge": 1.5, "fraud": 2.0, "subpoena": 1.5, "weak": 1.0
}


def analyze_article_sentiment(article: Dict) -> Tuple[float, str]:
    """Analyse un article individuel et renvoie (score, label)."""
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()

    pos_score = sum(weight for word, weight in POSITIVE_WORDS.items() if word in text)
    neg_score = sum(weight for word, weight in NEGATIVE_WORDS.items() if word in text)

    diff = pos_score - neg_score
    if diff > 0.5:
        label = "Positif"
    elif diff < -0.5:
        label = "Négatif"
    else:
        label = "Neutre"

    return round(diff, 2), label


def news_sentiment(news: List[Dict]) -> float:
    """
    Calcule le sentiment global agrégé d'une liste d'articles.
    Renvoie une valeur centrée autour de 0 (ex. entre -3 et +3).
    """
    if not news:
        return 0.0

    total_score = 0.0
    for art in news:
        score, label = analyze_article_sentiment(art)
        art["sentiment_score"] = score
        art["sentiment_label"] = label
        total_score += score

    # Moyenne pondérée ou somme modérée
    avg_score = total_score / len(news)
    return round(avg_score, 2)