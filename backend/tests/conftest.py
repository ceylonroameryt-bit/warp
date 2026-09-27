"""
Warp Ladger — Pytest Test Fixtures
Async in-memory SQLite database setup with multi-tenant organisations, users, and roles.
"""
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.dependencies import get_db
from app.core.security import create_access_token, hash_password
from app.database.base import Base
from app.database.models import (
    Membership,
    MembershipStatus,
    Organisation,
    OrganisationStatus,
    Role,
    User,
)
from app.core.config import settings
from app.main import app
from app.roles.service import seed_permissions_and_roles

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
settings.STORAGE_BACKEND = "memory"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def test_setup(db_session: AsyncSession):
    """Seed permissions, roles, 2 distinct organisations, and users."""
    await seed_permissions_and_roles(db_session)

    # User 1: Alice (Owner of Org A)
    user_a = User(
        id=uuid.uuid4(),
        email="alice@orga.com",
        full_name="Alice Owner",
        hashed_password=hash_password("Password123!"),
        email_verified=True,
        is_active=True,
    )
    db_session.add(user_a)

    # User 2: Bob (Member of Org A)
    user_a_member = User(
        id=uuid.uuid4(),
        email="bob@orga.com",
        full_name="Bob Member",
        hashed_password=hash_password("Password123!"),
        email_verified=True,
        is_active=True,
    )
    db_session.add(user_a_member)

    # User 3: Charlie (Owner of Org B)
    user_b = User(
        id=uuid.uuid4(),
        email="charlie@orgb.com",
        full_name="Charlie OrgB",
        hashed_password=hash_password("Password123!"),
        email_verified=True,
        is_active=True,
    )
    db_session.add(user_b)
    await db_session.flush()

    # Organisation A
    org_a = Organisation(
        id=uuid.uuid4(),
        name="Acme Corp UK",
        slug="acme-corp-uk",
        currency="GBP",
        owner_id=user_a.id,
        status=OrganisationStatus.active,
    )
    db_session.add(org_a)

    # Organisation B
    org_b = Organisation(
        id=uuid.uuid4(),
        name="Beta Logistics",
        slug="beta-logistics",
        currency="EUR",
        owner_id=user_b.id,
        status=OrganisationStatus.active,
    )
    db_session.add(org_b)
    await db_session.flush()

    # Get roles
    from sqlalchemy import select
    res_owner = await db_session.execute(select(Role).where(Role.name == "owner"))
    owner_role = res_owner.scalar_one()

    res_member = await db_session.execute(select(Role).where(Role.name == "member"))
    member_role = res_member.scalar_one()

    # Memberships
    mem_a_owner = Membership(
        user_id=user_a.id,
        organisation_id=org_a.id,
        role_id=owner_role.id,
        status=MembershipStatus.active,
    )
    mem_a_member = Membership(
        user_id=user_a_member.id,
        organisation_id=org_a.id,
        role_id=member_role.id,
        status=MembershipStatus.active,
    )
    mem_b_owner = Membership(
        user_id=user_b.id,
        organisation_id=org_b.id,
        role_id=owner_role.id,
        status=MembershipStatus.active,
    )
    db_session.add_all([mem_a_owner, mem_a_member, mem_b_owner])
    await db_session.commit()

    # Tokens
    token_a = create_access_token(str(user_a.id))
    token_a_member = create_access_token(str(user_a_member.id))
    token_b = create_access_token(str(user_b.id))

    return {
        "org_a": org_a,
        "org_b": org_b,
        "user_a": user_a,
        "user_a_member": user_a_member,
        "user_b": user_b,
        "token_a": token_a,
        "token_a_member": token_a_member,
        "token_b": token_b,
    }


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
