import json
import os
import pandas as pd
import streamlit as st
from database import Database

from google import genai
from google.genai import types

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")


def get_gemini_api_key():
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key
    try:
        import streamlit as st
        return st.secrets.get("GEMINI_API_KEY")
    except Exception:
        return None


def _get_client():
    api_key = get_gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=api_key)


# Free-tier protection: avoid accidental bursts and duplicate requests.
import hashlib
import threading
import time

_API_LOCK = threading.Lock()
_LAST_API_CALL = 0.0
_MIN_SECONDS_BETWEEN_CALLS = 2.5

_RESPONSE_CACHE = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL_SECONDS = 90


def _error_text(exc):
    return str(exc or "")


def _status_code(exc):
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
        try:
            if value is not None:
                return int(value)
        except Exception:
            pass

    text = _error_text(exc)
    for code in ("429", "500", "503", "504"):
        if code in text:
            return int(code)
    return None


def _is_daily_quota_error(exc):
    text = _error_text(exc).lower()
    return (
        "quota" in text
        or ("daily" in text and "limit" in text)
        or ("resource exhausted" in text and "per day" in text)
    )


def _is_retryable_rate_error(exc):
    code = _status_code(exc)
    text = _error_text(exc).lower()

    # Never hammer a daily quota that cannot recover during this session.
    if _is_daily_quota_error(exc):
        return False

    if code in (500, 503, 504):
        return True

    if code == 429 or "rate_limit_exceeded" in text or "too many requests" in text:
        return True

    if "service unavailable" in text or "temporarily overloaded" in text:
        return True

    return False


def _friendly_gemini_error(exc):
    code = _status_code(exc)
    text = _error_text(exc)
    lowered = text.lower()

    if _is_daily_quota_error(exc):
        return (
            "Gemini's free-tier daily quota has been reached. "
            "The app will not keep retrying. Please try again after the quota resets."
        )

    if code == 429 or "rate_limit_exceeded" in lowered or "too many requests" in lowered:
        return (
            "Gemini is temporarily rate-limiting the app. "
            "Please wait about 30–60 seconds and try again."
        )

    if code == 503 or "service unavailable" in lowered or "temporarily overloaded" in lowered:
        return (
            "Gemini is temporarily busy. "
            "The app already retried safely. Please try again in a moment."
        )

    return f"Gemini request failed: {text}"


def _cache_key(model, prompt, structured):
    raw = f"{model}|{int(bool(structured))}|{prompt}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _get_cached(key):
    now = time.monotonic()
    with _CACHE_LOCK:
        item = _RESPONSE_CACHE.get(key)
        if not item:
            return None
        timestamp, response_text = item
        if now - timestamp > _CACHE_TTL_SECONDS:
            _RESPONSE_CACHE.pop(key, None)
            return None
        return response_text


def _put_cached(key, response_text):
    with _CACHE_LOCK:
        _RESPONSE_CACHE[key] = (time.monotonic(), response_text)
        if len(_RESPONSE_CACHE) > 100:
            oldest_key = min(_RESPONSE_CACHE, key=lambda k: _RESPONSE_CACHE[k][0])
            _RESPONSE_CACHE.pop(oldest_key, None)


def _wait_for_global_spacing():
    """Serialize calls enough to avoid accidental free-tier bursts."""
    global _LAST_API_CALL

    with _API_LOCK:
        now = time.monotonic()
        wait = _MIN_SECONDS_BETWEEN_CALLS - (now - _LAST_API_CALL)
        if wait > 0:
            time.sleep(wait)
        _LAST_API_CALL = time.monotonic()


def _generate(client, prompt, structured=False, schema=None):
    """
    Gemini request wrapper for the free tier.

    Protections:
    - 90-second cache for identical prompts/context.
    - 2.5-second minimum spacing between API calls in the process.
    - Exponential backoff for transient 503/500/504 errors.
    - Conservative retry for temporary 429 rate limits.
    - No retry for daily quota exhaustion.
    """
    kwargs = {}

    if structured:
        kwargs["response_mime_type"] = "application/json"
        kwargs["response_schema"] = schema if schema else RECOMMENDATION_SCHEMA

    cache_key = _cache_key(MODEL, prompt, structured)
    cached = _get_cached(cache_key)
    if cached is not None:
        class CachedResponse:
            def __init__(self, text):
                self.text = text
        return CachedResponse(cached)

    # 2s, 5s, 10s exponential backoff.
    delays = (2.0, 5.0, 10.0)
    max_attempts = 3
    last_exc = None

    for attempt in range(max_attempts):
        try:
            _wait_for_global_spacing()
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(**kwargs),
            )

            if not response.text:
                raise RuntimeError("Gemini returned an empty response.")

            _put_cached(cache_key, response.text)
            return response

        except Exception as exc:
            last_exc = exc

            if not _is_retryable_rate_error(exc) or attempt == max_attempts - 1:
                raise RuntimeError(_friendly_gemini_error(exc)) from exc

            time.sleep(delays[attempt])

    raise RuntimeError(_friendly_gemini_error(last_exc)) from last_exc


RECOMMENDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "company_name": {"type": "string"},
                    "verdict": {
                        "type": "string",
                        "enum": ["Apply", "Consider", "Avoid", "Insufficient data"],
                    },
                    "investment_score": {"type": "integer"},
                    "allotment_score": {"type": "integer"},
                    "confidence": {
                        "type": "string",
                        "enum": ["High", "Medium", "Low"],
                    },
                    "reason": {"type": "string"},
                    "anchor_signal": {"type": "string"},
                    "valuation_signal": {"type": "string"},
                    "financial_signal": {"type": "string"},
                    "demand_signal": {"type": "string"},
                    "key_risks": {"type": "array", "items": {"type": "string"}},
                    "research_notes": {"type": "string"},
                },
                "required": [
                    "source_id",
                    "company_name",
                    "verdict",
                    "investment_score",
                    "allotment_score",
                    "confidence",
                    "reason",
                    "anchor_signal",
                    "valuation_signal",
                    "financial_signal",
                    "demand_signal",
                    "key_risks",
                    "research_notes",
                ],
            },
        },
    },
    "required": ["summary", "recommendations"],
}


def analyze_ipos(
    ipos,
    objective="Balanced",
    risk_tolerance="Moderate",
    holding_horizon="Listing day",
    horizon=None,
):
    if horizon is not None:
        holding_horizon = horizon

    if not ipos:
        raise ValueError("No IPO data was supplied for analysis.")

    payload = json.dumps(ipos, ensure_ascii=False, default=str)

    prompt = f"""
You are the decision engine for an Indian IPO intelligence application.

User objective: {objective}
Risk tolerance: {risk_tolerance}
Holding horizon: {holding_horizon}

IMPORTANT DATA RULE:
Use ONLY the supplied application IPO data. Do not use web search,
external browsing, outside facts, or assumed investor track records.
If a fact is not present in the supplied data, say that it is unavailable.

IMPORTANT SUBSCRIPTION TIMING:
- Do NOT penalize an IPO simply because QIB subscription is low early in
  the bidding period.
- QIB and NII demand can be heavily back-loaded and may rise sharply on
  the final day.
- Treat subscription as a time-stamped snapshot, not final demand.

ANCHOR INVESTOR ANALYSIS:
- Use the supplied anchor amount, count, price, mutual-fund percentage,
  summary and named investors.
- Evaluate breadth, diversity and concentration from the supplied data.
- Consider domestic mutual fund participation when supplied.
- Do not treat a famous investor name as proof that an IPO is good.
- Do not invent or infer an investor's historical performance.

OTHER FACTORS:
- valuation: P/E, P/B and market cap when available;
- financial quality: ROE, ROCE, RoNW, PAT margin, debt/equity and
  promoter holding when available;
- fresh issue versus OFS;
- GMP and GMP trend, clearly marked unofficial;
- category subscription with timing;
- issue size, price band and lot size;
- supplied strengths and risks;
- business/sector quality only when supported by supplied application data.

SCORING:
- You have been provided with deterministic, rule-based scores (`deterministic_listing_score`, `deterministic_investment_score`, `deterministic_allotment_score`) in the payload.
- Do NOT output these exact scores independently. Instead, use them as your baseline.
- You must output an "AI-adjusted" score (0-100) for Investment and Allotment that factors in qualitative risks/strengths not captured by the math.
- In your `reason` field, you MUST explain your adjusted score relative to the deterministic score (e.g., "AI-adjusted Investment Score: 78. While the rule-based score was 82 based on financials, the heavy OFS component introduces risk...").
- Keep Investment Score and Allotment Score conceptually separate.
- Confidence reflects evidence completeness and reliability.
- Apply means attractive enough to consider applying, not guaranteed
  returns or allotment.

RESEARCH NOTES:
Because this is a free-tier, database-only AI system, research_notes must
describe only what can be verified from the supplied application data.
Do not claim that anything was checked online.

Return one recommendation for every IPO supplied.

IPO DATA:
{payload}
"""

    client = _get_client()
    try:
        response = _generate(client, prompt, structured=True)
        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")
        return json.loads(response.text)
    finally:
        client.close()

RECOMMENDATION_SCHEMA_V2 = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "company_name": {"type": "string"},
                    "ai_adjustment": {"type": "integer"},
                    "reason": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]},
                },
                "required": ["source_id", "company_name", "ai_adjustment", "reason", "confidence"]
            }
        }
    },
    "required": ["summary", "recommendations"]
}

def analyze_ipos_v2(ipos, objective="Balanced", risk_tolerance="Moderate", holding_horizon="Listing day"):
    if not ipos:
        raise ValueError("No IPO data was supplied for analysis.")

    payload = json.dumps(ipos, ensure_ascii=False, default=str)

    prompt = f"""
You are an AI narrator for an Indian IPO intelligence application. You have been provided with deterministic scores. 
Do not invent a new score. Your job is to explain WHY the deterministic score is what it is, and you may apply a maximum +/- 5 point 'AI Adjustment' based on qualitative anchor book data.

User objective: {objective}
Risk tolerance: {risk_tolerance}
Holding horizon: {holding_horizon}

IPO DATA:
{payload}
"""

    client = _get_client()
    try:
        response = _generate(client, prompt, structured=True, schema=RECOMMENDATION_SCHEMA_V2)
        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")
        return json.loads(response.text)
    finally:
        client.close()


