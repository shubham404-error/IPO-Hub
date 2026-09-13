import json
import sqlite3
from pathlib import Path

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS ipos (
    ipo_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    company_name TEXT,
    symbol TEXT,
    ipo_type TEXT,
    segment TEXT,
    status TEXT,
    open_date TEXT,
    close_date TEXT,
    allotment_date TEXT,
    listing_date TEXT,
    listing_exchange TEXT,
    price_low REAL,
    price_high REAL,
    lot_size INTEGER,
    issue_size REAL,
    fresh_issue REAL,
    ofs_issue REAL,
    gmp REAL,
    gmp_pct REAL,
    indicative_listing REAL,
    gmp_updated_at TEXT,
    subscription REAL,
    qib REAL,
    nii REAL,
    snii REAL,
    bnii REAL,
    retail REAL,
    employee REAL,
    others REAL,
    applications INTEGER,
    subscription_updated_at TEXT,
    registrar TEXT,
    lead_managers TEXT,
    source_url TEXT,
    detail_url TEXT,
    subscription_url TEXT,
    gmp_url TEXT,
    anchor_amount REAL,
    anchor_count INTEGER,
    anchor_price REAL,
    anchor_mf_pct REAL,
    anchor_summary TEXT,
    anchor_investors TEXT,
    pre_issue_holding REAL,
    post_issue_holding REAL,
    pe_pre REAL,
    pe_post REAL,
    roe REAL,
    roce REAL,
    ronw REAL,
    pat_margin REAL,
    debt_equity REAL,
    price_book REAL,
    market_cap REAL,
    strengths TEXT,
    risks TEXT,
    collected_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    raw_json TEXT,
    UNIQUE(source, source_id)
);

