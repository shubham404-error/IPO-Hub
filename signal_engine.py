import math
import pandas as pd
from datetime import datetime, timezone

def _safe_float(val):
    try:
        return float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return 0.0

def _calc_velocity(snapshots, column, now):
    if len(snapshots) < 2:
        return 0.0
    
    current = snapshots.iloc[-1]
    prev = snapshots.iloc[-2]
    
    dt = (current["captured_at"] - prev["captured_at"]).total_seconds() / 3600.0
    if dt <= 0:
        return 0.0
        
    return (_safe_float(current.get(column)) - _safe_float(prev.get(column))) / dt

def calculate_subscription_metrics(history_df):
    metrics = {
        "v_total": 0.0, "v_qib": 0.0, "v_nii": 0.0, "v_retail": 0.0,
        "a_total": 0.0, "a_qib": 0.0, "a_nii": 0.0, "a_retail": 0.0
    }
    
    if history_df.empty:
        return metrics
        
    history_df["captured_at"] = pd.to_datetime(history_df["captured_at"])
    history_df = history_df.sort_values("captured_at")
    now = datetime.now(timezone.utc)
    
    if len(history_df) >= 2:
        metrics["v_total"] = _calc_velocity(history_df, "total", now)
        metrics["v_qib"] = _calc_velocity(history_df, "qib", now)
        metrics["v_nii"] = _calc_velocity(history_df, "nii", now)
        metrics["v_retail"] = _calc_velocity(history_df, "retail", now)
        
    if len(history_df) >= 3:
        # Calculate velocity for the previous period to find acceleration
        prev_period = history_df.iloc[:-1]
        pv_total = _calc_velocity(prev_period, "total", now)
        pv_qib = _calc_velocity(prev_period, "qib", now)
        pv_nii = _calc_velocity(prev_period, "nii", now)
        pv_retail = _calc_velocity(prev_period, "retail", now)
        
        metrics["a_total"] = metrics["v_total"] - pv_total
        metrics["a_qib"] = metrics["v_qib"] - pv_qib
        metrics["a_nii"] = metrics["v_nii"] - pv_nii
        metrics["a_retail"] = metrics["v_retail"] - pv_retail
        
    return metrics

def calculate_gmp_momentum(current_gmp_pct, gmp_history_df):
    if gmp_history_df.empty or current_gmp_pct is None:
        return None
        
    gmp_history_df["captured_at"] = pd.to_datetime(gmp_history_df["captured_at"])
    gmp_history_df = gmp_history_df.sort_values("captured_at")
    now = datetime.now(timezone.utc)
    
    # Find snapshot ~24h ago
    one_day_ago = now - pd.Timedelta(hours=24)
    past_snapshots = gmp_history_df[gmp_history_df["captured_at"] <= one_day_ago]
    
    if not past_snapshots.empty:
        last_snapshot = past_snapshots.iloc[-1]
        past_gmp_pct = _safe_float(last_snapshot.get("gmp_pct", 0.0))
        return _safe_float(current_gmp_pct) - past_gmp_pct
        
    return None

def calculate_anchor_quality(row):
    # 40% MF participation
    mf_pct = _safe_float(row.get("anchor_mf_pct"))
    mf_score = 0
    if mf_pct > 15: mf_score = 10
    elif mf_pct > 10: mf_score = 8
    elif mf_pct > 5: mf_score = 6
    elif mf_pct > 0: mf_score = 4
    else: mf_score = 2

    # 30% investor breadth
    count = _safe_float(row.get("anchor_count"))
    count_score = 0
    if count > 15: count_score = 10
    elif count > 10: count_score = 8
    elif count > 5: count_score = 6
    elif count > 0: count_score = 4
    else: count_score = 2
    
    # 30% anchor coverage (amount / issue_size)
    amt = _safe_float(row.get("anchor_amount"))
    issue = _safe_float(row.get("issue_size"))
    coverage = (amt / issue * 100) if issue > 0 else 0
    
    cov_score = 0
    if coverage > 30: cov_score = 10
    elif coverage >= 20: cov_score = 8
    elif coverage >= 10: cov_score = 6
    elif coverage >= 5: cov_score = 4
    elif coverage > 0: cov_score = 2
    
    return int(0.4 * mf_score + 0.3 * count_score + 0.3 * cov_score)

