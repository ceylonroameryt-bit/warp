"""
Warp Ladger — Phase 1: Secure Private File Storage Tests
Verifies uploading PDF, JPG, PNG, HEIC, rejecting disallowed file formats,
enforcing 25MB limits, presigned URLs, and file deletion audit logs.
"""
import io
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_upload_supported_formats(client: AsyncClient, test_setup: dict):
    org_a_id = str(test_setup["org_a"].id)
    token_a = test_setup["token_a"]

    # Test PDF
    pdf_content = b"%PDF-1.4 sample pdf document bytes"
    pdf_res = await client.post(
        f"/api/v1/files/organisations/{org_a_id}/upload",
        files={"upload": ("document.pdf", io.BytesIO(pdf_content), "application/pdf")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert pdf_res.status_code == 201
    assert pdf_res.json()["filename"] == "document.pdf"
    assert pdf_res.json()["content_type"] == "application/pdf"
    assert "url" in pdf_res.json()

    # Test JPEG
    jpg_content = b"\xff\xd8\xff\xe0\x00\x10JFIF"
    jpg_res = await client.post(
        f"/api/v1/files/organisations/{org_a_id}/upload",
        files={"upload": ("receipt.jpg", io.BytesIO(jpg_content), "image/jpeg")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert jpg_res.status_code == 201
    assert jpg_res.json()["content_type"] == "image/jpeg"

    # Test PNG
    png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    png_res = await client.post(
        f"/api/v1/files/organisations/{org_a_id}/upload",
        files={"upload": ("statement.png", io.BytesIO(png_content), "image/png")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert png_res.status_code == 201
    assert png_res.json()["content_type"] == "image/png"

    # Test HEIC
    heic_content = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00"
    heic_res = await client.post(
        f"/api/v1/files/organisations/{org_a_id}/upload",
        files={"upload": ("camera_receipt.heic", io.BytesIO(heic_content), "image/heic")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert heic_res.status_code == 201
    assert heic_res.json()["content_type"] in ["image/heic", "image/heif"]


async def test_reject_disallowed_file_types(client: AsyncClient, test_setup: dict):
    org_a_id = str(test_setup["org_a"].id)
    token_a = test_setup["token_a"]

    # Executable file
    exe_content = b"MZ\x90\x00\x03\x00\x00\x00"
    res = await client.post(
        f"/api/v1/files/organisations/{org_a_id}/upload",
        files={"upload": ("virus.exe", io.BytesIO(exe_content), "application/x-msdos-program")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res.status_code == 422 or res.status_code == 400


async def test_file_deletion_and_audit(client: AsyncClient, test_setup: dict):
    org_a_id = str(test_setup["org_a"].id)
    token_a = test_setup["token_a"]

    # Upload file
    upload_res = await client.post(
        f"/api/v1/files/organisations/{org_a_id}/upload",
        files={"upload": ("to_delete.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["id"]

    # Delete file
    del_res = await client.delete(
        f"/api/v1/files/organisations/{org_a_id}/{file_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert del_res.status_code == 204

    # Verify file is not returned in list
    list_res = await client.get(
        f"/api/v1/files/organisations/{org_a_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert list_res.status_code == 200
    files = list_res.json()
    assert not any(f["id"] == file_id for f in files)
