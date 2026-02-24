"use client";

import { useEffect, useState } from "react";
import ScheduleEditor from "./ScheduleEditor";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface PilotRecord {
  pilot_id: string;
  lead_email: string;
  company: string;
  status: string;
  notes: string;
  last_reminded_at: string | null;
  reminder_count: number;
  created_at: string;
  updated_at: string;
}

export default function PilotsPage() {
  const [pilots, setPilots] = useState<PilotRecord[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const token = typeof window !== "undefined" ? localStorage.getItem("vs_token") : "";

  const fetchPilots = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/pilots`, {
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
      setPilots(data.pilots || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load pilots");
    } finally {
      setLoading(false);
    }
  };

  const downloadPilots = async (format: "csv" | "json") => {
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/pilots/export?format=${format}`, {
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
      link.download = `pilots.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download pilots");
    }
  };

  const remindPilot = async (pilot: PilotRecord) => {
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/pilots/${pilot.pilot_id}/remind`, {
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send reminder");
    }
  };

  const runScheduledReminders = async () => {
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/pilots/reminders/run`, {
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
      await fetchPilots();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run reminders");
    }
  };

  useEffect(() => {
    fetchPilots();
  }, []);

  const updatePilot = async (pilot: PilotRecord, status: string, notes: string) => {
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/pilots/${pilot.pilot_id}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ status, notes }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      await fetchPilots();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update pilot");
    }
  };

  return (
    <div className="min-h-screen bg-[#12151B] text-[#EAEAEA]">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
        body { font-family: 'Inter', sans-serif; }
      `}</style>

      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className="mb-6">
          <ScheduleEditor />
        </div>

        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-semibold">Pilot Status</h1>
            <p className="text-[#9AA0A6]">Track pilot outcomes and follow-ups</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => downloadPilots("csv")}
              className="text-xs px-3 py-1 rounded-full bg-[#2F3134] hover:bg-[#4A90E2]/20"
            >
              Export CSV
            </button>
            <button
              onClick={() => downloadPilots("json")}
              className="text-xs px-3 py-1 rounded-full bg-[#2F3134] hover:bg-[#4A90E2]/20"
            >
              Export JSON
            </button>
            <button
              onClick={runScheduledReminders}
              className="text-xs px-3 py-1 rounded-full bg-[#2F3134] hover:bg-[#72CFA1]/20"
            >
              Run Reminders
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
            <div className="space-y-4">
              {pilots.map((pilot) => (
                <div key={pilot.pilot_id} className="p-4 rounded-2xl bg-[#1C2230]">
                  <div className="flex flex-wrap justify-between gap-4">
                    <div>
                      <div className="text-sm text-[#9AA0A6]">{pilot.company}</div>
                      <div className="text-base font-semibold">{pilot.lead_email}</div>
                    </div>
                    <div className="text-sm text-[#9AA0A6]">Status: {pilot.status}</div>
                    <div className="text-xs text-[#9AA0A6]">Updated: {pilot.updated_at}</div>
                    <div className="text-xs text-[#9AA0A6]">
                      Reminders: {pilot.reminder_count || 0}
                    </div>
                    <div className="text-xs text-[#9AA0A6]">
                      Last reminder: {pilot.last_reminded_at || "-"}
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {["new", "qualified", "pilot", "converted", "churned"].map((status) => (
                      <button
                        key={status}
                        onClick={() => updatePilot(pilot, status, pilot.notes)}
                        className={`text-xs px-3 py-1 rounded-full ${
                          pilot.status === status
                            ? "bg-[#4A90E2] text-black"
                            : "bg-[#2F3134] hover:bg-[#4A90E2]/20"
                        }`}
                      >
                        {status}
                      </button>
                    ))}
                    <button
                      onClick={() => remindPilot(pilot)}
                      className="text-xs px-3 py-1 rounded-full bg-[#2F3134] hover:bg-[#72CFA1]/20"
                    >
                      Send Reminder
                    </button>
                  </div>
                  <textarea
                    value={pilot.notes}
                    onChange={(e) => updatePilot(pilot, pilot.status, e.target.value)}
                    className="w-full mt-3 px-3 py-2 rounded-xl bg-[#141A22] border border-[#242C3A] text-sm"
                    placeholder="Notes"
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