def calculate_valuation_score(row):
    pe_score = 0
    pe = _safe_float(row.get("pe_post") or row.get("pe_pre"))
    if pe > 0:
        if pe <= 15: pe_score = 10
        elif pe <= 20: pe_score = 9
        elif pe <= 25: pe_score = 8
        elif pe <= 30: pe_score = 7
        elif pe <= 35: pe_score = 6
        elif pe <= 40: pe_score = 4
        elif pe <= 50: pe_score = 2
        else: pe_score = 1
    
    pb_score = 0
    pb = _safe_float(row.get("price_book"))
    if pb > 0:
        if pb <= 1.5: pb_score = 10
        elif pb <= 2.5: pb_score = 8
        elif pb <= 3.5: pb_score = 6
        elif pb <= 5.0: pb_score = 4
        else: pb_score = 2
        
    if pe > 0 and pb > 0:
        return int(0.6 * pe_score + 0.4 * pb_score)
    elif pe > 0:
        return pe_score
    elif pb > 0:
        return pb_score
    return 5 # Neutral fallback

def calculate_financial_quality(row):
    roe = _safe_float(row.get("roe"))
    roce = _safe_float(row.get("roce"))
    pat = _safe_float(row.get("pat_margin"))
    debt = _safe_float(row.get("debt_equity"))
    
    # Evenly weighted 25% each
    roe_score = 10 if roe > 20 else (8 if roe > 15 else (6 if roe > 10 else (4 if roe > 5 else 2)))
    roce_score = 10 if roce > 20 else (8 if roce > 15 else (6 if roce > 10 else (4 if roce > 5 else 2)))
    pat_score = 10 if pat > 15 else (8 if pat > 10 else (6 if pat > 5 else (4 if pat > 0 else 2)))
    debt_score = 10 if debt < 0.5 else (8 if debt < 1.0 else (6 if debt < 1.5 else (4 if debt < 2.0 else 2)))
    
    return int(0.25 * roe_score + 0.25 * roce_score + 0.25 * pat_score + 0.25 * debt_score)

def nonlinear_score(value, max_val=50):
    """Logarithmic-like decay, reaching 100 at max_val"""
    if value <= 0: return 0
    if value >= max_val: return 100
    # Map 1-50 non-linearly to 0-100
    # math.log(x+1) based
    normalized = math.log(value + 1) / math.log(max_val + 1)
    return normalized * 100

def get_stage_multiplier(row):
    """Determine how far along the IPO is to scale subscription expectations."""
    open_d = pd.to_datetime(row.get("open_date"), errors='coerce')
    close_d = pd.to_datetime(row.get("close_date"), errors='coerce')
    now = pd.Timestamp.now().normalize()
    
    if pd.isna(open_d) or pd.isna(close_d):
        return 1.0 # Default full weight
        
    total_days = (close_d - open_d).days + 1
    if total_days <= 0:
        return 1.0
        
    days_elapsed = (now - open_d).days + 1
    
    if days_elapsed <= 0:
        return 5.0 # Pre-open or Day 1 early
        
    progress = max(0.0, min(1.0, days_elapsed / total_days))
    
    # Continuous decay from 5.0 (start) to 1.0 (end)
    return 1.0 + 4.0 * (1.0 - progress)

def calculate_listing_score(row, metrics, momentum, anchor_score, valuation_score):
    score = 0.0
    
    # 30% GMP
    gmp_pct = _safe_float(row.get("gmp_pct"))
    if gmp_pct > 50: score += 30
    elif gmp_pct > 0: score += (gmp_pct / 50.0) * 30
    
    # 10% GMP Momentum
    if momentum is not None:
        if momentum > 10: score += 10
        elif momentum > 0: score += (momentum / 10.0) * 10
    else:
        # Re-allocate momentum weight to base GMP if no momentum history
        if gmp_pct > 50: score += 10
        elif gmp_pct > 0: score += (gmp_pct / 50.0) * 10
    
    stage_mult = get_stage_multiplier(row)
    
    # 15% NII
    nii = _safe_float(row.get("nii")) * stage_mult
    score += (nonlinear_score(nii, 50) / 100.0) * 15
    
    # 15% QIB
    qib = _safe_float(row.get("qib")) * stage_mult
    score += (nonlinear_score(qib, 50) / 100.0) * 15
    
    # 10% Velocity Total
    v_total = metrics["v_total"]
    if v_total > 5: score += 10
    elif v_total > 0: score += (v_total / 5.0) * 10
    
    # 5% Acceleration Total
    a_total = metrics["a_total"]
    if a_total > 1: score += 5
    elif a_total > 0: score += (a_total / 1.0) * 5
    
    # 5% Anchor Quality
    score += (anchor_score / 10.0) * 5
    
    # 10% Valuation
    score += (valuation_score / 10.0) * 10
    
    return int(min(100, max(0, score)))

