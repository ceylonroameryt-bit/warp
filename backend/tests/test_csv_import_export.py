"""
Warp Ladger — CSV Import & Export Tests
Section 38, 39, 40, 41 Compliance.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_csv_import_preview_and_execution(client: AsyncClient, test_setup: dict):
    org_id = str(test_setup["org_a"].id)
    headers = {"Authorization": f"Bearer {test_setup['token_a']}"}

    csv_data = """Name,Type,Email,Telephone,VAT
Valid Tech Ltd,CUSTOMER,contact@validtech.com,02071234567,GB111222333
,SUPPLIER,,02079998888,
Bad Email Ltd,CUSTOMER,not-an-email,01211112222,GB444555666
Good Supplies,SUPPLIER,info@goodsupplies.com,01612223333,
"""
    files = {"file": ("contacts.csv", csv_data.encode("utf-8"), "text/csv")}

    # 1. Preview
    preview_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/import/preview",
        files=files,
        headers=headers,
    )
    assert preview_res.status_code == 200, preview_res.text
    preview = preview_res.json()
    assert preview["total_rows"] == 4
    assert preview["valid_rows"] == 2
    assert preview["error_count"] == 2

    # 2. Execute Import with valid rows
    valid_rows = [r["data"] for r in preview["rows"] if r["valid"]]
    exec_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/import/execute",
        json={"rows": valid_rows, "skip_errors": True},
        headers=headers,
    )
    assert exec_res.status_code == 200
    res_data = exec_res.json()
    assert res_data["created_count"] == 2
    assert res_data["skipped_count"] == 0

    # Verify contacts exist in list
    list_res = await client.get(f"/api/v1/organisations/{org_id}/contacts", headers=headers)
    names = [c["business_name"] for c in list_res.json()["items"]]
    assert "Valid Tech Ltd" in names
    assert "Good Supplies" in names


async def test_csv_export(client: AsyncClient, test_setup: dict):
    org_id = str(test_setup["org_a"].id)
    headers = {"Authorization": f"Bearer {test_setup['token_a']}"}

    # Create a contact first
    await client.post(
        f"/api/v1/organisations/{org_id}/contacts/quick",
        json={"business_name": "Export Test Company", "email": "export@test.com"},
        headers=headers,
    )

    export_res = await client.get(f"/api/v1/organisations/{org_id}/contacts/export", headers=headers)
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers["content-type"]
    csv_text = export_res.text
    assert "Business Name" in csv_text
    assert "Export Test Company" in csv_text
    assert "export@test.com" in csv_text
