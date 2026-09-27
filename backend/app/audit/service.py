"""Warp Ladger — Audit Logging Service"""
import uuid
from typing import Any, Optional

import structlog
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AuditLog

log = structlog.get_logger(__name__)


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    async def log_static(
        db: AsyncSession,
        *,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        organisation_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        diff: Optional[dict] = None,
        request: Optional[Request] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        if request:
            ip_address = ip_address or (request.client.host if request.client else None)
            user_agent = user_agent or request.headers.get("user-agent")

        entry = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            organisation_id=organisation_id,
            user_id=user_id,
            diff=diff,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if db:
            db.add(entry)
            await db.flush()
        log.info(
            "audit_event",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            org_id=str(organisation_id) if organisation_id else None,
            user_id=str(user_id) if user_id else None,
        )
        return entry

    class _LogDispatcher:
        def __get__(self, instance, owner):
            if instance is not None:
                async def _call(*args, **kwargs):
                    return await owner.log_static(instance.db, *args, **kwargs)
                return _call
            else:
                async def _call(*args, db=None, **kwargs):
                    if db is None and args:
                        db = args[0]
                        args = args[1:]
                    return await owner.log_static(db, *args, **kwargs)
                return _call

    log = _LogDispatcher()

    async def list_events(
        self,
        *,
        organisation_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
        resource_type: Optional[str] = None,
    ) -> tuple[list[AuditLog], int]:
        query = (
            select(AuditLog)
            .where(AuditLog.organisation_id == organisation_id)
            .order_by(AuditLog.created_at.desc())
        )
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)

        from sqlalchemy import func, select as sa_select

        count_result = await self.db.execute(
            sa_select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        return list(result.scalars().all()), total