def chat_with_advisor(
    message,
    analysis=None,
    ipos=None,
    objective="Balanced",
    risk_tolerance="Moderate",
    holding_horizon="Listing day",
):
    context = {
        "objective": objective,
        "risk_tolerance": risk_tolerance,
        "holding_horizon": holding_horizon,
        "analysis": analysis or {},
        "ipos": ipos or [],
    }

    prompt = f"""
You are the IPO Advisor inside an Indian IPO intelligence application.

Answer the user's question using ONLY the supplied application data and
previous analysis.

Rules:
- Do not use web search or external information.
- Do not invent facts.
- If the supplied data does not contain the answer, say it is not available.
- Keep investment attractiveness and allotment probability separate.
- GMP is unofficial and not guaranteed.
- Do not promise returns or allotment.
- Be concise and practical.
- If comparing IPOs, explain the key evidence from the supplied data.
- If a user asks about external consensus or Trendlyne, state you cannot see it.

CURRENT CONTEXT:
{json.dumps(context, ensure_ascii=False, default=str)}

USER QUESTION:
{message}
"""

    client = _get_client()
    try:
        response = _generate(client, prompt, structured=False)
        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")
        return response.text
    finally:
        client.close()

def hash_dataset(dataset):
    data_str = json.dumps(dataset, sort_keys=True, default=str)
    import hashlib
    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

def build_ai_dataset(frame):
    cols = [
        "source_id", "company_name", "segment", "display_status",
        "open_date", "close_date", "price_low", "price_high", "lot_size",
        "issue_size", "fresh_issue", "ofs_issue", "gmp", "gmp_pct",
        "indicative_listing", "subscription", "qib", "nii", "snii",
        "bnii", "retail", "applications", "listing_exchange",
        "anchor_amount", "anchor_count", "anchor_price", "anchor_mf_pct",
        "anchor_summary", "anchor_investors",
        "pre_issue_holding", "post_issue_holding", "pe_pre", "pe_post",
        "roe", "roce", "ronw", "pat_margin", "debt_equity", "price_book",
        "market_cap", "strengths", "risks",
    ]
    available = [c for c in cols if c in frame.columns]
    data = frame[available].copy()
    
    records = data.where(pd.notna(data), None).to_dict(orient="records")
    
    db = Database()
    try:
        for rec in records:
            sig = db.get_signal(str(rec["source_id"]))
            if sig:
                rec["deterministic_listing_score"] = sig.get("listing_score")
                rec["deterministic_investment_score"] = sig.get("investment_score")
                rec["deterministic_allotment_score"] = sig.get("allotment_score")
                rec["subscription_velocity_total"] = sig.get("subscription_velocity_total")
                rec["gmp_momentum_24h"] = sig.get("gmp_momentum_24h")
                rec["qvt_scorecard"] = sig.get("qvt_scorecard")
    finally:
        db.close()
        
    return records

def ai_score_for_ipo(row):
    if not get_gemini_api_key():
        st.error("AI is not configured yet. Add GEMINI_API_KEY to Streamlit secrets.")
        return
        
    source_id = str(row["source_id"])
    dataset = build_ai_dataset(pd.DataFrame([row]))
    data_hash = hash_dataset(dataset)
    
    db = Database()
    try:
        cached = db.get_ai_verdict(source_id)
        if cached and cached["data_hash"] == data_hash:
            st.session_state["ai_scores"][source_id] = json.loads(cached["recommendation_json"])
            return
    finally:
        db.close()

    try:
        with st.spinner("AI is reviewing this IPO..."):
            result = analyze_ipos_v2(
                dataset,
                objective="Balanced",
                risk_tolerance="Moderate",
                holding_horizon="Listing day",
            )
            print("--- SHADOW MODE V2 LOG ---")
            print(json.dumps(result, indent=2))
            
        recommendations = result.get("recommendations", [])
        if recommendations:
            rec = recommendations[0]
            adj = rec.get("ai_adjustment", 0)
            base_inv = dataset[0].get("deterministic_investment_score", 50)
            base_allot = dataset[0].get("deterministic_allotment_score", 50)
            
            # Map back to legacy schema for UI compatibility during shadow mode
            rec["investment_score"] = min(100, max(0, base_inv + adj))
            rec["allotment_score"] = min(100, max(0, base_allot + adj))
            rec["verdict"] = "Consider" # Placeholder since v2 dropped verdict
            
            st.session_state["ai_scores"][source_id] = rec
            db = Database()
            try:
                db.save_ai_verdict(source_id, data_hash, rec)
            finally:
                db.close()
    except Exception as exc:
        st.error(f"AI error: {exc}")
