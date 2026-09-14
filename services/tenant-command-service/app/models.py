"""
SQLAlchemy ORM model for the tenant registry - system-postgres.

No migration framework (Alembic) is used by deliberate choice. Since this
is early-stage development with no data worth preserving, schema changes
are handled by resetting the database (docker compose down -v) and letting
Base.metadata.create_all() rebuild it from scratch - not by altering
existing tables in place.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    postgres_host: Mapped[str] = mapped_column(String)
    postgres_port: Mapped[int] = mapped_column(Integer)
    postgres_user: Mapped[str] = mapped_column(String)
    postgres_password: Mapped[str] = mapped_column(String)
    postgres_db: Mapped[str] = mapped_column(String)

    redis_host: Mapped[str] = mapped_column(String)
    redis_port: Mapped[int] = mapped_column(Integer)

    rabbitmq_vhost: Mapped[str] = mapped_column(String)
    rabbitmq_user: Mapped[str] = mapped_column(String)
    rabbitmq_password: Mapped[str] = mapped_column(String)