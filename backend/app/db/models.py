"""SQLAlchemy models for SCAMTRACE AI."""
import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Case(Base):
    __tablename__ = "cases"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    status = Column(String(32), default="open", nullable=False)  # open, closed
    notes = Column(Text, nullable=True)

    evidence_items = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="case", cascade="all, delete-orphan")
    edges = relationship("Edge", back_populates="case", cascade="all, delete-orphan")
    audit_entries = relationship("AuditEntry", back_populates="case", cascade="all, delete-orphan", order_by="AuditEntry.seq")


class Evidence(Base):
    __tablename__ = "evidence"

    # Composite primary key: evidence ID is unique within each case (e.g. E1, E2)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True, index=True)
    id = Column(String(64), primary_key=True, index=True)

    type = Column(String(32), nullable=False)  # sms, chat, url, apk, screenshot, email_text
    original_filename = Column(String(255), nullable=True)
    mime_type = Column(String(128), default="application/octet-stream", nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    stored_path = Column(String(512), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    source_timestamp = Column(DateTime, nullable=True)
    timestamp_source = Column(String(32), default="none", nullable=False)  # embedded, user_entered, none
    uploader = Column(String(128), default="investigator", nullable=False)
    raw_text = Column(Text, nullable=True)
    analysis_status = Column(String(32), default="pending", nullable=False)  # pending, analyzed, failed
    type_conflict = Column(String(255), nullable=True)

    case = relationship("Case", back_populates="evidence_items")
    entities = relationship("Entity", back_populates="evidence", cascade="all, delete-orphan", overlaps="entities,case")
    analyses = relationship("Analysis", back_populates="evidence", cascade="all, delete-orphan", overlaps="analyses,case")


class Entity(Base):
    __tablename__ = "entities"

    id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(32), nullable=False)  # phone, url, domain, upi_handle, apk_package, cert_sha256, amount, datetime, brand, sender_id
    value = Column(String(512), nullable=False, index=True)  # normalized value
    raw_value = Column(String(512), nullable=False)
    span_start = Column(Integer, nullable=True)
    span_end = Column(Integer, nullable=True)

    case = relationship("Case", back_populates="entities", overlaps="entities,evidence")
    evidence = relationship("Evidence", back_populates="entities", overlaps="entities,case")

    __table_args__ = (
        ForeignKeyConstraint(["case_id", "evidence_id"], ["evidence.case_id", "evidence.id"], ondelete="CASCADE"),
    )


class Edge(Base):
    __tablename__ = "edges"

    id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    source_evidence_id = Column(String(64), nullable=False, index=True)
    target_evidence_id = Column(String(64), nullable=False, index=True)
    link_type = Column(String(64), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    supporting_fields = Column(Text, nullable=False)  # JSON string
    rule_version = Column(String(32), default="1.0", nullable=False)

    case = relationship("Case", back_populates="edges")

    __table_args__ = (
        UniqueConstraint("case_id", "source_evidence_id", "target_evidence_id", "link_type", name="uq_edge_case_src_tgt_type"),
    )


class AuditEntry(Base):
    __tablename__ = "audit_entries"

    id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    seq = Column(Integer, nullable=False)
    timestamp_utc = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    actor = Column(String(128), default="investigator", nullable=False)
    action = Column(String(64), nullable=False)  # ingest, analyze, edit_note, correlate, generate_report, verify
    payload_json = Column(Text, nullable=False)  # canonical JSON
    prev_hash = Column(String(64), nullable=False)
    entry_hash = Column(String(64), nullable=False)

    case = relationship("Case", back_populates="audit_entries")

    __table_args__ = (
        UniqueConstraint("case_id", "seq", name="uq_audit_case_seq"),
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), nullable=False, index=True)
    evidence_id = Column(String(64), nullable=False, index=True)
    model_name = Column(String(64), nullable=False)
    model_version = Column(String(32), nullable=False)
    label = Column(String(32), nullable=False)  # benign, suspicious
    score = Column(Float, nullable=False)
    top_factors = Column(Text, nullable=False)  # JSON string
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    evidence = relationship("Evidence", back_populates="analyses", overlaps="analyses,case")

    __table_args__ = (
        ForeignKeyConstraint(["case_id", "evidence_id"], ["evidence.case_id", "evidence.id"], ondelete="CASCADE"),
    )
