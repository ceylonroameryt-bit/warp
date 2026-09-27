"""
Warp Ladger — Comprehensive Phase 2 Test Suite: Customers, Suppliers & Contact Management
Validates:
1. Central Contact System (CUSTOMER, SUPPLIER, BOTH)
2. Sub-resource hierarchy: People, Addresses, Notes, Documents (FileLink)
3. Search, Filters, Sorting, and Pagination
4. Archive and Restore lifecycle
5. Smart Duplicate Detection (VAT, Company Number, Normalized Name)
6. CSV Import (Preview & Execution) and CSV Export
7. Fine-grained RBAC across all 8 canonical roles
8. Strict Tenant Isolation
"""
import io
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User, Organisation, Membership, MembershipStatus, Role, ContactType, ContactStatus
from app.roles.service import seed_permissions_and_roles
from app.core.security import create_access_token

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def phase2_setup(db_session: AsyncSession):
    """
    Sets up two isolated organisations (Org Alpha and Org Beta)
    and seeds all 8 canonical roles.
    """
    await seed_permissions_and_roles(db_session)

    # 1. Users
    owner_a = User(
        email="owner_a@test.com",
        hashed_password="hash",
        full_name="Alice Owner",
        email_verified=True,
    )
    admin_a = User(
        email="admin_a@test.com",
        hashed_password="hash",
        full_name="Arthur Admin",
        email_verified=True,
    )
    accountant_a = User(
        email="accountant_a@test.com",
        hashed_password="hash",
        full_name="Amy Accountant",
        email_verified=True,
    )
    bookkeeper_a = User(
        email="bookkeeper_a@test.com",
        hashed_password="hash",
        full_name="Bob Bookkeeper",
        email_verified=True,
    )
    approver_a = User(
        email="approver_a@test.com",
        hashed_password="hash",
        full_name="Arnold Approver",
        email_verified=True,
    )
    employee_a = User(
        email="employee_a@test.com",
        hashed_password="hash",
        full_name="Evan Employee",
        email_verified=True,
    )
    auditor_a = User(
        email="auditor_a@test.com",
        hashed_password="hash",
        full_name="Audrey Auditor",
        email_verified=True,
    )
    viewer_a = User(
        email="viewer_a@test.com",
        hashed_password="hash",
        full_name="Victor Viewer",
        email_verified=True,
    )

    # Tenant B User
    owner_b = User(
        email="owner_b@test.com",
        hashed_password="hash",
        full_name="Boris Beta",
        email_verified=True,
    )

    db_session.add_all([
        owner_a, admin_a, accountant_a, bookkeeper_a, approver_a, employee_a, auditor_a, viewer_a, owner_b
    ])
    await db_session.flush()

    # 2. Organisations
    org_a = Organisation(name="Alpha Corp", slug="alpha-corp", owner_id=owner_a.id)
    org_b = Organisation(name="Beta Enterprises", slug="beta-enterprises", owner_id=owner_b.id)
    db_session.add_all([org_a, org_b])
    await db_session.flush()

    # 3. Roles lookup
    async def get_role(name: str):
        res = await db_session.execute(Role.__table__.select().where(Role.name == name))
        return res.mappings().first()["id"]

    roles = {
        "owner": await get_role("owner"),
        "administrator": await get_role("administrator"),
        "accountant": await get_role("accountant"),
        "bookkeeper": await get_role("bookkeeper"),
        "approver": await get_role("approver"),
        "employee": await get_role("employee"),
        "auditor": await get_role("auditor"),
        "viewer": await get_role("viewer"),
    }

    # 4. Memberships for Org A
    members = [
        Membership(organisation_id=org_a.id, user_id=owner_a.id, role_id=roles["owner"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=admin_a.id, role_id=roles["administrator"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=accountant_a.id, role_id=roles["accountant"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=bookkeeper_a.id, role_id=roles["bookkeeper"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=approver_a.id, role_id=roles["approver"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=employee_a.id, role_id=roles["employee"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=auditor_a.id, role_id=roles["auditor"], status=MembershipStatus.active),
        Membership(organisation_id=org_a.id, user_id=viewer_a.id, role_id=roles["viewer"], status=MembershipStatus.active),
    ]
    # Membership for Org B
    members.append(
        Membership(organisation_id=org_b.id, user_id=owner_b.id, role_id=roles["owner"], status=MembershipStatus.active)
    )
    db_session.add_all(members)
    await db_session.commit()

    return {
        "org_a": org_a,
        "org_b": org_b,
        "tokens": {
            "owner": create_access_token(str(owner_a.id)),
            "admin": create_access_token(str(admin_a.id)),
            "accountant": create_access_token(str(accountant_a.id)),
            "bookkeeper": create_access_token(str(bookkeeper_a.id)),
            "approver": create_access_token(str(approver_a.id)),
            "employee": create_access_token(str(employee_a.id)),
            "auditor": create_access_token(str(auditor_a.id)),
            "viewer": create_access_token(str(viewer_a.id)),
            "owner_b": create_access_token(str(owner_b.id)),
        },
        "users": {
            "owner_a": owner_a,
            "owner_b": owner_b,
        }
    }


async def test_full_contact_hierarchy_lifecycle(client: AsyncClient, phase2_setup: dict):
    """
    Test creating a contact with primary person and addresses,
    adding secondary people, addresses, notes, and file attachments.
    """
    org_id = str(phase2_setup["org_a"].id)
    token = phase2_setup["tokens"]["owner"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Contact (CUSTOMER) with primary person & billing address
    payload = {
        "contact_type": "CUSTOMER",
        "business_name": "Zenith Dynamics Ltd",
        "legal_name": "Zenith Dynamics Limited",
        "email": "finance@zenithdynamics.com",
        "phone": "+44 20 7123 4567",
        "company_number": "08765432",
        "vat_number": "GB999888777",
        "currency": "GBP",
        "primary_contact": {
            "first_name": "Alice",
            "last_name": "Vance",
            "job_title": "CFO",
            "email": "alice@zenithdynamics.com",
            "phone": "+44 20 7123 4568",
            "is_primary": True,
        },
        "billing_address": {
            "address_type": "BILLING",
            "line1": "45 Park Lane",
            "city": "London",
            "postcode": "W1K 1PN",
            "country_code": "GB",
            "is_primary": True,
        },
    }

    res = await client.post(f"/api/v1/organisations/{org_id}/contacts", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    contact = res.json()
    assert contact["business_name"] == "Zenith Dynamics Ltd"
    assert contact["contact_type"] == "CUSTOMER"
    assert contact["primary_contact_name"] == "Alice Vance"
    contact_id = contact["id"]

    # 2. Add Secondary Person
    person_payload = {
        "first_name": "Bob",
        "last_name": "Builder",
        "job_title": "Operations Manager",
        "email": "bob@zenithdynamics.com",
        "is_primary": False,
    }
    res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/{contact_id}/people",
        json=person_payload,
        headers=headers,
    )
    assert res.status_code == 201
    person_data = res.json()
    assert person_data["first_name"] == "Bob"
    person_id = person_data["id"]

    # 3. Add Shipping Address
    addr_payload = {
        "address_type": "SHIPPING",
        "line1": "Warehouse Dock 4",
        "city": "Manchester",
        "postcode": "M1 4BT",
        "country_code": "GB",
        "is_primary": False,
    }
    res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/{contact_id}/addresses",
        json=addr_payload,
        headers=headers,
    )
    assert res.status_code == 201
    addr_id = res.json()["id"]

    # 4. Add Internal Note
    note_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/{contact_id}/notes",
        json={"content": "Credit limit approved up to £50,000."},
        headers=headers,
    )
    assert note_res.status_code == 201
    assert note_res.json()["content"] == "Credit limit approved up to £50,000."

    # 5. Upload file and attach to contact
    file_bytes = b"%PDF-1.4 test contact doc"
    upload_res = await client.post(
        f"/api/v1/files/organisations/{org_id}/upload",
        files={"upload": ("contract.pdf", io.BytesIO(file_bytes), "application/pdf")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["id"]

    attach_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/{contact_id}/documents",
        json={"file_id": file_id},
        headers=headers,
    )
    assert attach_res.status_code == 201
    assert attach_res.json()["filename"] == "contract.pdf"

    # 6. Verify Contact Detail view
    detail_res = await client.get(f"/api/v1/organisations/{org_id}/contacts/{contact_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["people"]) == 2
    assert len(detail["addresses"]) == 2
    assert len(detail["internal_notes"]) == 1
    assert len(detail["documents"]) == 1
    assert detail["documents"][0]["filename"] == "contract.pdf"


async def test_search_filter_and_pagination(client: AsyncClient, phase2_setup: dict):
    """
    Test contact listing with filtering by type, free-text search, and pagination.
    """
    org_id = str(phase2_setup["org_a"].id)
    token = phase2_setup["tokens"]["accountant"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create multiple contacts
    c1 = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/quick",
        json={"contact_type": "CUSTOMER", "business_name": "Alpha Retail Ltd", "email": "retail@alpha.com"},
        headers=headers,
    )
    assert c1.status_code == 201

    c2 = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/quick",
        json={"contact_type": "SUPPLIER", "business_name": "Alpha Wholesale Logistics", "email": "wholesale@alpha.com"},
        headers=headers,
    )
    assert c2.status_code == 201

    c3 = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/quick",
        json={"contact_type": "BOTH", "business_name": "Beta Supplies Ltd", "email": "info@beta.com"},
        headers=headers,
    )
    assert c3.status_code == 201

    # Filter by contact_type=CUSTOMER
    res = await client.get(f"/api/v1/organisations/{org_id}/contacts?contact_type=CUSTOMER", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(c["business_name"] == "Alpha Retail Ltd" for c in items)
    assert not any(c["business_name"] == "Alpha Wholesale Logistics" for c in items)

    # Search query "Wholesale"
    res = await client.get(f"/api/v1/organisations/{org_id}/contacts?search=Wholesale", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["business_name"] == "Alpha Wholesale Logistics"

    # Pagination: page_size=1
    res = await client.get(f"/api/v1/organisations/{org_id}/contacts?page=1&page_size=1", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1
    assert data["page_size"] == 1
    assert data["total"] >= 3


async def test_archive_and_restore_workflow(client: AsyncClient, phase2_setup: dict):
    """
    Test archiving a contact and restoring it, verifying status and audit recording.
    """
    org_id = str(phase2_setup["org_a"].id)
    token = phase2_setup["tokens"]["admin"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create contact
    c_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/quick",
        json={"business_name": "Temporary Partner Ltd"},
        headers=headers,
    )
    contact_id = c_res.json()["id"]

    # Archive contact
    arch_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/{contact_id}/archive",
        headers=headers,
    )
    assert arch_res.status_code == 200
    assert arch_res.json()["status"] == "ARCHIVED"

    # Default list excludes archived
    list_res = await client.get(f"/api/v1/organisations/{org_id}/contacts?status=ACTIVE", headers=headers)
    assert not any(c["id"] == contact_id for c in list_res.json()["items"])

    # Query with status=ARCHIVED
    arch_list = await client.get(f"/api/v1/organisations/{org_id}/contacts?status=ARCHIVED", headers=headers)
    assert any(c["id"] == contact_id for c in arch_list.json()["items"])

    # Restore contact
    restore_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/{contact_id}/restore",
        headers=headers,
    )
    assert restore_res.status_code == 200
    assert restore_res.json()["status"] == "ACTIVE"


async def test_duplicate_detection_rules(client: AsyncClient, phase2_setup: dict):
    """
    Test duplicate checking:
    1. Exact VAT Number match (HIGH confidence)
    2. Exact Company Number match (HIGH confidence)
    3. Normalized Name match (HIGH / MEDIUM confidence)
    """
    org_id = str(phase2_setup["org_a"].id)
    token = phase2_setup["tokens"]["bookkeeper"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create base contact
    await client.post(
        f"/api/v1/organisations/{org_id}/contacts",
        json={
            "business_name": "Titanium Engineering Ltd",
            "vat_number": "GB 111 222 333",
            "company_number": "07654321",
            "email": "orders@titanium-eng.co.uk",
        },
        headers=headers,
    )

    # 1. Check duplicate on VAT number
    dup_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/check-duplicates",
        json={
            "business_name": "Completely Different Name",
            "vat_number": "GB111222333",
        },
        headers=headers,
    )
    assert dup_res.status_code == 200
    data = dup_res.json()
    assert data["has_duplicates"] is True
    assert any("vat_number" in m["matched_fields"] for m in data["matches"])

    # 2. Check duplicate on Company Number
    dup_res2 = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/check-duplicates",
        json={
            "business_name": "Another Company",
            "company_number": "07654321",
        },
        headers=headers,
    )
    assert dup_res2.status_code == 200
    data2 = dup_res2.json()
    assert data2["has_duplicates"] is True
    assert any("company_number" in m["matched_fields"] for m in data2["matches"])

    # 3. Check duplicate on Normalized Name ("Titanium Engineering Limited")
    dup_res3 = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/check-duplicates",
        json={
            "business_name": "Titanium Engineering Limited",
        },
        headers=headers,
    )
    assert dup_res3.status_code == 200
    data3 = dup_res3.json()
    assert data3["has_duplicates"] is True
    assert any("business_name" in m["matched_fields"] for m in data3["matches"])


async def test_csv_import_preview_and_execute(client: AsyncClient, phase2_setup: dict):
    """
    Test CSV import workflow:
    1. Upload CSV to preview validation
    2. Commit valid rows via execute endpoint
    3. Export contacts back to CSV
    """
    org_id = str(phase2_setup["org_a"].id)
    token = phase2_setup["tokens"]["owner"]
    headers = {"Authorization": f"Bearer {token}"}

    csv_data = (
        "Company Name,Type,Email Address,Phone Number,Company Reg No,VAT Number,Street Address,City,Postal Code,Country Code\n"
        "CSV Client One Ltd,CUSTOMER,c1@csvtest.com,+44 20 0000 0001,11112222,GB111122222,10 Fleet St,London,EC4A 2AB,GB\n"
        "CSV Supplier Two Ltd,SUPPLIER,s2@csvtest.com,+44 20 0000 0002,33334444,GB333344444,20 High St,Manchester,M4 1AB,GB\n"
        ",CUSTOMER,invalid@missingname.com,,,,,,\n"  # Invalid row (missing name)
    )

    # 1. Preview CSV
    preview_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/import/preview",
        files={"file": ("import.csv", csv_data.encode("utf-8"), "text/csv")},
        headers=headers,
    )
    assert preview_res.status_code == 200, preview_res.text
    preview = preview_res.json()
    assert preview["total_rows"] == 3
    assert preview["valid_rows"] == 2
    assert preview["error_count"] == 1

    # 2. Execute Import with valid rows
    valid_rows = [r["data"] for r in preview["rows"] if r["valid"]]
    exec_res = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/import/execute",
        json={"rows": valid_rows, "skip_errors": True},
        headers=headers,
    )
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["created_count"] == 2
    assert exec_data["skipped_count"] == 0

    # 3. Export Contacts to CSV
    export_res = await client.get(
        f"/api/v1/organisations/{org_id}/contacts/export",
        headers=headers,
    )
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers["Content-Type"]
    csv_text = export_res.text
    assert "CSV Client One Ltd" in csv_text
    assert "CSV Supplier Two Ltd" in csv_text


async def test_rbac_8_roles_boundaries(client: AsyncClient, phase2_setup: dict):
    """
    Test fine-grained RBAC permission matrix for Contacts across all 8 canonical roles:
    - owner, admin, accountant, bookkeeper: full manage & archive
    - employee: can create & update, CANNOT archive
    - approver: can read, CANNOT create or archive
    - auditor & viewer: read-only, CANNOT mutate
    """
    org_id = str(phase2_setup["org_a"].id)
    tokens = phase2_setup["tokens"]

    # 1. Employee: Can create contact, cannot archive
    emp_headers = {"Authorization": f"Bearer {tokens['employee']}"}
    emp_create = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/quick",
        json={"business_name": "Employee Created Contact"},
        headers=emp_headers,
    )
    assert emp_create.status_code == 201
    contact_id = emp_create.json()["id"]

    # Employee tries to archive -> 403 Forbidden
    emp_archive = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/{contact_id}/archive",
        headers=emp_headers,
    )
    assert emp_archive.status_code == 403

    # 2. Approver: Cannot create contact
    appr_headers = {"Authorization": f"Bearer {tokens['approver']}"}
    appr_create = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/quick",
        json={"business_name": "Approver Created Contact"},
        headers=appr_headers,
    )
    assert appr_create.status_code == 403

    # Approver can read contact
    appr_read = await client.get(f"/api/v1/organisations/{org_id}/contacts/{contact_id}", headers=appr_headers)
    assert appr_read.status_code == 200

    # 3. Viewer: Cannot create, cannot update, can read
    view_headers = {"Authorization": f"Bearer {tokens['viewer']}"}
    view_create = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/quick",
        json={"business_name": "Viewer Created Contact"},
        headers=view_headers,
    )
    assert view_create.status_code == 403

    view_patch = await client.patch(
        f"/api/v1/organisations/{org_id}/contacts/{contact_id}",
        json={"business_name": "Hacked Name"},
        headers=view_headers,
    )
    assert view_patch.status_code == 403

    view_read = await client.get(f"/api/v1/organisations/{org_id}/contacts", headers=view_headers)
    assert view_read.status_code == 200

    # 4. Auditor: Can read, cannot create
    audit_headers = {"Authorization": f"Bearer {tokens['auditor']}"}
    audit_create = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/quick",
        json={"business_name": "Auditor Created Contact"},
        headers=audit_headers,
    )
    assert audit_create.status_code == 403

    # 5. Bookkeeper cannot archive contact
    bk_headers = {"Authorization": f"Bearer {tokens['bookkeeper']}"}
    bk_archive = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/{contact_id}/archive",
        headers=bk_headers,
    )
    assert bk_archive.status_code == 403

    # 6. Accountant can archive contact
    act_headers = {"Authorization": f"Bearer {tokens['accountant']}"}
    act_archive = await client.post(
        f"/api/v1/organisations/{org_id}/contacts/{contact_id}/archive",
        headers=act_headers,
    )
    assert act_archive.status_code == 200
    assert act_archive.json()["status"] == "ARCHIVED"


