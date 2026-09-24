"""User database access helpers."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    hashed_password: str,
    display_name: str | None = None,
    is_superuser: bool = False,
) -> User:
    """Create a user and flush it into the current transaction."""
    user = User(
        email=email,
        hashed_password=hashed_password,
        display_name=display_name,
        is_superuser=is_superuser,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    """Return one user by primary key."""
    return await session.get(User, user_id)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Return one user by email address."""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def list_users(
    session: AsyncSession,
    *,
    limit: int = 20,
    offset: int = 0,
) -> list[User]:
    """Return a paginated list of users."""
    result = await session.execute(
        select(User)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def update_user(
    session: AsyncSession,
    user: User,
    *,
    display_name: str | None = None,
    is_active: bool | None = None,
    is_superuser: bool | None = None,
) -> User:
    """Update editable user fields and refresh the ORM object."""
    if display_name is not None:
        user.display_name = display_name
    if is_active is not None:
        user.is_active = is_active
    if is_superuser is not None:
        user.is_superuser = is_superuser

    await session.flush()
    await session.refresh(user)
    return user


async def delete_user(session: AsyncSession, user_id: UUID) -> bool:
    """Delete one user by id and return whether a row was removed."""
    result = await session.execute(delete(User).where(User.id == user_id))
    return bool(result.rowcount)


async def set_user_active(
    session: AsyncSession,
    user: User,
    *,
    is_active: bool,
) -> User:
    """Enable or disable a user account."""
    user.is_active = is_active
    await session.flush()
    await session.refresh(user)
    return user


async def update_user_password(
    session: AsyncSession,
    user: User,
    *,
    hashed_password: str,
) -> User:
    """Update a user's hashed password."""
    user.hashed_password = hashed_password
    await session.flush()
    await session.refresh(user)
    return user
