from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MachineStateModel(Base):
    __tablename__ = "machine_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    error_code = Column(String(50))
    time = Column(DateTime(timezone=True), nullable=False)