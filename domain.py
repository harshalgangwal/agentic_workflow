"""
models/domain.py
Pydantic domain models for claims, documents, decisions, agents.
These are the canonical data contracts across the entire pipeline.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────
# Enums
# ─────────────────────────────────────────

class ClaimCategory(str, Enum):
    CONSULTATION = "CONSULTATION"
    DIAGNOSTIC = "DIAGNOSTIC"
    PHARMACY = "PHARMACY"
    DENTAL = "DENTAL"
    VISION = "VISION"
    ALTERNATIVE_MEDICINE = "ALTERNATIVE_MEDICINE"


class DocumentType(str, Enum):
    PRESCRIPTION = "PRESCRIPTION"
    HOSPITAL_BILL = "HOSPITAL_BILL"
    PHARMACY_BILL = "PHARMACY_BILL"
    LAB_REPORT = "LAB_REPORT"
    DIAGNOSTIC_REPORT = "DIAGNOSTIC_REPORT"
    DENTAL_REPORT = "DENTAL_REPORT"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    UNKNOWN = "UNKNOWN"


class DocumentQuality(str, Enum):
    GOOD = "GOOD"
    POOR = "POOR"
    UNREADABLE = "UNREADABLE"


class DecisionStatus(str, Enum):
    APPROVED = "APPROVED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    PENDING_DOCUMENTS = "PENDING_DOCUMENTS"


class CheckStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"


class RejectionReason(str, Enum):
    WAITING_PERIOD = "WAITING_PERIOD"
    EXCLUDED_CONDITION = "EXCLUDED_CONDITION"
    PER_CLAIM_EXCEEDED = "PER_CLAIM_EXCEEDED"
    ANNUAL_LIMIT_EXCEEDED = "ANNUAL_LIMIT_EXCEEDED"
    SUB_LIMIT_EXCEEDED = "SUB_LIMIT_EXCEEDED"
    PRE_AUTH_REQUIRED = "PRE_AUTH_REQUIRED"
    MEMBER_NOT_FOUND = "MEMBER_NOT_FOUND"
    POLICY_INACTIVE = "POLICY_INACTIVE"
    DOCUMENT_MISMATCH = "DOCUMENT_MISMATCH"
    PATIENT_MISMATCH = "PATIENT_MISMATCH"
    FRAUD_FLAG = "FRAUD_FLAG"
    WRONG_DOCUMENT_TYPE = "WRONG_DOCUMENT_TYPE"
    UNREADABLE_DOCUMENT = "UNREADABLE_DOCUMENT"
    NOT_COVERED = "NOT_COVERED"


# ─────────────────────────────────────────
# Document Models
# ─────────────────────────────────────────

class LineItem(BaseModel):
    description: str
    amount: float
    covered: Optional[bool] = None
    rejection_reason: Optional[str] = None
    approved_amount: Optional[float] = None


class ExtractedDocumentContent(BaseModel):
    doctor_name: Optional[str] = None
    doctor_registration: Optional[str] = None
    doctor_specialization: Optional[str] = None
    patient_name: Optional[str] = None
    patient_age: Optional[str] = None
    patient_gender: Optional[str] = None
    hospital_name: Optional[str] = None
    hospital_address: Optional[str] = None
    date: Optional[str] = None
    diagnosis: Optional[str] = None
    diagnosis_codes: list[str] = Field(default_factory=list)
    medicines: list[str] = Field(default_factory=list)
    tests_ordered: list[str] = Field(default_factory=list)
    line_items: list[LineItem] = Field(default_factory=list)
    total_amount: Optional[float] = None
    bill_number: Optional[str] = None
    lab_name: Optional[str] = None
    nabl_accredited: Optional[bool] = None
    treatment: Optional[str] = None
    procedures: list[str] = Field(default_factory=list)
    raw_text: Optional[str] = None
    extraction_confidence: float = 0.5


class DocumentSubmission(BaseModel):
    file_id: str
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    actual_type: Optional[DocumentType] = None
    declared_type: Optional[DocumentType] = None
    quality: Optional[DocumentQuality] = None
    content: Optional[dict[str, Any]] = None  # Pre-filled content for test cases
    extracted_content: Optional[ExtractedDocumentContent] = None
    ocr_confidence: float = 1.0
    is_readable: bool = True
    patient_name_on_doc: Optional[str] = None


# ─────────────────────────────────────────
# Claim Input
# ─────────────────────────────────────────

class ClaimsHistory(BaseModel):
    claim_id: str
    date: str
    amount: float
    provider: Optional[str] = None


class ClaimInput(BaseModel):
    claim_id: str = Field(default_factory=lambda: f"CLM_{uuid.uuid4().hex[:8].upper()}")
    member_id: str
    policy_id: str
    claim_category: ClaimCategory
    treatment_date: date
    claimed_amount: float
    hospital_name: Optional[str] = None
    ytd_claims_amount: float = 0.0
    claims_history: list[ClaimsHistory] = Field(default_factory=list)
    documents: list[DocumentSubmission] = Field(default_factory=list)
    simulate_component_failure: bool = False
    submitted_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("treatment_date", mode="before")
    @classmethod
    def parse_treatment_date(cls, v):
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v


# ─────────────────────────────────────────
# Policy Models
# ─────────────────────────────────────────

class Member(BaseModel):
    member_id: str
    name: str
    date_of_birth: date
    gender: str
    relationship: str
    join_date: date
    dependents: list[str] = Field(default_factory=list)
    primary_member_id: Optional[str] = None

    @field_validator("date_of_birth", "join_date", mode="before")
    @classmethod
    def parse_dates(cls, v):
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v


class PolicyConfig(BaseModel):
    policy_id: str
    policy_name: str
    insurer: str
    policy_holder: dict[str, Any]
    coverage: dict[str, Any]
    opd_categories: dict[str, Any]
    waiting_periods: dict[str, Any]
    exclusions: dict[str, Any]
    pre_authorization: dict[str, Any]
    network_hospitals: list[str]
    submission_rules: dict[str, Any]
    document_requirements: dict[str, Any]
    fraud_thresholds: dict[str, Any]
    members: list[Member]

    def get_member(self, member_id: str) -> Optional[Member]:
        for m in self.members:
            if m.member_id == member_id:
                return m
        return None

    def get_category_config(self, category: ClaimCategory) -> Optional[dict]:
        return self.opd_categories.get(category.value.lower())

    def is_network_hospital(self, hospital_name: str) -> bool:
        if not hospital_name:
            return False
        hospital_lower = hospital_name.lower()
        for nh in self.network_hospitals:
            if nh.lower() in hospital_lower or hospital_lower in nh.lower():
                return True
        return False


# ─────────────────────────────────────────
# Check & Decision Models
# ─────────────────────────────────────────

class CheckResult(BaseModel):
    check_name: str
    status: CheckStatus
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    confidence_impact: float = 0.0  # negative = reduces confidence


class DocumentVerificationResult(BaseModel):
    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_document_types: list[DocumentType] = Field(default_factory=list)
    wrong_documents: list[dict[str, Any]] = Field(default_factory=list)
    unreadable_documents: list[str] = Field(default_factory=list)
    patient_mismatches: list[dict[str, Any]] = Field(default_factory=list)
    user_message: Optional[str] = None


class FraudSignal(BaseModel):
    signal_type: str
    description: str
    severity: str  # LOW, MEDIUM, HIGH
    evidence: dict[str, Any] = Field(default_factory=dict)


class FinancialCalculation(BaseModel):
    claimed_amount: float
    network_discount_applied: bool = False
    network_discount_amount: float = 0.0
    amount_after_network_discount: float = 0.0
    copay_percent: float = 0.0
    copay_amount: float = 0.0
    sub_limit_cap: Optional[float] = None
    per_claim_cap: Optional[float] = None
    approved_amount: float = 0.0
    calculation_breakdown: list[str] = Field(default_factory=list)
    line_item_decisions: list[LineItem] = Field(default_factory=list)


class ClaimDecision(BaseModel):
    claim_id: str
    decision: DecisionStatus
    approved_amount: float = 0.0
    confidence_score: float = 0.0
    rejection_reasons: list[RejectionReason] = Field(default_factory=list)
    reasoning: str = ""
    checks_performed: list[CheckResult] = Field(default_factory=list)
    rule_trace: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    fraud_signals: list[FraudSignal] = Field(default_factory=list)
    financial_calculation: Optional[FinancialCalculation] = None
    component_failures: list[str] = Field(default_factory=list)
    manual_review_recommended: bool = False
    manual_review_reasons: list[str] = Field(default_factory=list)
    line_item_decisions: list[LineItem] = Field(default_factory=list)
    eligibility_date: Optional[date] = None
    decided_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────
# Pipeline State (LangGraph)
# ─────────────────────────────────────────

class PipelineState(BaseModel):
    """State that flows through the LangGraph pipeline."""
    claim_input: ClaimInput
    policy: Optional[PolicyConfig] = None
    member: Optional[Member] = None
    document_verification: Optional[DocumentVerificationResult] = None
    extracted_documents: list[DocumentSubmission] = Field(default_factory=list)
    checks: list[CheckResult] = Field(default_factory=list)
    fraud_signals: list[FraudSignal] = Field(default_factory=list)
    financial_calculation: Optional[FinancialCalculation] = None
    decision: Optional[ClaimDecision] = None
    component_failures: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)
    pipeline_complete: bool = False
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