CREATE TABLE IF NOT EXISTS subscription_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ipo_source TEXT NOT NULL,
    ipo_source_id TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    qib REAL,
    nii REAL,
    snii REAL,
    bnii REAL,
    retail REAL,
    employee REAL,
    others REAL,
    total REAL,
    applications INTEGER,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS gmp_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ipo_source TEXT NOT NULL,
    ipo_source_id TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    gmp REAL,
    gmp_pct REAL,
    indicative_listing REAL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS ipo_signals (
    source_id TEXT PRIMARY KEY,
    signal_version TEXT,
    subscription_velocity_total REAL,
    subscription_velocity_qib REAL,
    subscription_velocity_nii REAL,
    subscription_velocity_retail REAL,
    subscription_acceleration_total REAL,
    subscription_acceleration_qib REAL,
    subscription_acceleration_nii REAL,
    subscription_acceleration_retail REAL,
    gmp_momentum_24h REAL,
    anchor_quality_score INTEGER,
    valuation_score INTEGER,
    financial_quality_score INTEGER,
    listing_score INTEGER,
    investment_score INTEGER,
    allotment_score INTEGER,
    allotment_retail INTEGER,
    allotment_shni INTEGER,
    allotment_bhni INTEGER,
    signal_confidence TEXT,
    qvt_scorecard TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_verdicts (
    source_id TEXT PRIMARY KEY,
    data_hash TEXT NOT NULL,
    recommendation_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

MIGRATIONS = {
    "allotment_date": "TEXT",
    "listing_exchange": "TEXT",
    "fresh_issue": "REAL",
    "ofs_issue": "REAL",
    "gmp_pct": "REAL",
    "indicative_listing": "REAL",
    "gmp_updated_at": "TEXT",
    "qib": "REAL",
    "nii": "REAL",
    "snii": "REAL",
    "bnii": "REAL",
    "retail": "REAL",
    "employee": "REAL",
    "others": "REAL",
    "applications": "INTEGER",
    "subscription_updated_at": "TEXT",
    "registrar": "TEXT",
    "lead_managers": "TEXT",
    "detail_url": "TEXT",
    "subscription_url": "TEXT",
    "gmp_url": "TEXT",
    "anchor_amount": "REAL",
    "anchor_count": "INTEGER",
    "anchor_price": "REAL",
    "anchor_mf_pct": "REAL",
    "anchor_summary": "TEXT",
    "anchor_investors": "TEXT",
    "pre_issue_holding": "REAL",
    "post_issue_holding": "REAL",
    "pe_pre": "REAL",
    "pe_post": "REAL",
    "roe": "REAL",
    "roce": "REAL",
    "ronw": "REAL",
    "pat_margin": "REAL",
    "debt_equity": "REAL",
    "price_book": "REAL",
    "market_cap": "REAL",
    "strengths": "TEXT",
    "risks": "TEXT",
}

class Database:
    def __init__(self, path=DB_PATH):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._migrate()
        self.conn.commit()

    def _migrate(self):
        existing = {
            row[1] for row in self.conn.execute("PRAGMA table_info(ipos)")
        }
        for name, sql_type in MIGRATIONS.items():
            if name not in existing:
                self.conn.execute(
                    f"ALTER TABLE ipos ADD COLUMN {name} {sql_type}"
                )
        
        # Migrate ipo_signals table for qvt_scorecard
        existing_signals = {
            row[1] for row in self.conn.execute("PRAGMA table_info(ipo_signals)")
        }
        if "qvt_scorecard" not in existing_signals:
            self.conn.execute("ALTER TABLE ipo_signals ADD COLUMN qvt_scorecard TEXT")

    def upsert_ipos(self, rows):
        query = """
        INSERT INTO ipos (
            source, source_id, company_name, symbol, ipo_type, segment, status,
            open_date, close_date, allotment_date, listing_date, listing_exchange,
            price_low, price_high, lot_size, issue_size, fresh_issue, ofs_issue,
            gmp, gmp_pct, indicative_listing, gmp_updated_at,
            subscription, qib, nii, snii, bnii, retail, employee, others,
            applications, subscription_updated_at, registrar, lead_managers,
            source_url, detail_url, subscription_url, gmp_url,
            anchor_amount, anchor_count, anchor_price, anchor_mf_pct, anchor_summary,
            anchor_investors, pre_issue_holding, post_issue_holding, pe_pre, pe_post,
            roe, roce, ronw, pat_margin, debt_equity, price_book, market_cap, strengths, risks,
            collected_at, updated_at, raw_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(source, source_id) DO UPDATE SET
            company_name=excluded.company_name,
            symbol=excluded.symbol,
            ipo_type=excluded.ipo_type,
            segment=excluded.segment,
            status=excluded.status,
            open_date=excluded.open_date,
            close_date=excluded.close_date,
            allotment_date=excluded.allotment_date,
            listing_date=excluded.listing_date,
            listing_exchange=excluded.listing_exchange,
            price_low=excluded.price_low,
            price_high=excluded.price_high,
            lot_size=excluded.lot_size,
            issue_size=excluded.issue_size,
            fresh_issue=excluded.fresh_issue,
            ofs_issue=excluded.ofs_issue,
            gmp=excluded.gmp,
            gmp_pct=excluded.gmp_pct,
            indicative_listing=excluded.indicative_listing,
            gmp_updated_at=excluded.gmp_updated_at,
            subscription=excluded.subscription,
            qib=excluded.qib,
            nii=excluded.nii,
            snii=excluded.snii,
            bnii=excluded.bnii,
            retail=excluded.retail,
            employee=excluded.employee,
            others=excluded.others,
            applications=excluded.applications,
            subscription_updated_at=excluded.subscription_updated_at,
            registrar=excluded.registrar,
            lead_managers=excluded.lead_managers,
            source_url=excluded.source_url,
            detail_url=excluded.detail_url,
            anchor_amount=excluded.anchor_amount,
            anchor_count=excluded.anchor_count,
            anchor_price=excluded.anchor_price,
            anchor_mf_pct=excluded.anchor_mf_pct,
            anchor_summary=excluded.anchor_summary,
            anchor_investors=excluded.anchor_investors,
            pre_issue_holding=excluded.pre_issue_holding,
            post_issue_holding=excluded.post_issue_holding,
            pe_pre=excluded.pe_pre,
            pe_post=excluded.pe_post,
            roe=excluded.roe,
            roce=excluded.roce,
            ronw=excluded.ronw,
            pat_margin=excluded.pat_margin,
            debt_equity=excluded.debt_equity,
            price_book=excluded.price_book,
            market_cap=excluded.market_cap,
            strengths=excluded.strengths,
            risks=excluded.risks,
            subscription_url=excluded.subscription_url,
            gmp_url=excluded.gmp_url,
            updated_at=excluded.updated_at,
            raw_json=excluded.raw_json
        """

        for r in rows:
            values = (
                r.get("source"), r.get("source_id"), r.get("company_name"),
                r.get("symbol"), r.get("ipo_type"), r.get("segment"), r.get("status"),
                r.get("open_date"), r.get("close_date"), r.get("allotment_date"),
                r.get("listing_date"), r.get("listing_exchange"), r.get("price_low"),
                r.get("price_high"), r.get("lot_size"), r.get("issue_size"),
                r.get("fresh_issue"), r.get("ofs_issue"), r.get("gmp"),
                r.get("gmp_pct"), r.get("indicative_listing"), r.get("gmp_updated_at"),
                r.get("subscription"), r.get("qib"), r.get("nii"), r.get("snii"),
                r.get("bnii"), r.get("retail"), r.get("employee"), r.get("others"),
                r.get("applications"), r.get("subscription_updated_at"),
                r.get("registrar"), r.get("lead_managers"), r.get("source_url"),
                r.get("detail_url"), r.get("subscription_url"), r.get("gmp_url"),
                r.get("anchor_amount"), r.get("anchor_count"), r.get("anchor_price"),
                r.get("anchor_mf_pct"), r.get("anchor_summary"), r.get("anchor_investors"),
                r.get("pre_issue_holding"), r.get("post_issue_holding"), r.get("pe_pre"), r.get("pe_post"),
                r.get("roe"), r.get("roce"), r.get("ronw"), r.get("pat_margin"), r.get("debt_equity"),
                r.get("price_book"), r.get("market_cap"), r.get("strengths"), r.get("risks"),
                r.get("collected_at"), r.get("collected_at"),
                json.dumps(r.get("raw", {}), default=str),
            )
            self.conn.execute(query, values)
        self.conn.commit()
        return len(rows)

    def add_subscription_snapshot(self, source, source_id, data, captured_at):
        self.conn.execute(
            """INSERT INTO subscription_snapshots
            (ipo_source, ipo_source_id, captured_at, qib, nii, snii, bnii,
             retail, employee, others, total, applications, raw_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                source, source_id, captured_at, data.get("qib"), data.get("nii"),
                data.get("snii"), data.get("bnii"), data.get("retail"),
                data.get("employee"), data.get("others"), data.get("total"),
                data.get("applications"), json.dumps(data.get("raw", {}), default=str),
            ),
        )
        self.conn.commit()

    def add_gmp_snapshot(self, source, source_id, data, captured_at):
        self.conn.execute(
            """INSERT INTO gmp_snapshots
            (ipo_source, ipo_source_id, captured_at, gmp, gmp_pct,
             indicative_listing, raw_json)
            VALUES (?,?,?,?,?,?,?)""",
            (
                source, source_id, captured_at, data.get("gmp"),
                data.get("gmp_pct"), data.get("indicative_listing"),
                json.dumps(data.get("raw", {}), default=str),
            ),
        )
        self.conn.commit()

    def get_ipos(self):
        return self.conn.execute(
            "SELECT * FROM ipos ORDER BY close_date, company_name"
        ).fetchall()

    def get_ipo(self, source_id):
        return self.conn.execute(
            "SELECT * FROM ipos WHERE source='ipoji' AND source_id=?",
            (source_id,),
        ).fetchone()

    def get_subscription_history(self, source_id):
        return self.conn.execute(
            """SELECT * FROM subscription_snapshots
               WHERE ipo_source='ipoji' AND ipo_source_id=?
               ORDER BY captured_at""",
            (source_id,),
        ).fetchall()

    def get_gmp_history(self, source_id):
        return self.conn.execute(
            """SELECT * FROM gmp_snapshots
               WHERE ipo_source='ipoji' AND ipo_source_id=?
               ORDER BY captured_at""",
            (source_id,),
        ).fetchall()

    def get_ai_verdict(self, source_id):
        row = self.conn.execute("SELECT * FROM ai_verdicts WHERE source_id=?", (source_id,)).fetchone()
        return dict(row) if row else None

    def save_ai_verdict(self, source_id, data_hash, recommendation):
        self.conn.execute("""
            INSERT INTO ai_verdicts (source_id, data_hash, recommendation_json, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(source_id) DO UPDATE SET
                data_hash=excluded.data_hash,
                recommendation_json=excluded.recommendation_json,
                updated_at=excluded.updated_at
        """, (source_id, data_hash, json.dumps(recommendation)))
        self.conn.commit()

    def get_signal(self, source_id):
        row = self.conn.execute("SELECT * FROM ipo_signals WHERE source_id=?", (source_id,)).fetchone()
        return dict(row) if row else None

    def upsert_signal(self, source_id, data):
        self.conn.execute("""
            INSERT INTO ipo_signals (
                source_id, signal_version, 
                subscription_velocity_total, subscription_velocity_qib,
                subscription_velocity_nii, subscription_velocity_retail,
                subscription_acceleration_total, subscription_acceleration_qib,
                subscription_acceleration_nii, subscription_acceleration_retail,
                gmp_momentum_24h, anchor_quality_score, valuation_score,
                financial_quality_score, listing_score, investment_score,
                allotment_score, allotment_retail, allotment_shni, allotment_bhni,
                signal_confidence, qvt_scorecard, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(source_id) DO UPDATE SET
                signal_version=excluded.signal_version,
                subscription_velocity_total=excluded.subscription_velocity_total,
                subscription_velocity_qib=excluded.subscription_velocity_qib,
                subscription_velocity_nii=excluded.subscription_velocity_nii,
                subscription_velocity_retail=excluded.subscription_velocity_retail,
                subscription_acceleration_total=excluded.subscription_acceleration_total,
                subscription_acceleration_qib=excluded.subscription_acceleration_qib,
                subscription_acceleration_nii=excluded.subscription_acceleration_nii,
                subscription_acceleration_retail=excluded.subscription_acceleration_retail,
                gmp_momentum_24h=excluded.gmp_momentum_24h,
                anchor_quality_score=excluded.anchor_quality_score,
                valuation_score=excluded.valuation_score,
                financial_quality_score=excluded.financial_quality_score,
                listing_score=excluded.listing_score,
                investment_score=excluded.investment_score,
                allotment_score=excluded.allotment_score,
                allotment_retail=excluded.allotment_retail,
                allotment_shni=excluded.allotment_shni,
                allotment_bhni=excluded.allotment_bhni,
                signal_confidence=excluded.signal_confidence,
                qvt_scorecard=excluded.qvt_scorecard,
                updated_at=excluded.updated_at
        """, (
            source_id, data.get("signal_version", "v1.1"),
            data.get("subscription_velocity_total"), data.get("subscription_velocity_qib"),
            data.get("subscription_velocity_nii"), data.get("subscription_velocity_retail"),
            data.get("subscription_acceleration_total"), data.get("subscription_acceleration_qib"),
            data.get("subscription_acceleration_nii"), data.get("subscription_acceleration_retail"),
            data.get("gmp_momentum_24h"), data.get("anchor_quality_score"), data.get("valuation_score"),
            data.get("financial_quality_score"), data.get("listing_score"), data.get("investment_score"),
            data.get("allotment_score"), data.get("allotment_retail"), data.get("allotment_shni"),
            data.get("allotment_bhni"), data.get("signal_confidence"), data.get("qvt_scorecard")
        ))
        self.conn.commit()

    def close(self):
        self.conn.close()
def get_df():
    import pandas as pd
    import sqlite3
    from config import DB_PATH
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM ipos", conn)


def get_selected_ipo(source_id):
    db = Database()
    try:
        row = db.get_ipo(source_id)
        sub_history = db.get_subscription_history(source_id)
        gmp_history = db.get_gmp_history(source_id)
        return dict(row) if row else None, [dict(x) for x in sub_history], [dict(x) for x in gmp_history]
    finally:
        db.close()
