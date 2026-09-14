# -*- coding: utf-8 -*-
"""
Fournisseur de données de marché et financières (prix historiques, données fondamentales, ratios).
Dispose d'une gestion autonome de session Yahoo Finance (cookies + crumb dynamiques) et d'un cache local performant.
"""

import os
import json
import time
import datetime
import requests
import pandas as pd
import numpy as np
import yfinance as yf

CACHE_DIR = "cache_prices"
os.makedirs(CACHE_DIR, exist_ok=True)

FUND_CACHE_DIR = os.path.join("data", "cache")
os.makedirs(FUND_CACHE_DIR, exist_ok=True)


class YahooSessionManager:
    """Gère l'authentification et les miettes (crumb) Yahoo Finance pour un accès direct et illimité."""
    _session = None
    _crumb = None
    _last_crumb_time = 0

    @classmethod
    def get_session_and_crumb(cls):
        now = time.time()
        if cls._session is None or cls._crumb is None or (now - cls._last_crumb_time > 1800):
            s = requests.Session()
            s.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            })
            try:
                s.get("https://fc.yahoo.com", timeout=6)
                r_crumb = s.get("https://query2.finance.yahoo.com/v1/test/getcrumb", timeout=6)
                if r_crumb.status_code == 200 and r_crumb.text.strip():
                    cls._crumb = r_crumb.text.strip()
                    cls._session = s
                    cls._last_crumb_time = now
            except Exception as e:
                print(f"⚠️ Erreur initialisation session Yahoo: {e}")
                if cls._session is None:
                    cls._session = s
        return cls._session, cls._crumb