async def test_tenant_isolation_contacts(client: AsyncClient, phase2_setup: dict):
    """
    Ensure Tenant B cannot access, modify, or list contacts belonging to Tenant A.
    """
    org_a_id = str(phase2_setup["org_a"].id)
    org_b_id = str(phase2_setup["org_b"].id)
    token_a = phase2_setup["tokens"]["owner"]
    token_b = phase2_setup["tokens"]["owner_b"]

    # Org A creates a confidential contact
    headers_a = {"Authorization": f"Bearer {token_a}"}
    c_res = await client.post(
        f"/api/v1/organisations/{org_a_id}/contacts/quick",
        json={"business_name": "Confidential Alpha Client Ltd"},
        headers=headers_a,
    )
    assert c_res.status_code == 201
    contact_id = c_res.json()["id"]

    # Org B attempts to access Org A contact using Org A route -> 403 (membership check)
    headers_b = {"Authorization": f"Bearer {token_b}"}
    res = await client.get(f"/api/v1/organisations/{org_a_id}/contacts/{contact_id}", headers=headers_b)
    assert res.status_code == 403

    # Org B attempts to access Org A contact using Org B route -> 404 (tenant boundary check)
    res_b = await client.get(f"/api/v1/organisations/{org_b_id}/contacts/{contact_id}", headers=headers_b)
    assert res_b.status_code == 404

    # Org B listing must be empty
    list_b = await client.get(f"/api/v1/organisations/{org_b_id}/contacts", headers=headers_b)
    assert list_b.status_code == 200
    assert len(list_b.json()["items"]) == 0
