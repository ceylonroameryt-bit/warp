"use client";

import React, { useState, useEffect } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import {
  Users,
  UserPlus,
  Shield,
  MoreVertical,
  Mail,
  CheckCircle,
  AlertCircle,
  Trash2,
  UserX,
  UserCheck,
  Clock,
  ChevronDown,
  Loader2,
  X,
} from "lucide-react";

interface Member {
  user_id: string;
  email: string;
  full_name: string | null;
  role: string;
  role_id: string;
  status: "active" | "invited" | "suspended";
  joined_at: string | null;
}

interface Invitation {
  id: string;
  email: string;
  role_id: string;
  expires_at: string;
  created_at: string;
}

interface RoleOption {
  id: string;
  name: string;
  description: string;
}

const CANONICAL_ROLES: { name: string; label: string; description: string; badgeColor: string }[] = [
  { name: "owner", label: "Owner", description: "Full commercial & system authority", badgeColor: "bg-purple-100 text-purple-800 border-purple-200" },
  { name: "administrator", label: "Administrator", description: "Manages team, settings, and business records", badgeColor: "bg-blue-100 text-blue-800 border-blue-200" },
  { name: "accountant", label: "Accountant", description: "Manages ledger, tax, journal posting, and reports", badgeColor: "bg-emerald-100 text-emerald-800 border-emerald-200" },
  { name: "bookkeeper", label: "Bookkeeper", description: "Data entry, draft invoices, bills, and document capture", badgeColor: "bg-cyan-100 text-cyan-800 border-cyan-200" },
  { name: "approver", label: "Approver", description: "Authorizes supplier bills and purchase commitments", badgeColor: "bg-amber-100 text-amber-800 border-amber-200" },
  { name: "employee", label: "Employee", description: "Uploads receipts and creates operational records", badgeColor: "bg-slate-100 text-slate-800 border-slate-200" },
  { name: "auditor", label: "Auditor", description: "Read-only inspection across all financial ledgers and logs", badgeColor: "bg-indigo-100 text-indigo-800 border-indigo-200" },
  { name: "viewer", label: "Viewer", description: "Read-only business dashboard view", badgeColor: "bg-gray-100 text-gray-700 border-gray-200" },
];