# ==========================================
# 1. PRIX DU MARCHÉ (OHLCV)
# ==========================================
def download_direct_chart(ticker: str, range_period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Téléchargement direct et ultra-rapide des chandeliers Yahoo sans passer par la librairie yfinance."""
    session, _ = YahooSessionManager.get_session_and_crumb()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={range_period}"
    try:
        res = session.get(url, timeout=7)
        if res.status_code == 200:
            payload = res.json().get("chart", {}).get("result", [])
            if payload:
                data = payload[0]
                timestamps = data.get("timestamp", [])
                indicators = data.get("indicators", {}).get("quote", [{}])[0]
                if timestamps and indicators:
                    dates = [datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d") for ts in timestamps]
                    df = pd.DataFrame({
                        "Open": indicators.get("open", []),
                        "High": indicators.get("high", []),
                        "Low": indicators.get("low", []),
                        "Close": indicators.get("close", []),
                        "Volume": indicators.get("volume", [])
                    }, index=pd.to_datetime(dates))
                    df = df.dropna()
                    if not df.empty and len(df) >= 5:
                        return df
    except Exception as e:
        print(f"⚠️ Erreur chart direct {ticker}: {e}")
    return pd.DataFrame()


def get_single_price_data(ticker: str, period: str = "6mo", max_cache_hours: int = 4) -> pd.DataFrame:
    """
    Récupère l'historique de prix pour un ticker.
    Utilise le cache local si celui-ci date de moins de max_cache_hours.
    """
    cache_path = os.path.join(CACHE_DIR, f"{ticker}.csv")

    # 1. Vérification Cache
    if os.path.exists(cache_path):
        mtime = os.path.getmtime(cache_path)
        age_hours = (time.time() - mtime) / 3600.0
        if age_hours < max_cache_hours:
            try:
                df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                if not df.empty and "Close" in df.columns:
                    return df
            except Exception:
                pass

    # 2. Téléchargement direct (ultra fiable)
    df = download_direct_chart(ticker, range_period=period)
    if not df.empty:
        df.to_csv(cache_path)
        return df

    # 3. Tentative de fallback via yfinance
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        if df is not None and not df.empty and len(df) >= 5:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]
            df.to_csv(cache_path)
            return df
    except Exception:
        pass

    # 4. Fallback vers cache existant
    if os.path.exists(cache_path):
        try:
            return pd.read_csv(cache_path, index_col=0, parse_dates=True)
        except Exception:
            pass

    return pd.DataFrame()


def get_bulk_price_data(tickers: list, period: str = "3mo") -> dict:
    """Télécharge les cours pour une liste d'actions en s'assurant que chaque ticker a ses données."""
    results = {}
    for ticker in tickers:
        df = get_single_price_data(ticker, period=period)
        if not df.empty:
            results[ticker] = df
    return results


def load_from_cache(ticker: str) -> pd.DataFrame:
    """Charge les données de prix depuis le cache local."""
    cache_path = os.path.join(CACHE_DIR, f"{ticker}.csv")
    if os.path.exists(cache_path):
        try:
            return pd.read_csv(cache_path, index_col=0, parse_dates=True)
        except Exception:
            pass
    return None


# ==========================================
# 2. DONNÉES FONDAMENTALES (PROJET ALPHA)
# ==========================================
def get_raw_fundamental_data(ticker: str, max_cache_hours: int = 24) -> dict:
    """
    Extrait les données fondamentales nécessaires au module de scoring ALPHA.
    Met en cache les résultats dans data/cache/{ticker}_fund.json pour éviter les requêtes redondantes.
    """
    cache_file = os.path.join(FUND_CACHE_DIR, f"{ticker}_fund.json")

    # 1. Vérifier le cache local
    if os.path.exists(cache_file):
        age_hours = (time.time() - os.path.getmtime(cache_file)) / 3600.0
        if age_hours < max_cache_hours:
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    # 2. Requête directe Yahoo Finance QuoteSummary
    session, crumb = YahooSessionManager.get_session_and_crumb()
    modules = "financialData,defaultKeyStatistics,summaryDetail,assetProfile,price"
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules={modules}"
    if crumb:
        url += f"&crumb={crumb}"

    raw_metrics = {}
    try:
        res = session.get(url, timeout=8)
        if res.status_code == 200:
            payload = res.json().get("quoteSummary", {}).get("result", [{}])[0]
            fin = payload.get("financialData", {})
            stats = payload.get("defaultKeyStatistics", {})
            prof = payload.get("assetProfile", {})
            price_info = payload.get("price", {})

            def get_f(dict_obj, key):
                v = dict_obj.get(key)
                if isinstance(v, dict):
                    return v.get("raw")
                return v

            short_name = price_info.get("shortName") or price_info.get("longName") or ticker
            sector = prof.get("sector", "Technologie")
            industry = prof.get("industry", "Divers")

            # Données financières de base
            rev_growth = get_f(fin, "revenueGrowth")
            gross_margin = get_f(fin, "grossMargins")
            op_margin = get_f(fin, "operatingMargins")
            roe = get_f(fin, "returnOnEquity")
            current_ratio = get_f(fin, "currentRatio")
            total_debt = get_f(fin, "totalDebt") or 0.0
            total_cash = get_f(fin, "totalCash") or 0.0
            ebitda = get_f(fin, "ebitda") or 0.0
            fcf = get_f(fin, "freeCashflow")
            revenue = get_f(fin, "totalRevenue") or 1.0

            eps_growth = get_f(stats, "earningsQuarterlyGrowth")
            beta = get_f(stats, "beta") or 1.0

            # Dette nette / EBITDA
            net_debt = total_debt - total_cash
            if ebitda and abs(ebitda) > 0:
                net_debt_ebitda = float(net_debt / ebitda)
            else:
                net_debt_ebitda = 0.0 if net_debt <= 0 else 5.0

            # Spread ROIC - WACC
            wacc_est = 0.04 + (beta * 0.05)
            roic_est = (op_margin * 0.79 * 1.5) if (op_margin is not None) else None
            spread_roic_wacc = (roic_est - wacc_est) if roic_est is not None else None

            # FCF conversion & FCF margin
            fcf_margin = (fcf / revenue) if (fcf is not None and revenue > 0) else None
            fcf_conversion = 1.0
            if fcf is not None and op_margin is not None and revenue > 0:
                approx_net_income = revenue * op_margin * 0.79
                if approx_net_income > 0:
                    fcf_conversion = float(fcf / approx_net_income)

            # Couverture des intérêts
            interest_coverage = 15.0 if total_debt <= 0 else float(np.clip(ebitda / max(total_debt * 0.04, 1.0), 0.5, 30.0))

            raw_metrics = {
                "ticker": ticker,
                "short_name": short_name,
                "company_name": prof.get("longBusinessSummary", "")[:120] if prof else short_name,
                "sector": sector,
                "industry": industry,
                "revenue_growth_yoy": rev_growth,
                "revenue_cagr_3y": rev_growth * 0.85 if rev_growth is not None else None,
                "eps_growth_yoy": eps_growth,
                "gross_margin": gross_margin,
                "operating_margin": op_margin,
                "roe": roe,
                "spread_roic_wacc": spread_roic_wacc,
                "net_debt_ebitda": net_debt_ebitda,
                "interest_coverage": interest_coverage,
                "current_ratio": current_ratio,
                "fcf_conversion": fcf_conversion,
                "fcf_margin": fcf_margin,
                "gross_margin_std_5y": 0.015,
                "roic_trend": 0.02,
                "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(raw_metrics, f, indent=2)

    except Exception as e:
        print(f"⚠️ Erreur récupération fondamentaux {ticker}: {e}")

    return raw_metrics