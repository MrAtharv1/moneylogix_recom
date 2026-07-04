"""database.py — Async SQLite database setup and CRUD operations."""
import json
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, select

try:
    from config import settings
    DB_URL = settings.DATABASE_URL
except ImportError:
    DB_URL = "sqlite:///./moneylogix.db"

# Format for async SQLite
ASYNC_DB_URL = DB_URL.replace("sqlite://", "sqlite+aiosqlite://")

logger = logging.getLogger(__name__)

engine = create_async_engine(ASYNC_DB_URL, connect_args={"check_same_thread": False})
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
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

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def save_snapshot(strategy_id: str, symbol: str, strategy_type: str,
                        legs: list, metrics: dict, spot: float, iv: float):
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(StrategySnapshot).filter(StrategySnapshot.strategy_id == strategy_id))
            existing = result.scalars().first()
            
            if existing:
                existing.symbol = symbol.upper()
                existing.strategy_type = strategy_type
                existing.legs_json = json.dumps(legs)
                existing.entry_metrics_json = json.dumps(metrics)
                existing.entry_spot = spot
                existing.entry_iv = iv
                existing.created_at = datetime.utcnow()
            else:
                snap = StrategySnapshot(
                    strategy_id=strategy_id,
                    symbol=symbol.upper(),
                    strategy_type=strategy_type,
                    legs_json=json.dumps(legs),
                    entry_metrics_json=json.dumps(metrics),
                    entry_spot=spot,
                    entry_iv=iv
                )
                db.add(snap)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Save snapshot failed: {e}")
            raise

async def get_snapshot(strategy_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(StrategySnapshot).filter(StrategySnapshot.strategy_id == strategy_id))
        return result.scalars().first()

async def save_health_log(strategy_id: str, diff: dict, explanation: str):
    async with AsyncSessionLocal() as db:
        try:
            entry = HealthLog(strategy_id=strategy_id, diff_json=json.dumps(diff), explanation=explanation)
            db.add(entry)
            await db.commit()
            await db.refresh(entry)
            return entry
        except Exception as e:
            await db.rollback()
            logger.error(f"Save health log failed: {e}")
            raise

async def get_health_logs(strategy_id: str, limit: int = 50):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(HealthLog).filter(HealthLog.strategy_id == strategy_id).order_by(HealthLog.logged_at.desc()).limit(limit)
        )
        return result.scalars().all()

async def get_last_option_data(symbol: str) -> dict | None:
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(StrategySnapshot)
                .filter(StrategySnapshot.symbol == symbol.upper())
                .order_by(StrategySnapshot.created_at.desc())
                .limit(1)
            )
            latest = result.scalars().first()
            if latest and latest.entry_metrics_json:
                metrics = json.loads(latest.entry_metrics_json)
                if "full_chain" in metrics:
                    return metrics["full_chain"]
            return None
        except Exception as e:
            logger.warning(f"Error fetching last option data: {e}")
            return None