from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select
from .config import settings
from .models.base import Base

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_default_categories()


async def _seed_default_categories():
    """Вставляє системні категорії якщо їх ще немає."""
    from .models.category import Category, DEFAULT_CATEGORIES
    async with async_session_maker() as session:
        await _seed_categories_in_session(session)


async def _seed_categories_in_session(session):
    """Seed можна викликати з будь-якої сесії (включаючи тестову)."""
    from .models.category import Category, DEFAULT_CATEGORIES
    result = await session.execute(
        select(Category).where(Category.is_default == True).limit(1)
    )
    if result.scalar_one_or_none():
        return
    for item in DEFAULT_CATEGORIES:
        session.add(Category(
            user_id=None,
            name=item["name"],
            tax_code=item["tax_code"],
            sort_order=item["sort_order"],
            is_default=True,
        ))
    await session.commit()


async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
