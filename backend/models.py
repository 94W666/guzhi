"""SQLAlchemy ORM models for fund tracking."""

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, ForeignKey, Text, create_engine, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Fund(Base):
    __tablename__ = "funds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    fund_type = Column(String(50), default="OTHER")
    tracking_index = Column(String(100), default="")
    scale = Column(Float, default=0.0)  # fund scale in 亿元
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    holdings = relationship("Holding", back_populates="fund", cascade="all, delete-orphan")
    nav_estimates = relationship("NavEstimate", back_populates="fund", cascade="all, delete-orphan")
    nav_history = relationship("FundNav", back_populates="fund", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Fund(code={self.code}, name={self.name})>"


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_id = Column(Integer, ForeignKey("funds.id"), nullable=False)
    stock_code = Column(String(20), nullable=False)
    stock_name = Column(String(100), default="")
    weight = Column(Float, default=0.0)  # percentage weight in portfolio
    report_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    fund = relationship("Fund", back_populates="holdings")

    def __repr__(self):
        return f"<Holding(fund_id={self.fund_id}, stock={self.stock_code}, weight={self.weight})>"


class NavEstimate(Base):
    __tablename__ = "nav_estimates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_id = Column(Integer, ForeignKey("funds.id"), nullable=False)
    official_nav = Column(Float, default=0.0)
    estimated_nav = Column(Float, default=0.0)
    nav_date = Column(Date, nullable=False)
    realtime_nav = Column(Float, default=0.0)  # real-time estimated NAV during market hours
    last_stock_update = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    fund = relationship("Fund", back_populates="nav_estimates")

    def __repr__(self):
        return f"<NavEstimate(fund_id={self.fund_id}, date={self.nav_date}, est={self.estimated_nav})>"


class FundNav(Base):
    """Historical NAV data for a fund."""

    __tablename__ = "fund_nav"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_id = Column(Integer, ForeignKey("funds.id"), nullable=False)
    nav_date = Column(Date, nullable=False)
    unit_nav = Column(Float, default=0.0)
    cumulative_nav = Column(Float, default=0.0)
    daily_return = Column(Float, default=0.0)  # (nav_t / nav_{t-1}) - 1

    fund = relationship("Fund", back_populates="nav_history")

    __table_args__ = (
        Index("ix_fund_nav_fund_date", "fund_id", "nav_date"),
    )

    def __repr__(self):
        return f"<FundNav(fund_id={self.fund_id}, date={self.nav_date}, unit={self.unit_nav})>"