def calculate_investment_score(financial_score, valuation_score, anchor_score):
    score = (financial_score / 10.0) * 45 + (valuation_score / 10.0) * 40 + (anchor_score / 10.0) * 15
    return int(min(100, max(0, score)))

def calculate_allotment_scores(row):
    """
    Returns specific estimated allotment chances for Retail, sHNI, bHNI (0-100 scale proxy).
    Uses non-linear inverse mappings based on subscription.
    """
    retail_sub = _safe_float(row.get("retail"))
    snii_sub = _safe_float(row.get("snii"))
    bnii_sub = _safe_float(row.get("bnii"))
    
    def inv_score(sub):
        if sub <= 1: return 100
        # If it's subscribed 10x, chance is roughly 10%. Score = 10.
        # If it's subscribed 50x, chance is 2%. Score = 2.
        return int(min(100, max(1, 100.0 / sub)))
        
    return {
        "allotment_retail": inv_score(retail_sub),
        "allotment_shni": inv_score(snii_sub),
        "allotment_bhni": inv_score(bnii_sub)
    }

def calculate_confidence(row, sub_history, gmp_history):
    pts = 0
    if len(sub_history) >= 2: pts += 1
    if len(sub_history) >= 5: pts += 1
    if len(gmp_history) >= 2: pts += 1
    if row.get("pe_post") or row.get("pe_pre"): pts += 1
    if row.get("roe"): pts += 1
    
    if pts >= 4: return "High"
    if pts >= 2: return "Medium"
    return "Low"

def compute_signals(row, sub_history, gmp_history):
    """
    Computes all signals for an IPO row and returns a dictionary.
    """
    sub_df = pd.DataFrame(sub_history) if sub_history else pd.DataFrame()
    gmp_df = pd.DataFrame(gmp_history) if gmp_history else pd.DataFrame()
    
    metrics = calculate_subscription_metrics(sub_df)
    momentum = calculate_gmp_momentum(row.get("gmp_pct"), gmp_df)
    
    anchor_score = calculate_anchor_quality(row)
    val_score = calculate_valuation_score(row)
    fin_score = calculate_financial_quality(row)
    
    listing = calculate_listing_score(row, metrics, momentum, anchor_score, val_score)
    investment = calculate_investment_score(fin_score, val_score, anchor_score)
    
    allot = calculate_allotment_scores(row)
    # Generic allotment score is average of the three
    overall_allot = int((allot["allotment_retail"] + allot["allotment_shni"] + allot["allotment_bhni"]) / 3.0)
    
    confidence = calculate_confidence(row, sub_history, gmp_history)
    
    return {
        "signal_version": "v1.1",
        "subscription_velocity_total": metrics["v_total"],
        "subscription_velocity_qib": metrics["v_qib"],
        "subscription_velocity_nii": metrics["v_nii"],
        "subscription_velocity_retail": metrics["v_retail"],
        "subscription_acceleration_total": metrics["a_total"],
        "subscription_acceleration_qib": metrics["a_qib"],
        "subscription_acceleration_nii": metrics["a_nii"],
        "subscription_acceleration_retail": metrics["a_retail"],
        "gmp_momentum_24h": momentum,
        "anchor_quality_score": anchor_score,
        "valuation_score": val_score,
        "financial_quality_score": fin_score,
        "listing_score": listing,
        "investment_score": investment,
        "allotment_score": overall_allot,
        "allotment_retail": allot["allotment_retail"],
        "allotment_shni": allot["allotment_shni"],
        "allotment_bhni": allot["allotment_bhni"],
        "signal_confidence": confidence
    }
