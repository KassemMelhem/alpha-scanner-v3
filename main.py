# -*- coding: utf-8 -*-
"""
Alpha Scanner V3 / V4 - Pipeline d'analyse financière et de scoring quantitatif.
Orchestre l'analyse des fondamentaux (scoring ALPHA), de la dynamique technique et du sentiment des actualités.
"""

import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import pandas as pd

from config import WATCHLIST, DATABASE_PATH
from providers.news_provider import get_news
from providers.market_provider import (
    get_single_price_data,
    get_raw_fundamental_data,
    load_from_cache
)
from engine.sentiment import news_sentiment
from engine.indicators import compute_indicators
from engine.fundamental_scoring import calculate_fundamental_score
from engine.scoring import compute_composite_alpha
from database.storage import save_results


def run_scanner(watchlist=None, save_db=True):
    tickers = watchlist or WATCHLIST
    results = []

    print("=" * 70)
    print("🚀 LANCEMENT ALPHA SCANNER V3 / V4")
    print(f"📊 Univers d'analyse : {len(tickers)} actions (US & Europe)")
    print("=" * 70)

    for i, ticker in enumerate(tickers, start=1):
        print(f"\n[{i}/{len(tickers)}] 🔍 Analyse {ticker}...")

        # 1. PRIX & INDICATEURS TECHNIQUES
        df_price = get_single_price_data(ticker)
        if df_price is None or df_price.empty:
            df_price = load_from_cache(ticker)

        if df_price is None or df_price.empty or len(df_price) < 5:
            print(f"   ❌ Données de prix indisponibles pour {ticker}, passage au suivant.")
            continue

        tech_metrics = compute_indicators(df_price)
        current_price = tech_metrics.get("current_price", 0.0)
        momentum = tech_metrics.get("momentum", 0.0)
        vol_ann = tech_metrics.get("volatility_annualized", 0.0)

        # 2. ACTUALITÉS & SENTIMENT (Gratuit, illimité)
        try:
            news_items = get_news(ticker, limit=10)
            sentiment_score = news_sentiment(news_items)
        except Exception as e:
            print(f"   ⚠️ Actualités {ticker} : {e}")
            sentiment_score = 0.0
            news_items = []

        # 3. ANALYSE FONDAMENTALE (Conforme au document Word scoring ALPHA)
        try:
            raw_fund = get_raw_fundamental_data(ticker)
            fund_results = calculate_fundamental_score(raw_fund)
            fund_score = fund_results.get("fundamental_score", 50.0)
            completeness = fund_results.get("completeness_rate", 0.0)
            short_name = raw_fund.get("short_name", ticker)
        except Exception as e:
            print(f"   ⚠️ Fondamentaux {ticker} : {e}")
            fund_results = {}
            fund_score = 50.0
            completeness = 0.0
            short_name = ticker

        # 4. SCORING COMPOSITE ALPHA & SIGNAL
        alpha_entry = compute_composite_alpha(
            ticker=ticker,
            momentum=momentum,
            sentiment=sentiment_score,
            fundamental_data=fund_results,
            technical_data=tech_metrics
        )

        signal = alpha_entry["signal"]
        alpha_score = alpha_entry["alpha_score"]

        # 5. STOCKAGE RÉSULTATS
        results.append({
            "ticker": ticker,
            "nom": short_name,
            "prix": current_price,
            "variation_5j_%": tech_metrics.get("change_5d", 0.0),
            "volatilite_ann_%": vol_ann,
            "score_fondamental": fund_score,
            "momentum": momentum,
            "sentiment": sentiment_score,
            "alpha_score": alpha_score,
            "signal": signal,
            "completude_%": completeness,
            "rsi_14": tech_metrics.get("rsi_14", 50.0),
            "nb_news": len(news_items),
        })

        # Affichage synthétique console
        signal_icon = "🟢" if "BUY" in signal else ("🔴" if "SELL" in signal else "🟡")
        print(f"   -> Prix: {current_price} | Fund: {fund_score}/100 | Mom: {momentum} | Sent: {sentiment_score}")
        print(f"   -> Alpha Score: {alpha_score} | Signal: {signal_icon} {signal}")

    if not results:
        print("\n❌ Aucun résultat généré.")
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df = df.sort_values(by="alpha_score", ascending=False).reset_index(drop=True)

    # =========================
    # AFFICHAGE TOP 10
    # =========================
    print("\n" + "=" * 85)
    print("🏆 TOP 10 ALPHA SCANNER - CLASSEMENT & SIGNAUX RECOMMANDÉS")
    print("=" * 85)

    display_cols = ["ticker", "nom", "prix", "signal", "alpha_score", "score_fondamental", "momentum", "sentiment", "volatilite_ann_%"]
    print(df[display_cols].head(10).to_string(index=True))
    print("=" * 85)

    # =========================
    # SAUVEGARDE
    # =========================
    csv_file = "alpha_results.csv"
    df.to_csv(csv_file, index=False)
    print(f"\n💾 Résultats sauvegardés dans {csv_file}")

    if save_db:
        try:
            save_results(df)
            print(f"💾 Historique enregistré dans la base SQLite ({DATABASE_PATH})")
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde SQLite : {e}")

    return df


def main():
    run_scanner()


if __name__ == "__main__":
    main()