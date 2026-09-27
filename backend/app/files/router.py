"""Warp Ladger — Files Router"""
import uuid
from fastapi import APIRouter, Depends, UploadFile, File as FastAPIFile
from sqlalchemy import select
from app.core.dependencies import CurrentUser, DBSession, OrgMembership, require_permission
from app.database.models import File
from app.files.storage import get_storage_backend, make_storage_key
from app.core.config import settings

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/heic",
    "image/heif",
    "application/pdf",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


@router.post(
    "/organisations/{org_id}/upload",
    status_code=201,
    dependencies=[Depends(require_permission("file", "upload"))],
)
async def upload_file(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
    upload: UploadFile = FastAPIFile(...),
):
    content_type = upload.content_type or ""
    # Normalise filename extension if content-type header is ambiguous
    filename = upload.filename or "unknown"
    if filename.lower().endswith(".heic") and content_type in ("", "application/octet-stream"):
        content_type = "image/heic"
    elif filename.lower().endswith(".heif") and content_type in ("", "application/octet-stream"):
        content_type = "image/heif"

    if content_type not in ALLOWED_CONTENT_TYPES:
        from app.core.exceptions import ValidationFailedError
        raise ValidationFailedError(f"File type '{content_type}' is not allowed.")

    data = await upload.read()
    if len(data) > MAX_FILE_SIZE:
        from app.core.exceptions import ValidationFailedError
        raise ValidationFailedError("File exceeds maximum size of 25 MB.")

    storage = get_storage_backend()
    key = make_storage_key(org_id, filename)
    await storage.upload(key=key, data=data, content_type=content_type)

    file_record = File(
        organisation_id=org_id,
        uploaded_by_id=current_user.id,
        bucket=settings.STORAGE_BUCKET_NAME,
        key=key,
        filename=filename,
        content_type=content_type,
        size_bytes=len(data),
    )
    db.add(file_record)
    await db.flush()

    from app.audit.service import AuditService
    audit = AuditService(db)
    await audit.log(
        action="file.uploaded",
        resource_type="file",
        resource_id=str(file_record.id),
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"filename": filename, "content_type": content_type, "size_bytes": len(data)},
    )

    url = await storage.generate_presigned_url(key=key)
    return {
        "id": str(file_record.id),
        "filename": file_record.filename,
        "content_type": file_record.content_type,
        "size_bytes": file_record.size_bytes,
        "url": url,
    }


@router.get(
    "/organisations/{org_id}",
    dependencies=[Depends(require_permission("file", "read"))],
)
async def list_files(
    org_id: uuid.UUID, db: DBSession, membership: OrgMembership
):
    result = await db.execute(
        select(File)
        .where(File.organisation_id == org_id)
        .where(File.is_deleted.is_(False))
        .order_by(File.created_at.desc())
    )
    files = result.scalars().all()
    storage = get_storage_backend()
    return [
        {
            "id": str(f.id),
            "filename": f.filename,
            "content_type": f.content_type,
            "size_bytes": f.size_bytes,
            "created_at": f.created_at.isoformat(),
        }
        for f in files
    ]


@router.get(
    "/organisations/{org_id}/{file_id}",
    dependencies=[Depends(require_permission("file", "read"))],
)
async def get_file_detail(
    org_id: uuid.UUID,
    file_id: uuid.UUID,
    db: DBSession,
    membership: OrgMembership,
):
    result = await db.execute(
        select(File)
        .where(File.organisation_id == org_id)
        .where(File.id == file_id)
        .where(File.is_deleted.is_(False))
    )
    f = result.scalar_one_or_none()
    if f is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("File not found.")

    storage = get_storage_backend()
    url = await storage.generate_presigned_url(key=f.key)
    return {
        "id": str(f.id),
        "filename": f.filename,
        "content_type": f.content_type,
        "size_bytes": f.size_bytes,
        "created_at": f.created_at.isoformat(),
        "url": url,
    }


@router.delete(
    "/organisations/{org_id}/{file_id}",
    status_code=204,
    dependencies=[Depends(require_permission("file", "delete"))],
)
async def delete_file(
    org_id: uuid.UUID,
    file_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    membership: OrgMembership,
):
    result = await db.execute(
        select(File)
        .where(File.organisation_id == org_id)
        .where(File.id == file_id)
        .where(File.is_deleted.is_(False))
    )
    f = result.scalar_one_or_none()
    if f is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("File not found.")

    f.is_deleted = True
    await db.flush()

    storage = get_storage_backend()
    try:
        await storage.delete(f.key)
    except Exception:
        pass

    from app.audit.service import AuditService
    audit = AuditService(db)
    await audit.log(
        action="file.deleted",
        resource_type="file",
        resource_id=str(f.id),
        organisation_id=org_id,
        user_id=current_user.id,
        diff={"filename": f.filename},
    )
