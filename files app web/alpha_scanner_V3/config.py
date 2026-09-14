# -*- coding: utf-8 -*-
"""
Configuration globale du projet Alpha Scanner V3 / V4.
Contient les listes d'actions surveillées, les seuils par défaut et les chemins de données.
"""

import os

# ==========================================
# 1. WATCHLIST PAR DÉFAUT (US & EUROPE)
# ==========================================
DEFAULT_WATCHLIST = [
    # US Tech & AI
    "NVDA",
    "MSFT",
    "AAPL",
    "GOOGL",
    "META",
    "AMZN",
    "TSLA",
    "PLTR",
    "AMD",
    "AVGO",
    "CRWD",
    "SNOW",

    # Europe (Euronext Paris / XETRA)
    "MC.PA",     # LVMH
    "OR.PA",     # L'Oréal
    "TTE.PA",    # TotalEnergies
    "AIR.PA",    # Airbus
    "SAP.DE",    # SAP
]

# Rétrocompatibilité avec les scripts existants
WATCHLIST = DEFAULT_WATCHLIST


def build_watchlist():
    """Renvoie la liste des tickers à analyser."""
    return list(DEFAULT_WATCHLIST)


# ==========================================
# 2. PONDÉRATIONS ALPHA SCORE
# ==========================================
ALPHA_WEIGHTS = {
    "fundamental": 0.40,
    "momentum": 0.40,
    "sentiment": 0.20,
}

# Pondérations du module fondamental (scoring ALPHA_.docx)
FUNDAMENTAL_WEIGHTS = {
    "croissance": 0.20,
    "rentabilite": 0.25,
    "bilan": 0.25,
    "cash": 0.20,
    "moat": 0.10,
}

# ==========================================
# 3. CHEMINS & STOCKAGE
# ==========================================
DATA_DIR = "data"
CACHE_DIR = "cache_prices"
DATABASE_PATH = os.path.join(DATA_DIR, "alpha.db")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "cache"), exist_ok=True)