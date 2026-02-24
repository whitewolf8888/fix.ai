"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface LeadRecord {
  id: string;
  created_at: string;
  name: string;
  email: string;
  company: string;
  team_size: string;
  use_case: string;
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<LeadRecord[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const token = typeof window !== "undefined" ? localStorage.getItem("vs_token") : "";

  const fetchLeads = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/marketing/leads`, {
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setLeads(data.leads || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load leads");
    } finally {
      setLoading(false);
    }
  };

  const downloadLeads = async (format: "csv" | "json") => {
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/marketing/leads/export?format=${format}`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `leads.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download leads");
    }
  };

  useEffect(() => {
    fetchLeads();
  }, []);

  const createPilot = async (lead: LeadRecord) => {
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/pilots`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          lead_email: lead.email,
          company: lead.company || lead.name,
          status: "new",
          notes: lead.use_case,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      await fetchLeads();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create pilot");
    }
  };

  return (
    <div className="min-h-screen bg-[#12151B] text-[#EAEAEA]">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
        body { font-family: 'Inter', sans-serif; }
      `}</style>

      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-semibold">Lead Inbox</h1>
            <p className="text-[#9AA0A6]">Pilot requests and marketing leads</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => downloadLeads("csv")}
              className="text-xs px-3 py-1 rounded-full bg-[#2F3134] hover:bg-[#4A90E2]/20"
            >
              Export CSV
            </button>
            <button
              onClick={() => downloadLeads("json")}
              className="text-xs px-3 py-1 rounded-full bg-[#2F3134] hover:bg-[#4A90E2]/20"
            >
              Export JSON
            </button>
            <a className="text-sm text-[#4A90E2]" href="/landing">← Back</a>
          </div>
        </div>

        {error && (
          <div className="p-4 mb-6 bg-[#EA6E74]/10 border border-[#EA6E74] rounded-2xl text-[#EA6E74]">
            {error}
          </div>
        )}

        <div className="p-6 rounded-3xl bg-[#161B24] border border-[#232A36]">
          {loading ? (
            <div className="text-sm text-[#9AA0A6]">Loading...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[#9AA0A6]">
                    <th className="pb-3">Name</th>
                    <th className="pb-3">Email</th>
                    <th className="pb-3">Company</th>
                    <th className="pb-3">Team</th>
                    <th className="pb-3">Use Case</th>
                    <th className="pb-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {leads.map((lead) => (
                    <tr key={lead.id} className="border-t border-[#232A36]">
                      <td className="py-3 text-[#C4C7C5]">{lead.name}</td>
                      <td className="py-3 text-[#C4C7C5]">{lead.email}</td>
                      <td className="py-3 text-[#C4C7C5]">{lead.company}</td>
                      <td className="py-3 text-[#C4C7C5]">{lead.team_size}</td>
                      <td className="py-3 text-[#C4C7C5]">{lead.use_case}</td>
                      <td className="py-3">
                        <button
                          onClick={() => createPilot(lead)}
                          className="text-xs px-3 py-1 rounded-full bg-[#2F3134] hover:bg-[#4A90E2]/20"
                        >
                          Create Pilot
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
