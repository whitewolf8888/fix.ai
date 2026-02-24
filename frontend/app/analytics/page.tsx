"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const token = localStorage.getItem("vs_token");
        const res = await fetch(`${API_BASE}/api/analytics/summary`, {
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
        setSummary(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load analytics");
      }
    };
    load();
  }, []);

  return (
    <div className="min-h-screen bg-[#131314] text-[#E3E3E3] font-sans">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap');
        body { font-family: 'Outfit', sans-serif; }
      `}</style>

      <div className="max-w-5xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Analytics</h1>
            <p className="text-[#C4C7C5]">Security activity summary</p>
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

        {!summary && !error && (
          <div className="p-6 bg-[#1E1F20] rounded-2xl border border-[#2F3134]">
            Loading analytics...
          </div>
        )}

        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-6 bg-[#1E1F20] rounded-2xl border border-[#2F3134]">
              <h2 className="text-lg font-semibold mb-3">Totals</h2>
              <div className="space-y-2 text-sm text-[#C4C7C5]">
                {Object.entries(summary.totals || {}).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span>{key}</span>
                    <span className="text-[#E3E3E3] font-semibold">{value as any}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-6 bg-[#1E1F20] rounded-2xl border border-[#2F3134]">
              <h2 className="text-lg font-semibold mb-3">Last {summary.window_hours}h</h2>
              <div className="space-y-2 text-sm text-[#C4C7C5]">
                {Object.entries(summary.recent || {}).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span>{key}</span>
                    <span className="text-[#E3E3E3] font-semibold">{value as any}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
