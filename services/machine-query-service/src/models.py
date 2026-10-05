"""
SQLAlchemy models for machine-query-service.
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint, JSON, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MachineModel(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(String(255), nullable=False)
    box_id = Column(String(255), nullable=False)
    tenant_id = Column(String(255), nullable=False)
    name = Column(String(255))
    endpoint_url = Column(Text)
    metadata_json = Column(JSON, name="metadata")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("machine_id", "box_id", name="unique_machine_per_box"),
    )