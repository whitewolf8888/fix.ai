"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface LicenseRecord {
  license_key: string;
  owner_email: string;
  status: string;
  allowed_ips: string[];
  ip_history: { ip: string; first_seen: string; last_seen: string; count: number }[];
  max_ips: number;
  soft_lock: boolean;
  created_at: string;
  updated_at: string;
}

export default function LicensesPage() {
  const [licenses, setLicenses] = useState<LicenseRecord[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [licenseKey, setLicenseKey] = useState("");
  const [ownerEmail, setOwnerEmail] = useState("");
  const [maxIps, setMaxIps] = useState("0");
  const [softLock, setSoftLock] = useState(true);
  const [selectedHistory, setSelectedHistory] = useState<LicenseRecord | null>(null);

  const token = typeof window !== "undefined" ? localStorage.getItem("vs_token") : "";

  const fetchLicenses = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/license`, {
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
      setLicenses(data.licenses || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load licenses");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLicenses();
  }, []);

  const createLicense = async () => {
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/license`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          license_key: licenseKey,
          owner_email: ownerEmail,
          status: "active",
          allowed_ips: [],
          max_ips: Number(maxIps) || 0,
          soft_lock: softLock,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      setLicenseKey("");
      setOwnerEmail("");
      setMaxIps("0");
      setSoftLock(true);
      await fetchLicenses();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create license");
    }
  };

  const revokeLicense = async (key: string) => {
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/license/${key}/revoke`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      await fetchLicenses();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to revoke license");
    }
  };

  return (
    <div className="min-h-screen bg-[#131314] text-[#E3E3E3] font-sans">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap');
        body { font-family: 'Outfit', sans-serif; }
      `}</style>

      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Licenses</h1>
            <p className="text-[#C4C7C5]">Create and manage client licenses</p>
          </div>
          <a
            href="/"
            className="px-4 py-2 rounded-full bg-[#1E1F20] border border-[#2F3134] text-sm hover:bg-[#2A2C2F]"
          >
            Back to Dashboard
          </a>
        </div>

        {error && (
          <div className="p-4 mb-6 bg-[#EA6E74]/10 border border-[#EA6E74] rounded-2xl text-[#EA6E74]">
            {error}
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-6 mb-10">
          <div className="p-6 bg-[#1E1F20] rounded-2xl border border-[#2F3134]">
            <h2 className="text-lg font-semibold mb-4">Create License</h2>
            <input
              type="text"
              placeholder="License Key (client_ABC_123)"
              value={licenseKey}
              onChange={(e) => setLicenseKey(e.target.value)}
              className="w-full mb-3 px-4 py-3 rounded-2xl bg-[#282A2C] text-[#E3E3E3] border-none text-sm"
            />
            <input
              type="email"
              placeholder="Owner Email"
              value={ownerEmail}
              onChange={(e) => setOwnerEmail(e.target.value)}
              className="w-full mb-4 px-4 py-3 rounded-2xl bg-[#282A2C] text-[#E3E3E3] border-none text-sm"
            />
            <div className="flex gap-3 mb-4">
              <input
                type="number"
                min="0"
                placeholder="Max IPs (0 = unlimited)"
                value={maxIps}
                onChange={(e) => setMaxIps(e.target.value)}
                className="w-full px-4 py-3 rounded-2xl bg-[#282A2C] text-[#E3E3E3] border-none text-sm"
              />
              <label className="flex items-center gap-2 text-sm text-[#C4C7C5]">
                <input
                  type="checkbox"
                  checked={softLock}
                  onChange={(e) => setSoftLock(e.target.checked)}
                />
                Soft-lock
              </label>
            </div>
            <button
              onClick={createLicense}
              className="gradient-gemini text-white px-6 py-2 rounded-full hover:opacity-90"
            >
              Create
            </button>
          </div>

          <div className="p-6 bg-[#1E1F20] rounded-2xl border border-[#2F3134]">
            <h2 className="text-lg font-semibold mb-4">Tips</h2>
            <ul className="text-sm text-[#C4C7C5] space-y-2">
              <li>Use unique license keys per client.</li>
              <li>Revoke keys for expired subscriptions.</li>
              <li>Set IP thresholds and choose soft-lock mode.</li>
              <li>New IPs are flagged in logs and alerts.</li>
            </ul>
          </div>
        </div>

        <div className="p-6 bg-[#1E1F20] rounded-2xl border border-[#2F3134]">
          <h2 className="text-lg font-semibold mb-4">Active Licenses</h2>
          {loading ? (
            <div className="text-sm text-[#C4C7C5]">Loading...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[#9AA0A6]">
                    <th className="pb-3">Key</th>
                    <th className="pb-3">Owner</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3">Known IPs</th>
                    <th className="pb-3">Max IPs</th>
                    <th className="pb-3">Soft-lock</th>
                    <th className="pb-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {licenses.map((license) => (
                    <tr key={license.license_key} className="border-t border-[#2F3134]">
                      <td className="py-3 font-mono text-xs text-[#C4C7C5]">
                        {license.license_key}
                      </td>
                      <td className="py-3 text-[#C4C7C5]">{license.owner_email}</td>
                      <td className="py-3">
                        <span
                          className={`px-2 py-1 rounded-full text-xs ${
                            license.status === "active"
                              ? "bg-[#72CFA1]/20 text-[#72CFA1]"
                              : "bg-[#EA6E74]/20 text-[#EA6E74]"
                          }`}
                        >
                          {license.status}
                        </span>
                      </td>
                      <td className="py-3 text-[#9AA0A6]">
                        {license.allowed_ips?.length || 0}
                      </td>
                      <td className="py-3 text-[#9AA0A6]">
                        {license.max_ips === 0 ? "Unlimited" : license.max_ips}
                      </td>
                      <td className="py-3 text-[#9AA0A6]">
                        {license.soft_lock ? "Yes" : "No"}
                      </td>
                      <td className="py-3">
                        <button
                          onClick={() => setSelectedHistory(license)}
                          className="text-xs px-3 py-1 rounded-full bg-[#2F3134] hover:bg-[#4A90E2]/20 mr-2"
                        >
                          View IPs
                        </button>
                        <button
                          onClick={() => revokeLicense(license.license_key)}
                          className="text-xs px-3 py-1 rounded-full bg-[#2F3134] hover:bg-[#EA6E74]/20"
                        >
                          Revoke
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

      {selectedHistory && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedHistory(null)}
        >
          <div
            className="bg-[#1E1F20] rounded-3xl w-full max-w-3xl max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-[#2F3134] flex justify-between items-center">
              <div>
                <h3 className="text-lg font-semibold">IP History</h3>
                <p className="text-sm text-[#9AA0A6]">{selectedHistory.license_key}</p>
              </div>
              <button
                onClick={() => setSelectedHistory(null)}
                className="text-[#C4C7C5] hover:text-[#E3E3E3]"
              >
                ✕
              </button>
            </div>
            <div className="p-6">
              {selectedHistory.ip_history?.length ? (
                <div className="space-y-3">
                      {selectedHistory.ip_history.map((entry) => (
                    <div
                      key={entry.ip}
                      className="p-4 rounded-2xl bg-[#26282B] flex flex-col md:flex-row md:items-center md:justify-between"
                    >
                      <div className="font-mono text-sm text-[#E3E3E3]">{entry.ip}</div>
                      <div className="text-xs text-[#9AA0A6] mt-2 md:mt-0">
                        First: {entry.first_seen} | Last: {entry.last_seen} | Hits: {entry.count}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-[#9AA0A6]">No IP history yet.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
