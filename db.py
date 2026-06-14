"""
database/db.py
SQLite database layer using SQLAlchemy.
Stores claims, decisions, audit trails, and member usage.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    create_engine, Column, String, Float, Boolean,
    DateTime, Text, Integer, JSON, Index
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import DB_PATH
from utils.logger import logger


class Base(DeclarativeBase):
    pass


class ClaimRecord(Base):
    __tablename__ = "claims"

    claim_id = Column(String, primary_key=True)
    member_id = Column(String, nullable=False, index=True)
    policy_id = Column(String, nullable=False)
    claim_category = Column(String, nullable=False)
    treatment_date = Column(String, nullable=False)
    claimed_amount = Column(Float, nullable=False)
    approved_amount = Column(Float, default=0.0)
    decision = Column(String, nullable=True)
    confidence_score = Column(Float, default=0.0)
    reasoning = Column(Text, nullable=True)
    rejection_reasons = Column(JSON, default=list)
    rule_trace = Column(JSON, default=list)
    checks_performed = Column(JSON, default=list)
    fraud_signals = Column(JSON, default=list)
    warnings = Column(JSON, default=list)
    component_failures = Column(JSON, default=list)
    financial_calculation = Column(JSON, nullable=True)
    line_item_decisions = Column(JSON, default=list)
    manual_review_recommended = Column(Boolean, default=False)
    full_state = Column(JSON, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_member_treatment_date", "member_id", "treatment_date"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    agent_name = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MemberUsage(Base):
    __tablename__ = "member_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(String, nullable=False, index=True)
    policy_year = Column(String, nullable=False)
    ytd_approved_amount = Column(Float, default=0.0)
    claims_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)


def get_engine():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    return engine


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info(f"Database initialized at {DB_PATH}")
    return engine


_engine = None
_SessionLocal = None


def get_session() -> Session:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = init_db()
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _SessionLocal()


class ClaimsRepository:
    """Repository pattern for claim persistence."""

    def save_claim(self, claim_id: str, claim_input: dict, decision: dict) -> None:
        with get_session() as session:
            existing = session.get(ClaimRecord, claim_id)
            if existing:
                record = existing
            else:
                record = ClaimRecord(claim_id=claim_id)
                session.add(record)

            record.member_id = claim_input.get("member_id", "")
            record.policy_id = claim_input.get("policy_id", "")
            record.claim_category = claim_input.get("claim_category", "")
            record.treatment_date = str(claim_input.get("treatment_date", ""))
            record.claimed_amount = claim_input.get("claimed_amount", 0)
            record.decision = decision.get("decision")
            record.approved_amount = decision.get("approved_amount", 0)
            record.confidence_score = decision.get("confidence_score", 0)
            record.reasoning = decision.get("reasoning", "")
            record.rejection_reasons = decision.get("rejection_reasons", [])
            record.rule_trace = decision.get("rule_trace", [])
            record.checks_performed = decision.get("checks_performed", [])
            record.fraud_signals = decision.get("fraud_signals", [])
            record.warnings = decision.get("warnings", [])
            record.component_failures = decision.get("component_failures", [])
            record.financial_calculation = decision.get("financial_calculation")
            record.line_item_decisions = decision.get("line_item_decisions", [])
            record.manual_review_recommended = decision.get("manual_review_recommended", False)
            record.full_state = decision
            record.decided_at = datetime.utcnow()
            session.commit()
            logger.info(f"Saved claim {claim_id} with decision {decision.get('decision')}")

    def get_same_day_claims(self, member_id: str, date_str: str) -> list[dict]:
        with get_session() as session:
            records = session.query(ClaimRecord).filter(
                ClaimRecord.member_id == member_id,
                ClaimRecord.treatment_date == date_str
            ).all()
            return [{"claim_id": r.claim_id, "amount": r.claimed_amount} for r in records]

    def get_monthly_claims(self, member_id: str, year_month: str) -> list[dict]:
        with get_session() as session:
            records = session.query(ClaimRecord).filter(
                ClaimRecord.member_id == member_id,
                ClaimRecord.treatment_date.startswith(year_month)
            ).all()
            return [{"claim_id": r.claim_id, "amount": r.claimed_amount} for r in records]

    def get_claim(self, claim_id: str) -> Optional[dict]:
        with get_session() as session:
            record = session.get(ClaimRecord, claim_id)
            if not record:
                return None
            return {
                "claim_id": record.claim_id,
                "member_id": record.member_id,
                "decision": record.decision,
                "approved_amount": record.approved_amount,
                "confidence_score": record.confidence_score,
                "reasoning": record.reasoning,
                "full_state": record.full_state,
            }

    def log_audit_event(self, claim_id: str, event_type: str, agent_name: str, message: str, details: dict = None):
        with get_session() as session:
            entry = AuditLog(
                claim_id=claim_id,
                event_type=event_type,
                agent_name=agent_name,
                message=message,
                details=details or {},
            )
            session.add(entry)
            session.commit()

    def get_audit_trail(self, claim_id: str) -> list[dict]:
        with get_session() as session:
            entries = session.query(AuditLog).filter(
                AuditLog.claim_id == claim_id
            ).order_by(AuditLog.created_at).all()
            return [
                {
                    "event_type": e.event_type,
                    "agent_name": e.agent_name,
                    "message": e.message,
                    "details": e.details,
                    "created_at": str(e.created_at),
                }
                for e in entries
            ]

    def list_claims(self, limit: int = 50) -> list[dict]:
        with get_session() as session:
            records = session.query(ClaimRecord).order_by(
                ClaimRecord.submitted_at.desc()
            ).limit(limit).all()
            return [
                {
                    "claim_id": r.claim_id,
                    "member_id": r.member_id,
                    "claim_category": r.claim_category,
                    "claimed_amount": r.claimed_amount,
                    "approved_amount": r.approved_amount,
                    "decision": r.decision,
                    "confidence_score": r.confidence_score,
                    "submitted_at": str(r.submitted_at),
                }
                for r in records
            ]


# Singleton repository
claims_repo = ClaimsRepository()
