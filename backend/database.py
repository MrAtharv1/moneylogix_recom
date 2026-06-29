"""
database.py — SQLite database setup and CRUD operations.
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import logging

# Ensure fallback for settings to prevent crash if not implemented yet
try:
    from config import settings
    DB_URL = settings.DATABASE_URL
except ImportError:
    DB_URL = "sqlite:///./moneylogix.db"

logger = logging.getLogger(__name__)

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class StrategySnapshot(Base):
    __tablename__ = "strategy_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String, unique=True, index=True, nullable=False)
    symbol = Column(String, nullable=False)
    strategy_type = Column(String, nullable=False)
    legs_json = Column(Text, nullable=False)          
    entry_metrics_json = Column(Text, nullable=False) 
    entry_spot = Column(Float, nullable=False)
    entry_iv = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class HealthLog(Base):
    __tablename__ = "health_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String, index=True, nullable=False)
    diff_json = Column(Text, nullable=False)
    explanation = Column(Text, default="")
    logged_at = Column(DateTime, default=datetime.utcnow)

def create_tables() -> None:
    """Call this on app startup."""
    Base.metadata.create_all(bind=engine)

def save_snapshot(strategy_id: str, symbol: str, strategy_type: str,
                  legs: list, metrics: dict, spot: float, iv: float) -> StrategySnapshot:
    """Saves strategy entry state."""
    db = SessionLocal()
    try:
        snapshot = StrategySnapshot(
            strategy_id=strategy_id,
            symbol=symbol.upper(),
            strategy_type=strategy_type,
            legs_json=json.dumps(legs),
            entry_metrics_json=json.dumps(metrics),
            entry_spot=spot,
            entry_iv=iv
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save snapshot: {e}")
        raise
    finally:
        db.close()

def get_snapshot(strategy_id: str) -> StrategySnapshot | None:
    """Returns None if not found."""
    db = SessionLocal()
    try:
        return db.query(StrategySnapshot).filter(StrategySnapshot.strategy_id == strategy_id).first()
    finally:
        db.close()

def save_health_log(strategy_id: str, diff: dict, explanation: str) -> HealthLog:
    """Persists a health event."""
    db = SessionLocal()
    try:
        log_entry = HealthLog(
            strategy_id=strategy_id,
            diff_json=json.dumps(diff),
            explanation=explanation
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save health log: {e}")
        raise
    finally:
        db.close()

def get_health_logs(strategy_id: str, limit: int = 50) -> list[HealthLog]:
    """Returns logs newest first."""
    db = SessionLocal()
    try:
        return db.query(HealthLog).filter(
            HealthLog.strategy_id == strategy_id
        ).order_by(HealthLog.logged_at.desc()).limit(limit).all()
    finally:
        db.close()

def get_last_option_data(symbol: str) -> dict | None:
    """
    For Tier 3 fallback. Returns the most recently saved option chain
    data for this symbol extracted from strategy snapshots.
    """
    db = SessionLocal()
    try:
        latest = db.query(StrategySnapshot).filter(
            StrategySnapshot.symbol == symbol.upper()
        ).order_by(StrategySnapshot.created_at.desc()).first()
        
        if latest and latest.entry_metrics_json:
            metrics = json.loads(latest.entry_metrics_json)
            # Standard practice: we inject a full option chain snapshot into the metrics dict 
            # under "full_chain" when saving a StrategySnapshot, allowing this recovery.
            if "full_chain" in metrics:
                return metrics["full_chain"]
        return None
    except Exception as e:
        logger.warning(f"Error fetching last option data from DB: {e}")
        return None
    finally:
        db.close()