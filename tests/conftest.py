"""conftest.py — спільні fixtures для всіх тестів."""
import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from bot.models.base import Base
from bot.models import User, Vehicle, Address, Trip, TripPurpose
from datetime import date


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    """In-memory SQLite сесія для тестів."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(telegram_id=123456789, name="Test User", lang="de")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_vehicle(db_session: AsyncSession, test_user: User) -> Vehicle:
    v = Vehicle(user_id=test_user.id, make="VW", model="Golf",
                plate="M-TT 001", current_mileage=85000.0)
    db_session.add(v)
    await db_session.commit()
    await db_session.refresh(v)
    return v


@pytest.fixture
async def test_trips(db_session: AsyncSession, test_user: User, test_vehicle: Vehicle):
    trips = []
    km = 85000.0
    data = [
        (1, 45, "Heimat", "Kunde A", True),
        (3, 15, "Kunde A", "Büro",   True),
        (5, 60, "Büro",   "Heimat",  False),
    ]
    for day, dist, frm, to, biz in data:
        t = Trip(
            user_id=test_user.id, vehicle_id=test_vehicle.id,
            date=date(2025, 1, day),
            start_address_text=frm, end_address_text=to,
            start_mileage=km, end_mileage=km + dist,
            purpose=TripPurpose.BUSINESS if biz else TripPurpose.PRIVATE,
        )
        trips.append(t)
        km += dist
    db_session.add_all(trips)
    await db_session.commit()
    return trips
