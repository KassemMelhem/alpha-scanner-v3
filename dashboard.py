# -*- coding: utf-8 -*-
"""
Alpha Scanner Pro - Studio Financier & Diagnostic d'Investissement
Interface style Visual Studio / Bloomberg Terminal développée avec Streamlit et Plotly.
Propose une analyse multi-actifs complète avec onglets de navigation, graphiques chandeliers interactifs,
diagrammes radar de scoring fondamental, filtres dynamiques et diagnostic des axes d'amélioration.
"""

import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import datetime
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import DEFAULT_WATCHLIST, ALPHA_WEIGHTS, FUNDAMENTAL_WEIGHTS
from providers.news_provider import get_news
from providers.market_provider import (
    get_single_price_data,
    get_raw_fundamental_data,
    load_from_cache
)
from engine.sentiment import news_sentiment
from engine.indicators import compute_indicators
from engine.fundamental_scoring import calculate_fundamental_score
from engine.scoring import calculate_alpha_score, determine_signal

# ==============================================================================
# CONFIGURATION GLOBALE STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="Alpha Scanner Studio | Terminal Quantitatif",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# STYLES CSS INSPIRÉS DE VISUAL STUDIO / TERMINAL FINANCIER
# ==============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    code, pre {
        font-family: 'JetBrains Mono', monospace;
    }
    
    /* Barre supérieure style IDE */
    .ide-header {
        background: #181c24;
        border-bottom: 2px solid #282e3a;
        padding: 12px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* Cartes de statistiques */
    .studio-card {
        background: linear-gradient(135deg, #1a202c 0%, #151922 100%);
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 16px 18px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .studio-title {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94a3b8;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .studio-value {
        font-size: 1.65rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .studio-desc {
        font-size: 0.78rem;
        color: #64748b;
        margin-top: 2px;
    }
    
    /* Badges de signaux */
    .signal-strong-buy {
        background: #059669;
        color: #ffffff;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        letter-spacing: 0.04em;
        display: inline-block;
    }
    .signal-buy {
        background: rgba(16, 185, 129, 0.18);
        color: #34d399;
        border: 1px solid #10b981;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        display: inline-block;
    }
    .signal-hold {
        background: rgba(245, 158, 11, 0.18);
        color: #fbbf24;
        border: 1px solid #f59e0b;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        display: inline-block;
    }
    .signal-sell {
        background: rgba(239, 68, 68, 0.18);
        color: #f87171;
        border: 1px solid #ef4444;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        display: inline-block;
    }
    .signal-strong-sell {
        background: #dc2626;
        color: #ffffff;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        display: inline-block;
    }

    /* Cartes Axes d'Amélioration */
    .diagnostic-box {
        background: #1e2430;
        border-radius: 8px;
        border-left: 4px solid #38bdf8;
        padding: 16px;
        margin-bottom: 12px;
    }
    .box-strong { border-left-color: #10b981; }
    .box-warning { border-left-color: #f59e0b; }
    .box-catalyst { border-left-color: #8b5cf6; }

    /* News card */
    .news-box {
        background: #181d26;
        border: 1px solid #282f3c;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
    }
    .news-title {
        color: #e2e8f0;
        font-weight: 600;
        text-decoration: none;
    }
    .news-title:hover {
        color: #60a5fa;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# STATE & INITIALISATION
# ==============================================================================
if "watchlist" not in st.session_state:
    st.session_state.watchlist = list(DEFAULT_WATCHLIST)

if "cache_version" not in st.session_state:
    st.session_state.cache_version = 1


# ==============================================================================
# MOTEUR DE DIAGNOSTIC DES AXES D'AMÉLIORATION
# ==============================================================================
def generate_diagnostic(stock_data: dict) -> dict:
    """
    Génère une analyse diagnostique intelligente des points forts,
    des faiblesses et des axes d'amélioration précis pour passer en recommandation BUY/STRONG BUY.
    """
    points_forts = []
    points_faibles = []
    axes_amelioration = []

    sub = stock_data.get("sub_scores", {})
    raw = stock_data.get("raw_metrics", {})
    mom = stock_data.get("momentum", 0.0)
    sent = stock_data.get("sentiment", 0.0)
    vol = stock_data.get("volatility_annualized", 0.0)
    fund = stock_data.get("fundamental_score", 50.0)
    rsi = stock_data.get("rsi_14", 50.0)
    price = stock_data.get("price", 0.0)
    sma20 = stock_data.get("sma_20", 0.0)

    # 1. Analyse Fondamentale
    sc_croissance = sub.get("croissance", 50)
    if sc_croissance is not None:
        if sc_croissance >= 70:
            points_forts.append(f"Dynamique de croissance vigoureuse (score : {sc_croissance:.0f}/100)")
        elif sc_croissance < 45:
            points_faibles.append(f"Croissance du chiffre d'affaires ou de l'EPS ralentie ({sc_croissance:.0f}/100)")
            axes_amelioration.append("Besoin d'une ré-accélération de la croissance du chiffre d'affaires YoY au-dessus de +15%.")

    sc_rentab = sub.get("rentabilite", 50)
    if sc_rentab is not None:
        if sc_rentab >= 70:
            points_forts.append(f"Excellente rentabilité opérationnelle et fort spread ROIC-WACC ({sc_rentab:.0f}/100)")
        elif sc_rentab < 50:
            points_faibles.append(f"Marges sous pression concurrentielle ou ROIC faible ({sc_rentab:.0f}/100)")
            axes_amelioration.append("Améliorer la marge d'exploitation pour générer un surcroît de retour sur capital (ROIC).")

    sc_bilan = sub.get("bilan", 50)
    if sc_bilan is not None:
        if sc_bilan >= 80:
            points_forts.append(f"Bilan extrêmement sain : faible endettement ou trésorerie nette positive ({sc_bilan:.0f}/100)")
        elif sc_bilan < 50:
            points_faibles.append(f"Niveau d'endettement net / EBITDA préoccupant ({sc_bilan:.0f}/100)")
            axes_amelioration.append("Désendettement prioritaire : ramener le ratio Dette Nette / EBITDA sous 2.0x.")

    sc_cash = sub.get("cash", 50)
    if sc_cash is not None:
        if sc_cash >= 75:
            points_forts.append(f"Génération de Free Cash Flow robuste et taux de conversion élevé ({sc_cash:.0f}/100)")
        elif sc_cash < 50:
            points_faibles.append(f"Faible conversion du résultat net en cash disponible ({sc_cash:.0f}/100)")
            axes_amelioration.append("Optimiser le besoin en fonds de roulement pour améliorer la conversion en Free Cash Flow.")

    # 2. Analyse Technique & Momentum
    if mom > 0.4:
        points_forts.append(f"Tendance technique haussière confirmée (Momentum : +{mom:.2f})")
    elif mom < -0.3:
        points_faibles.append(f"Pression vendeuse à court terme (Momentum négatif : {mom:.2f})")
        if price < sma20:
            axes_amelioration.append(f"Catalyseur technique attendu : reprise au-dessus de la moyenne mobile 20 jours ({sma20:.2f}).")

    if rsi > 70:
        points_faibles.append(f"Zone de surachat technique (RSI 14 : {rsi:.1f}) — risque de respiration à court terme.")
    elif rsi < 35:
        points_forts.append(f"Zone de survente technique (RSI 14 : {rsi:.1f}) — opportunité d'achat sur repli potentiel.")

    # 3. Volatilité & Actualités
    if vol > 50:
        points_faibles.append(f"Volatilité annualisée élevée ({vol:.1f}%) — profil plus spéculatif que défensif.")
        axes_amelioration.append("Recherche de stabilisation de cours pour entrer dans les critères de « volatilité saine ».")
    elif vol < 30:
        points_forts.append(f"Volatilité saine et maîtrisée ({vol:.1f}% annualisée)")

    if sent > 0.6:
        points_forts.append(f"Flux d'actualités et sentiment de presse très favorables (+{sent:.2f})")
    elif sent < -0.1:
        points_faibles.append(f"Climat d'actualités négatif ou prudent ({sent:.2f})")
        axes_amelioration.append("Attendre un apaisement médiatique et de prochaines publications financières favorables.")

    if not points_forts:
        points_forts.append("Profil équilibré sans distorsion majeure constatée.")
    if not points_faibles:
        points_faibles.append("Aucun facteur de risque critique identifié sur les métriques actuelles.")
    if not axes_amelioration:
        axes_amelioration.append("Maintenir la trajectoire opérationnelle et surveiller les niveaux de support clés.")

    return {
        "points_forts": points_forts,
        "points_faibles": points_faibles,
        "axes_amelioration": axes_amelioration
    }


# ==============================================================================
# PIPELINE DE CHARGEMENT DES DONNÉES
# ==============================================================================
@st.cache_data(ttl=600, show_spinner=False)
def analyze_single_ticker(ticker: str, cache_key: int = 1) -> dict:
    """Analyse complète d'un titre individuel."""
    df_price = get_single_price_data(ticker)
    if df_price is None or df_price.empty or len(df_price) < 5:
        return None

    tech = compute_indicators(df_price)

    try:
        news_items = get_news(ticker, limit=8)
        sentiment_score = news_sentiment(news_items)
    except Exception:
        news_items = []
        sentiment_score = 0.0

    try:
        raw_fund = get_raw_fundamental_data(ticker)
        fund_results = calculate_fundamental_score(raw_fund)
        short_name = raw_fund.get("short_name", ticker)
        sector = raw_fund.get("sector", "Technologie")
        industry = raw_fund.get("industry", "Divers")
    except Exception:
        raw_fund = {}
        fund_results = {}
        short_name = ticker
        sector = "Divers"
        industry = "Divers"

    fund_score = fund_results.get("fundamental_score", 50.0)
    momentum = tech.get("momentum", 0.0)
    alpha_score = calculate_alpha_score(momentum, sentiment_score, fund_score)
    signal = determine_signal(alpha_score, fund_score, momentum)

    res = {
        "ticker": ticker,
        "short_name": short_name,
        "sector": sector,
        "industry": industry,
        "price": tech.get("current_price", 0.0),
        "change_1d": tech.get("change_1d", 0.0),
        "change_5d": tech.get("change_5d", 0.0),
        "volatility_20d": tech.get("volatility_20d", 0.0),
        "volatility_annualized": tech.get("volatility_annualized", 0.0),
        "rsi_14": tech.get("rsi_14", 50.0),
        "sma_20": tech.get("sma_20", 0.0),
        "sma_50": tech.get("sma_50", 0.0),
        "momentum": momentum,
        "sentiment": sentiment_score,
        "fundamental_score": fund_score,
        "alpha_score": alpha_score,
        "signal": signal,
        "completeness_rate": fund_results.get("completeness_rate", 0.0),
        "sub_scores": fund_results.get("sub_scores", {}),
        "raw_metrics": fund_results.get("raw_metrics", {}),
        "news": news_items,
    }

    # Ajouter le diagnostic automatique
    res["diagnostic"] = generate_diagnostic(res)
    return res


def scan_universe(tickers: list) -> pd.DataFrame:
    """Scanne tous les titres et retourne le DataFrame trié."""
    data = []
    p_bar = st.progress(0, text="Calcul des scores quantitatifs en cours...")
    for idx, t in enumerate(tickers):
        p_bar.progress((idx + 1) / len(tickers), text=f"Scan : {t} ({idx+1}/{len(tickers)})")
        res = analyze_single_ticker(t, cache_key=st.session_state.cache_version)
        if res:
            data.append(res)
    p_bar.empty()

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    return df.sort_values(by="alpha_score", ascending=False).reset_index(drop=True)


# ==============================================================================
# SIDEBAR NAVIGATION & WATCHLIST
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚡ **Alpha Studio** `v4.0`")
    st.caption("Module Fondamental (Word) • Momentum • News RSS")

    st.markdown("---")
    st.write(f"**Actions surveillées :** `{len(st.session_state.watchlist)} titres`")

    if st.button("🔄 Rafraîchir les Données", use_container_width=True):
        st.session_state.cache_version += 1
        st.rerun()

    st.markdown("---")
    st.subheader("🎯 Filtres Rapides")
    min_alpha = st.slider("Score Alpha Min.", -3.0, 3.0, -1.0, 0.1)
    market_filter = st.selectbox("Zone Géographique", ["Tous les Marchés", "Actions US", "Actions Europe (.PA, .DE)"])

    st.markdown("---")
    st.markdown("""
    **Guide des Signaux :**
    - 🟢 `BUY` : Alpha > +0.4 & Fondamentaux solides
    - 🟡 `HOLD` : Zone neutre / consolidation
    - 🔴 `SELL` : Dégradation technique ou fondamentale
    """)


# ==============================================================================
# CHARGEMENT DES RÉSULTATS
# ==============================================================================
df_all = scan_universe(st.session_state.watchlist)

if df_all.empty:
    st.error("Aucune donnée disponible. Veuillez vérifier votre connexion.")
    st.stop()

# Filtrage géographique
df_filtered = df_all[df_all["alpha_score"] >= min_alpha]
if market_filter == "Actions US":
    df_filtered = df_filtered[~df_filtered["ticker"].str.contains(r"\.", na=False)]
elif market_filter == "Actions Europe (.PA, .DE)":
    df_filtered = df_filtered[df_filtered["ticker"].str.contains(r"\.", na=False)]


# ==============================================================================
# BANDEAU SUPÉRIEUR (VISUAL STUDIO STYLE)
# ==============================================================================
col_head1, col_head2, col_head3, col_head4, col_head5 = st.columns([3, 1.2, 1.2, 1.2, 1.2])

with col_head1:
    st.markdown("## 💻 Alpha Terminal Studio")
    st.caption("Analyse multi-dimensionnelle conforme au document de méthodologie officiel.")

with col_head2:
    st.markdown(f"""
    <div class="studio-card">
        <div class="studio-title">Univers Actif</div>
        <div class="studio-value">{len(df_all)}</div>
        <div class="studio-desc">Titres analysés</div>
    </div>
    """, unsafe_allow_html=True)

with col_head3:
    nb_buys = len(df_all[df_all["signal"].str.contains("BUY")])
    st.markdown(f"""
    <div class="studio-card">
        <div class="studio-title">Opportunités BUY</div>
        <div class="studio-value" style="color:#34d399;">{nb_buys}</div>
        <div class="studio-desc">Sur {len(df_all)} actions</div>
    </div>
    """, unsafe_allow_html=True)

with col_head4:
    best_stock = df_all.iloc[0]
    st.markdown(f"""
    <div class="studio-card">
        <div class="studio-title">Top Alpha</div>
        <div class="studio-value" style="color:#38bdf8;">{best_stock['ticker']}</div>
        <div class="studio-desc">Score : {best_stock['alpha_score']}</div>
    </div>
    """, unsafe_allow_html=True)

with col_head5:
    avg_vol = round(df_all["volatility_annualized"].mean(), 1)
    st.markdown(f"""
    <div class="studio-card">
        <div class="studio-title">Volatilité Moy.</div>
        <div class="studio-value" style="color:#a855f7;">{avg_vol}%</div>
        <div class="studio-desc">Vol. annualisée</div>
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# ONGLETS DE NAVIGATION (VISUAL STUDIO TABS)
# ==============================================================================
tab_results, tab_charts, tab_diagnostic, tab_news, tab_matrix, tab_manage = st.tabs([
    "🏆 Top 10 & Résultats",
    "📈 Analyse Graphique Interactive",
    "🎯 Diagnostic & Axes d'Amélioration",
    "📰 Actualités en Direct (Illimité)",
    "📊 Matrice Risque / Volatilité",
    "⚙️ Gestionnaire Watchlist"
])


# ==============================================================================
# ONGLET 1 : TOP 10 & CLASSEMENT GLOBAL
# ==============================================================================
with tab_results:
    st.subheader("🏆 Classement Général & Recommandations")

    # Tableau interactif avec tri multi-colonnes et mise en forme
    show_df = df_filtered.copy()
    display_cols = [
        "ticker", "short_name", "price", "change_1d", "change_5d",
        "signal", "alpha_score", "fundamental_score", "momentum",
        "sentiment", "volatility_annualized", "rsi_14", "sector"
    ]
    renames = {
        "ticker": "Ticker", "short_name": "Société", "price": "Prix ($/€)",
        "change_1d": "Var. 1J (%)", "change_5d": "Var. 5J (%)",
        "signal": "Signal", "alpha_score": "Score Alpha",
        "fundamental_score": "Score Fondamental (/100)", "momentum": "Momentum",
        "sentiment": "Sentiment News", "volatility_annualized": "Volatilité Ann. (%)",
        "rsi_14": "RSI 14", "sector": "Secteur"
    }

    valid_cols = [c for c in display_cols if c in show_df.columns]
    table = show_df[valid_cols].rename(columns=renames)

    st.dataframe(
        table,
        use_container_width=True,
        height=480,
        column_config={
            "Prix ($/€)": st.column_config.NumberColumn(format="%.2f"),
            "Var. 1J (%)": st.column_config.NumberColumn(format="%+.2f%%"),
            "Var. 5J (%)": st.column_config.NumberColumn(format="%+.2f%%"),
            "Score Alpha": st.column_config.NumberColumn(format="%.2f"),
            "Score Fondamental (/100)": st.column_config.ProgressColumn(format="%.1f", min_value=0, max_value=100),
            "Volatilité Ann. (%)": st.column_config.NumberColumn(format="%.1f%%"),
            "RSI 14": st.column_config.NumberColumn(format="%.1f"),
        }
    )

    c_down1, c_down2 = st.columns([2, 4])
    with c_down1:
        csv_data = df_all.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Exporter les résultats (CSV)",
            data=csv_data,
            file_name="alpha_results.csv",
            mime="text/csv",
            use_container_width=True
        )


# ==============================================================================
# ONGLET 2 : ANALYSE GRAPHIQUE INTERACTIVE (CHANDELIERS + VOLUMES + RSI)
# ==============================================================================
with tab_charts:
    st.subheader("📈 Studio Graphique & Indicateurs Techniques")

    c_t, c_p = st.columns([3, 1])
    with c_t:
        active_ticker = st.selectbox("Sélectionnez l'action à analyser :", options=df_all["ticker"].tolist(), key="chart_tick")
    with c_p:
        history_range = st.selectbox("Période :", ["1mo", "3mo", "6mo", "1y", "2y"], index=2, key="chart_period")

    selected_row = df_all[df_all["ticker"] == active_ticker].iloc[0]

    # Bandeau métriques
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    col_m1.metric("Dernier Cours", f"{selected_row['price']} $ / €", f"{selected_row['change_1d']:+.2f}%")
    col_m2.metric("Score Alpha", f"{selected_row['alpha_score']}", f"Signal: {selected_row['signal']}")
    col_m3.metric("Score Fondamental", f"{selected_row['fundamental_score']}/100", f"Complétude: {selected_row['completeness_rate']}%")
    col_m4.metric("Volatilité Ann.", f"{selected_row['volatility_annualized']}%", "Vol. saine < 35%")
    col_m5.metric("RSI (14j)", f"{selected_row['rsi_14']}", "Survente <30 | Surachat >70")

    # Téléchargement et tracé Plotly interactif
    df_chart = get_single_price_data(active_ticker, period=history_range)

    if df_chart is not None and not df_chart.empty and len(df_chart) >= 5:
        df_chart["SMA20"] = df_chart["Close"].rolling(20).mean()
        df_chart["SMA50"] = df_chart["Close"].rolling(50).mean()

        # Calcul RSI
        delta = df_chart["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df_chart["RSI"] = 100 - (100 / (1 + rs))

        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.60, 0.20, 0.20],
            subplot_titles=[f"Chandeliers Japonais & Moyennes Mobiles ({active_ticker})", "Volume", "RSI (14 jours)"]
        )

        fig.add_trace(
            go.Candlestick(
                x=df_chart.index,
                open=df_chart["Open"], high=df_chart["High"],
                low=df_chart["Low"], close=df_chart["Close"],
                name="Prix",
                increasing_line_color="#10b981",
                decreasing_line_color="#ef4444"
            ),
            row=1, col=1
        )
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["SMA20"], line=dict(color="#f59e0b", width=1.5), name="SMA 20"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["SMA50"], line=dict(color="#3b82f6", width=1.5), name="SMA 50"), row=1, col=1)

        vol_colors = ["#10b981" if c >= o else "#ef4444" for c, o in zip(df_chart["Close"], df_chart["Open"])]
        fig.add_trace(go.Bar(x=df_chart.index, y=df_chart["Volume"], marker_color=vol_colors, name="Volume"), row=2, col=1)

        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["RSI"], line=dict(color="#a855f7", width=1.5), name="RSI"), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#10b981", row=3, col=1)

        fig.update_layout(
            template="plotly_dark",
            height=650,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Données de cours indisponibles pour ce titre.")


# ==============================================================================
# ONGLET 3 : DIAGNOSTIC & AXES D'AMÉLIORATION (NOUVEAU MODULE DEMANDÉ)
# ==============================================================================
with tab_diagnostic:
    st.subheader("🎯 Diagnostic Stratégique & Axes d'Amélioration")
    st.caption("Évaluation granulaire des forces, faiblesses et leviers d'action pour chaque titre.")

    d_ticker = st.selectbox("Choisir l'action à auditer :", options=df_all["ticker"].tolist(), key="diag_tick")
    item = df_all[df_all["ticker"] == d_ticker].iloc[0]
    diag = item["diagnostic"]
    sub = item.get("sub_scores", {})
    raw = item.get("raw_metrics", {})

    col_diag1, col_diag2 = st.columns([1.2, 1.8])

    with col_diag1:
        # DIAGRAMME RADAR (ARAIGNÉE) DES 5 SOUS-SCORES
        st.markdown("**Radar des 5 Piliers Fondamentaux (Doc Word) :**")
        categories = ["Croissance (20%)", "Rentabilité (25%)", "Solidité Bilan (25%)", "Cash Flow (20%)", "Moat (10%)"]
        values = [
            sub.get("croissance", 50) or 0,
            sub.get("rentabilite", 50) or 0,
            sub.get("bilan", 50) or 0,
            sub.get("cash", 50) or 0,
            sub.get("moat", 50) or 0,
        ]
        # Fermer la boucle
        categories_closed = categories + [categories[0]]
        values_closed = values + [values[0]]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            fill="toself",
            name=d_ticker,
            line=dict(color="#38bdf8", width=2),
            fillcolor="rgba(56, 189, 248, 0.25)"
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=[80, 80, 80, 80, 80, 80],
            theta=categories_closed,
            name="Seuil d'Excellence",
            line=dict(color="#10b981", dash="dot", width=1.5)
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            template="plotly_dark",
            height=380,
            margin=dict(l=30, r=30, t=20, b=20),
            showlegend=True,
            legend=dict(orientation="h", y=-0.1)
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_diag2:
        # CARTES DE DIAGNOSTIC DÉTAILLÉES
        st.markdown(f"### Diagnostic de `{d_ticker}` — {item['short_name']}")
        sig = item["signal"]
        badge_style = "signal-buy" if "BUY" in sig else ("signal-sell" if "SELL" in sig else "signal-hold")
        st.markdown(f"**Recommandation Actuelle :** <span class='{badge_style}'>{sig}</span> (Score Alpha : **{item['alpha_score']}**)", unsafe_allow_html=True)
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # Points Forts
        st.markdown("""
        <div class="diagnostic-box box-strong">
            <b style="color: #34d399;">✅ Points Forts Identifiés :</b>
        </div>
        """, unsafe_allow_html=True)
        for pf in diag["points_forts"]:
            st.markdown(f"- 🟢 {pf}")

        # Points de Vigilance / Faiblesses
        st.markdown("""
        <div class="diagnostic-box box-warning" style="margin-top: 15px;">
            <b style="color: #fbbf24;">⚠️ Points de Vigilance & Risques :</b>
        </div>
        """, unsafe_allow_html=True)
        for pv in diag["points_faibles"]:
            st.markdown(f"- 🟡 {pv}")

        # Axes d'Amélioration concrets
        st.markdown("""
        <div class="diagnostic-box box-catalyst" style="margin-top: 15px;">
            <b style="color: #c084fc;">🚀 Axes d'Amélioration & Catalyseurs pour déclencher un Achat (BUY) :</b>
        </div>
        """, unsafe_allow_html=True)
        for aa in diag["axes_amelioration"]:
            st.markdown(f"- 💡 **{aa}**")


# ==============================================================================
# ONGLET 4 : ACTUALITÉS EN DIRECT (SANS CLÉ API)
# ==============================================================================
with tab_news:
    st.subheader("📰 Fil d'Actualités Financières en Direct (100% Gratuit & Illimité)")
    st.caption("Agrégation multi-flux Yahoo Finance & Google News RSS sans aucune restriction de jetons.")

    n_ticker = st.selectbox("Filtrer par action :", options=["Toutes"] + df_all["ticker"].tolist(), key="news_select")

    articles = []
    if n_ticker == "Toutes":
        for t in df_all["ticker"].head(5):
            t_row = df_all[df_all["ticker"] == t].iloc[0]
            for art in t_row.get("news", [])[:3]:
                a = dict(art)
                a["ticker"] = t
                articles.append(a)
    else:
        t_row = df_all[df_all["ticker"] == n_ticker].iloc[0]
        articles = t_row.get("news", [])

    if articles:
        for a in articles:
            s_label = a.get("sentiment_label", "Neutre")
            s_color = "#10b981" if s_label == "Positif" else ("#ef4444" if s_label == "Négatif" else "#94a3b8")
            badge = f"<span style='color:{s_color}; font-weight:600; font-size:0.8rem; background:{s_color}22; padding:2px 8px; border-radius:10px;'>{s_label}</span>"
            t_tag = f"<span style='background:#3b82f6; color:#fff; padding:2px 6px; border-radius:4px; font-size:0.75rem;'>{a.get('ticker', n_ticker)}</span> "

            st.markdown(f"""
            <div class="news-box">
                <div>{t_tag} {badge}</div>
                <div style="margin-top: 6px;">
                    <a href="{a.get('link', '#')}" target="_blank" class="news-title">🔗 {a.get('title')}</a>
                </div>
                <div style="font-size:0.78rem; color:#64748b; margin-top:4px;">
                    Source : <b>{a.get('publisher', 'Yahoo Finance')}</b> • Date : {a.get('published', 'Récemment')}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Aucune actualité disponible pour ce filtre.")


# ==============================================================================
# ONGLET 5 : MATRICE RISQUE & VOLATILITÉ SAINE
# ==============================================================================
with tab_matrix:
    st.subheader("📊 Matrice Statistiques & Détection de « Volatilité Saine »")
    st.caption("L'objectif de la stratégie Alpha est d'isoler les entreprises à fondamentaux solides et volatilité maîtrisée.")

    col_m1, col_m2 = st.columns([1.6, 1])

    with col_m1:
        # Nuage de points Volatilité vs Score Fondamental
        fig_scatter = go.Figure()
        for s_type, col in [("BUY", "#10b981"), ("HOLD", "#f59e0b"), ("SELL", "#ef4444")]:
            sub_df = df_all[df_all["signal"].str.contains(s_type)]
            if not sub_df.empty:
                fig_scatter.add_trace(go.Scatter(
                    x=sub_df["volatility_annualized"],
                    y=sub_df["fundamental_score"],
                    mode="markers+text",
                    text=sub_df["ticker"],
                    textposition="top center",
                    marker=dict(size=14, color=col, line=dict(width=1, color="#ffffff")),
                    name=s_type
                ))

        # Zone idéale de volatilité saine
        fig_scatter.add_shape(
            type="rect",
            x0=15, y0=70, x1=35, y1=100,
            fillcolor="rgba(16, 185, 129, 0.12)",
            line=dict(color="#10b981", dash="dash", width=1),
        )
        fig_scatter.add_annotation(
            x=25, y=95,
            text="Zone Idéale : Volatilité Saine & Fondamentaux Forts",
            showarrow=False,
            font=dict(color="#34d399", size=11)
        )

        fig_scatter.update_layout(
            title="Score Fondamental (0-100) vs Volatilité Annualisée (%)",
            xaxis_title="Volatilité Annualisée (%)",
            yaxis_title="Score Fondamental",
            template="plotly_dark",
            height=430,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col_m2:
        sig_counts = df_all["signal"].apply(lambda s: "BUY" if "BUY" in s else ("SELL" if "SELL" in s else "HOLD")).value_counts()
        fig_donut = go.Figure(data=[go.Pie(
            labels=sig_counts.index,
            values=sig_counts.values,
            hole=0.55,
            marker_colors=["#10b981", "#f59e0b", "#ef4444"]
        )])
        fig_donut.update_layout(
            title="Répartition des Signaux Recommandés",
            template="plotly_dark",
            height=430,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_donut, use_container_width=True)


# ==============================================================================
# ONGLET 6 : GESTIONNAIRE DE WATCHLIST & CONFIGURATION
# ==============================================================================
with tab_manage:
    st.subheader("⚙️ Gestion de l'Univers d'Investissement & Watchlist")

    col_w1, col_w2 = st.columns(2)

    with col_w1:
        st.markdown("**Ajouter une nouvelle action :**")
        add_t = st.text_input("Symbole Boursier (ex: TSLA, GOOGL, AIR.PA, SAP.DE, MC.PA)", "").strip().upper()
        if st.button("➕ Ajouter au Scanner"):
            if add_t and add_t not in st.session_state.watchlist:
                st.session_state.watchlist.append(add_t)
                st.session_state.cache_version += 1
                st.success(f"Action {add_t} ajoutée avec succès à la watchlist !")
                st.rerun()
            elif add_t in st.session_state.watchlist:
                st.warning("Ce ticker est déjà présent dans la liste.")

        st.markdown("<br>**Retirer une action de la liste :**", unsafe_allow_html=True)
        del_t = st.selectbox("Choisir un ticker à retirer :", options=st.session_state.watchlist)
        if st.button("🗑️ Supprimer de la Watchlist"):
            if del_t in st.session_state.watchlist:
                st.session_state.watchlist.remove(del_t)
                st.session_state.cache_version += 1
                st.success(f"{del_t} retiré.")
                st.rerun()

    with col_w2:
        st.markdown("**Paramètres du Score Alpha Composite :**")
        st.write("Le score Alpha combine les 3 dimensions stratégiques :")
        st.write("- **Poids Fondamental** : 40% (filtrage de solidité)")
        st.write("- **Poids Momentum** : 40% (dynamique de prix et volume)")
        st.write("- **Poids Sentiment** : 20% (flux d'actualités)")

        st.markdown("<br>**Réinitialisation :**", unsafe_allow_html=True)
        if st.button("♻️ Rétablir la Watchlist par Défaut"):
            st.session_state.watchlist = list(DEFAULT_WATCHLIST)
            st.session_state.cache_version += 1
            st.rerun()
