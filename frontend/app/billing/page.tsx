"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function BillingPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const startCheckout = async () => {
    setLoading(true);
    setError("");

    try {
      const token = localStorage.getItem("vs_token");
      const res = await fetch(`${API_BASE}/api/billing/checkout`, {
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
      const data = await res.json();
      window.location.href = data.checkout_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start checkout");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#131314] text-[#E3E3E3] font-sans">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap');
        body { font-family: 'Outfit', sans-serif; }
      `}</style>

      <div className="max-w-4xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Billing</h1>
            <p className="text-[#C4C7C5]">Manage your VulnSentinel subscription</p>
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

        <div className="p-6 bg-[#1E1F20] rounded-2xl border border-[#2F3134]">
          <h2 className="text-xl font-semibold mb-2">VulnSentinel Pro</h2>
          <p className="text-[#C4C7C5] mb-4">
            Unlimited scans, priority remediation, and advanced analytics.
          </p>
          <button
            onClick={startCheckout}
            disabled={loading}
            className="gradient-gemini text-white px-6 py-2 rounded-full hover:opacity-90 disabled:opacity-60"
          >
            {loading ? "Starting checkout..." : "Upgrade Now"}
          </button>
        </div>
      </div>
    </div>
  );
}