export default function TeamManagementPage() {
  const [activeOrgId, setActiveOrgId] = useState<string>("00000000-0000-0000-0000-000000000001");
  const [members, setMembers] = useState<Member[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [roles, setRoles] = useState<RoleOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [selectedRoleId, setSelectedRoleId] = useState("");
  const [modalLoading, setModalLoading] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Load active organisation members and roles
  const loadData = async () => {
    setLoading(true);
    try {
      // 1. Fetch user orgs
      const orgsRes = await fetch("/api/v1/organisations/");
      if (orgsRes.ok) {
        const orgs = await orgsRes.json();
        if (orgs.length > 0) {
          const currentOrgId = orgs[0].id;
          setActiveOrgId(currentOrgId);

          // 2. Fetch members
          const memRes = await fetch(`/api/v1/organisations/${currentOrgId}/members/`);
          if (memRes.ok) {
            setMembers(await memRes.json());
          }

          // 3. Fetch invitations
          const invRes = await fetch(`/api/v1/organisations/${currentOrgId}/invitations/`);
          if (invRes.ok) {
            setInvitations(await invRes.json());
          }

          // 4. Fetch roles
          const rolesRes = await fetch(`/api/v1/organisations/${currentOrgId}/roles/`);
          if (rolesRes.ok) {
            const rData = await rolesRes.json();
            setRoles(rData);
            if (rData.length > 0) setSelectedRoleId(rData[0].id);
          }
        }
      }
    } catch (err) {
      console.error("Failed to load team data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSendInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalLoading(true);
    setNotification(null);

    try {
      const res = await fetch(`/api/v1/organisations/${activeOrgId}/invitations/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: inviteEmail, role_id: selectedRoleId }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to send invitation.");
      }

      setNotification({ type: "success", text: `Invitation dispatched to ${inviteEmail}.` });
      setInviteEmail("");
      setInviteModalOpen(false);
      loadData();
    } catch (err: any) {
      setNotification({ type: "error", text: err.message || "Failed to send invitation." });
    } finally {
      setModalLoading(false);
    }
  };

  const handleSuspendMember = async (userId: string, currentStatus: string) => {
    const isSuspended = currentStatus === "suspended";
    const endpoint = isSuspended ? "reactivate" : "suspend";
    try {
      const res = await fetch(
        `/api/v1/organisations/${activeOrgId}/members/${userId}/${endpoint}`,
        { method: "PATCH" }
      );
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Action failed.");
      }
      setNotification({
        type: "success",
        text: `Member status successfully set to ${isSuspended ? "active" : "suspended"}.`,
      });
      loadData();
    } catch (err: any) {
      setNotification({ type: "error", text: err.message });
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!confirm("Are you sure you want to remove this member from the organisation?")) return;
    try {
      const res = await fetch(
        `/api/v1/organisations/${activeOrgId}/members/${userId}`,
        { method: "DELETE" }
      );
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to remove member.");
      }
      setNotification({ type: "success", text: "Member removed from organisation." });
      loadData();
    } catch (err: any) {
      setNotification({ type: "error", text: err.message });
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200 pb-5">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <Users className="w-6 h-6 text-blue-600" />
              Team Management & Roles
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Configure fine-grained 8-role RBAC, invitations, and access permissions.
            </p>
          </div>
          <button
            onClick={() => setInviteModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors"
          >
            <UserPlus className="w-4 h-4" />
            Invite Member
          </button>
        </div>

        {/* Notifications */}
        {notification && (
          <div
            className={`p-4 rounded-xl border flex items-center justify-between ${
              notification.type === "success"
                ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                : "bg-red-50 border-red-200 text-red-800"
            }`}
          >
            <div className="flex items-center gap-2 text-sm font-medium">
              {notification.type === "success" ? (
                <CheckCircle className="w-5 h-5 text-emerald-600" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-600" />
              )}
              {notification.text}
            </div>
            <button onClick={() => setNotification(null)} className="text-slate-400 hover:text-slate-600">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Active Members Table */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
            <h3 className="text-sm font-semibold text-slate-800">
              Active Organisation Members ({members.length})
            </h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider font-semibold border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Member</th>
                  <th className="px-6 py-3">Role</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Joined Date</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {members.map((member) => {
                  const roleConfig = CANONICAL_ROLES.find(
                    (r) => r.name.toLowerCase() === member.role.toLowerCase()
                  ) || { label: member.role, badgeColor: "bg-slate-100 text-slate-700" };

                  return (
                    <tr key={member.user_id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="px-6 py-4">
                        <div className="font-medium text-slate-900">
                          {member.full_name || "Unnamed User"}
                        </div>
                        <div className="text-xs text-slate-500">{member.email}</div>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${roleConfig.badgeColor}`}
                        >
                          {roleConfig.label}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {member.status === "active" && (
                          <span className="inline-flex items-center gap-1 text-xs text-emerald-700 font-medium">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                            Active
                          </span>
                        )}
                        {member.status === "suspended" && (
                          <span className="inline-flex items-center gap-1 text-xs text-amber-700 font-medium">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                            Suspended
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-xs text-slate-500">
                        {member.joined_at
                          ? new Date(member.joined_at).toLocaleDateString("en-GB")
                          : "Pending"}
                      </td>
                      <td className="px-6 py-4 text-right space-x-2">
                        {member.role.toLowerCase() !== "owner" && (
                          <>
                            <button
                              onClick={() => handleSuspendMember(member.user_id, member.status)}
                              className="text-xs font-medium text-slate-600 hover:text-amber-600 transition-colors"
                              title={member.status === "suspended" ? "Reactivate member" : "Suspend member"}
                            >
                              {member.status === "suspended" ? "Reactivate" : "Suspend"}
                            </button>
                            <span className="text-slate-300">|</span>
                            <button
                              onClick={() => handleRemoveMember(member.user_id)}
                              className="text-xs font-medium text-red-600 hover:text-red-700 transition-colors"
                              title="Remove from team"
                            >
                              Remove
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pending Invitations Table */}
        {invitations.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
              <h3 className="text-sm font-semibold text-slate-800">
                Pending Invitations ({invitations.length})
              </h3>
            </div>
            <div className="divide-y divide-slate-100">
              {invitations.map((inv) => (
                <div key={inv.id} className="px-6 py-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Mail className="w-4 h-4 text-slate-400" />
                    <div>
                      <div className="text-sm font-medium text-slate-900">{inv.email}</div>
                      <div className="text-xs text-slate-400 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        Expires {new Date(inv.expires_at).toLocaleDateString("en-GB")}
                      </div>
                    </div>
                  </div>
                  <span className="text-xs bg-amber-50 text-amber-700 border border-amber-200 font-medium px-2 py-0.5 rounded-full">
                    Awaiting Acceptance
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Invite Member Modal */}
      {inviteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-md p-6">
            <div className="flex justify-between items-center pb-4 border-b border-slate-100">
              <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-blue-600" />
                Invite Team Member
              </h3>
              <button
                onClick={() => setInviteModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSendInvite} className="mt-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Recipient Email
                </label>
                <input
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@company.co.uk"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Assign Canonical Role
                </label>
                <select
                  value={selectedRoleId}
                  onChange={(e) => setSelectedRoleId(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600 bg-white"
                >
                  {roles.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name.toUpperCase()} — {r.description}
                    </option>
                  ))}
                </select>
              </div>

              <div className="pt-4 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setInviteModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 text-sm font-medium rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={modalLoading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors flex items-center gap-2"
                >
                  {modalLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
                  Send Invitation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
