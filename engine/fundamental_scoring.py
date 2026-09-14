# -*- coding: utf-8 -*-
"""
Module de scoring fondamental conforme à la méthodologie "PROJET ALPHA".
Évalue la solidité financière pour limiter le risque de perte permanente de capital.

5 dimensions normalisées (0-100) :
1. Croissance (20%)
2. Rentabilité (25%)
3. Solidité bilancielle (25%)
4. Génération de cash (20%)
5. Proxy de moat (10%)
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np


def normalize_linear(value: Optional[float], low: float, high: float, reverse: bool = False) -> Optional[float]:
    """
    Normalise une valeur brute sur une échelle 0-100 entre un seuil bas et un seuil haut.
    Écrêtage automatique aux bornes [0, 100].
    Si reverse=True, une valeur plus basse donne un score plus élevé.
    """
    if value is None or np.isnan(value):
        return None
    
    val = -value if reverse else value
    low_bound = low
    high_bound = high
    
    if high_bound == low_bound:
        return 50.0
    
    score = ((val - low_bound) / (high_bound - low_bound)) * 100.0
    return float(np.clip(score, 0.0, 100.0))


def calculate_fundamental_score(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcule le score fondamental composite et les 5 sous-scores à partir des données financières brutes.
    Gère les valeurs manquantes par renormalisation dynamique et calcule le taux de complétude.
    """
    total_metrics_count = 14
    available_metrics_count = 0

    def check_val(v):
        nonlocal available_metrics_count
        if v is not None and not (isinstance(v, float) and np.isnan(v)):
            available_metrics_count += 1
            return v
        return None

    # ==========================================
    # 1. CROISSANCE (Pondération 20%)
    # ==========================================
    ca_yoy = check_val(raw_data.get("revenue_growth_yoy"))
    ca_cagr_3y = check_val(raw_data.get("revenue_cagr_3y"))
    eps_yoy = check_val(raw_data.get("eps_growth_yoy"))

    sub_croissance = []
    s_ca_yoy = normalize_linear(ca_yoy, -0.05, 0.30)
    if s_ca_yoy is not None:
        sub_croissance.append(s_ca_yoy)

    s_cagr = normalize_linear(ca_cagr_3y, 0.00, 0.25)
    if s_cagr is not None:
        sub_croissance.append(s_cagr)

    s_eps_yoy = normalize_linear(eps_yoy, -0.10, 0.35)
    if s_eps_yoy is not None:
        sub_croissance.append(s_eps_yoy)

    score_croissance = float(np.mean(sub_croissance)) if sub_croissance else None

    # ==========================================
    # 2. RENTABILITÉ (Pondération 25%)
    # ==========================================
    gross_margin = check_val(raw_data.get("gross_margin"))
    operating_margin = check_val(raw_data.get("operating_margin"))
    roe = check_val(raw_data.get("roe"))
    spread_roic_wacc = check_val(raw_data.get("spread_roic_wacc"))

    sub_rentabilite = []
    s_gross = normalize_linear(gross_margin, 0.10, 0.70)
    if s_gross is not None:
        sub_rentabilite.append(s_gross)

    s_op = normalize_linear(operating_margin, 0.00, 0.35)
    if s_op is not None:
        sub_rentabilite.append(s_op)

    s_roe = normalize_linear(roe, 0.00, 0.30)
    if s_roe is not None:
        sub_rentabilite.append(s_roe)

    s_spread = normalize_linear(spread_roic_wacc, -0.05, 0.15)
    if s_spread is not None:
        sub_rentabilite.append(s_spread)

    score_rentabilite = float(np.mean(sub_rentabilite)) if sub_rentabilite else None

    # ==========================================
    # 3. SOLIDITÉ BILANCIELLE (Pondération 25%)
    # ==========================================
    net_debt_ebitda = check_val(raw_data.get("net_debt_ebitda"))
    interest_coverage = check_val(raw_data.get("interest_coverage"))
    current_ratio = check_val(raw_data.get("current_ratio"))

    sub_bilan = []
    # Dette nette / EBITDA : inversé (-valeur entre -5.0 et 0.0)
    # Moins de dette = score plus élevé
    s_debt = normalize_linear(net_debt_ebitda, -5.0, 0.0, reverse=True)
    if s_debt is not None:
        sub_bilan.append(s_debt)

    s_interest = normalize_linear(interest_coverage, 1.0, 15.0)
    if s_interest is not None:
        sub_bilan.append(s_interest)

    s_current = normalize_linear(current_ratio, 0.8, 2.5)
    if s_current is not None:
        sub_bilan.append(s_current)

    score_bilan = float(np.mean(sub_bilan)) if sub_bilan else None

    # ==========================================
    # 4. GÉNÉRATION DE CASH (Pondération 20%)
    # ==========================================
    fcf_conversion = check_val(raw_data.get("fcf_conversion"))
    fcf_margin = check_val(raw_data.get("fcf_margin"))

    sub_cash = []
    s_fcf_conv = normalize_linear(fcf_conversion, 0.30, 1.30)
    if s_fcf_conv is not None:
        sub_cash.append(s_fcf_conv)

    s_fcf_marg = normalize_linear(fcf_margin, 0.00, 0.25)
    if s_fcf_marg is not None:
        sub_cash.append(s_fcf_marg)

    score_cash = float(np.mean(sub_cash)) if sub_cash else None

    # ==========================================
    # 5. PROXY DE MOAT (Pondération 10%)
    # ==========================================
    gross_margin_std = check_val(raw_data.get("gross_margin_std_5y"))
    roic_trend = check_val(raw_data.get("roic_trend"))

    sub_moat = []
    # Moins de volatilité de marge brute = plus grand moat (inversé)
    s_moat_std = normalize_linear(gross_margin_std, -0.08, 0.00, reverse=True)
    if s_moat_std is not None:
        sub_moat.append(s_moat_std)

    s_roic_tr = normalize_linear(roic_trend, -0.05, 0.05)
    if s_roic_tr is not None:
        sub_moat.append(s_roic_tr)

    score_moat = float(np.mean(sub_moat)) if sub_moat else None

    # ==========================================
    # SCORE COMPOSITE & RENORMALISATION
    # ==========================================
    weights = {
        "croissance": (0.20, score_croissance),
        "rentabilite": (0.25, score_rentabilite),
        "bilan": (0.25, score_bilan),
        "cash": (0.20, score_cash),
        "moat": (0.10, score_moat),
    }

    weighted_sum = 0.0
    effective_weight_sum = 0.0

    for name, (w, val) in weights.items():
        if val is not None:
            weighted_sum += w * val
            effective_weight_sum += w

    if effective_weight_sum > 0:
        composite_score = round(weighted_sum / effective_weight_sum, 2)
    else:
        composite_score = 50.0  # Neutre par défaut si aucune donnée

    completeness_rate = round((available_metrics_count / total_metrics_count) * 100.0, 1)

    return {
        "fundamental_score": composite_score,
        "completeness_rate": completeness_rate,
        "sub_scores": {
            "croissance": round(score_croissance, 2) if score_croissance is not None else None,
            "rentabilite": round(score_rentabilite, 2) if score_rentabilite is not None else None,
            "bilan": round(score_bilan, 2) if score_bilan is not None else None,
            "cash": round(score_cash, 2) if score_cash is not None else None,
            "moat": round(score_moat, 2) if score_moat is not None else None,
        },
        "raw_metrics": {
            "revenue_growth_yoy": ca_yoy,
            "revenue_cagr_3y": ca_cagr_3y,
            "eps_growth_yoy": eps_yoy,
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "roe": roe,
            "spread_roic_wacc": spread_roic_wacc,
            "net_debt_ebitda": net_debt_ebitda,
            "interest_coverage": interest_coverage,
            "current_ratio": current_ratio,
            "fcf_conversion": fcf_conversion,
            "fcf_margin": fcf_margin,
            "gross_margin_std_5y": gross_margin_std,
            "roic_trend": roic_trend,
        }
    }
