"use client";

import React, { useState, useEffect } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import {
  ShieldAlert,
  Search,
  Filter,
  RefreshCw,
  FileText,
  User,
  Clock,
  ShieldCheck,
  ChevronRight,
  Database,
  ArrowDownUp,
} from "lucide-react";

interface AuditEntry {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  user_id: string | null;
  user_email?: string;
  diff: Record<string, any> | null;
  ip_address: string | null;
  created_at: string;
}

export default function AuditLogViewerPage() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeOrgId, setActiveOrgId] = useState<string>("00000000-0000-0000-0000-000000000001");

  const fetchAuditLogs = async () => {
    setLoading(true);
    try {
      const orgsRes = await fetch("/api/v1/organisations/");
      if (orgsRes.ok) {
        const orgs = await orgsRes.json();
        if (orgs.length > 0) {
          const orgId = orgs[0].id;
          setActiveOrgId(orgId);

          const auditRes = await fetch(`/api/v1/organisations/${orgId}/audit/?limit=50`);
          if (auditRes.ok) {
            const data = await auditRes.json();
            setLogs(data.items || data || []);
          }
        }
      }
    } catch (err) {
      console.error("Failed to load audit logs", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, []);

  const filteredLogs = logs.filter((log) => {
    const q = searchTerm.toLowerCase();
    return (
      log.action.toLowerCase().includes(q) ||
      log.resource_type.toLowerCase().includes(q) ||
      (log.resource_id && log.resource_id.toLowerCase().includes(q))
    );
  });

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200 pb-5">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-blue-600" />
              Centralized Audit Ledger
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Immutable, timestamped historical trace of all mutations, logins, and permission changes.
            </p>
          </div>
          <button
            onClick={fetchAuditLogs}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-medium rounded-lg shadow-sm transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh Trail
          </button>
        </div>

        {/* Filter bar */}
        <div className="flex items-center gap-4 bg-white p-3 rounded-xl border border-slate-200 shadow-sm">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search by action, resource type or ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>
        </div>

        {/* Audit Log Table */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider font-semibold border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Timestamp</th>
                  <th className="px-6 py-3">Action</th>
                  <th className="px-6 py-3">Resource</th>
                  <th className="px-6 py-3">Details / Diff</th>
                  <th className="px-6 py-3">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredLogs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-slate-500 text-sm">
                      {loading ? "Loading audit trail..." : "No matching audit log entries found."}
                    </td>
                  </tr>
                ) : (
                  filteredLogs.map((entry) => (
                    <tr key={entry.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-xs text-slate-500 font-mono">
                        {new Date(entry.created_at).toLocaleString("en-GB")}
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-slate-100 text-slate-800 font-mono border border-slate-200">
                          {entry.action}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-xs font-medium text-slate-900 capitalize">
                          {entry.resource_type}
                        </div>
                        {entry.resource_id && (
                          <div className="text-[10px] text-slate-400 font-mono">
                            {entry.resource_id.substring(0, 12)}...
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 text-xs font-mono text-slate-600 max-w-md truncate">
                        {entry.diff ? JSON.stringify(entry.diff) : "—"}
                      </td>
                      <td className="px-6 py-4 text-xs font-mono text-slate-400">
                        {entry.ip_address || "internal"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
