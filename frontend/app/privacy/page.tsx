"use client";

import { useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function track(event: string, properties: Record<string, any> = {}) {
  try {
    await fetch(`${API_BASE}/api/marketing/track`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event, properties }),
    });
  } catch {
    // Ignore tracking errors
  }
}

export default function PrivacyPage() {
  useEffect(() => {
    track("privacy_view", { path: "/privacy" });
  }, []);

  return (
    <div className="min-h-screen bg-[#0F1116] text-[#EAEAEA]">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
        body { font-family: 'Inter', sans-serif; }
      `}</style>

      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-semibold">Privacy</h1>
            <p className="text-[#9AA0A6]">How we handle your data</p>
          </div>
          <a className="text-sm text-[#4A90E2]" href="/landing">← Back</a>
        </div>

        <div className="space-y-6 text-sm text-[#C4C7C5]">
          <div className="p-6 rounded-3xl bg-[#151925] border border-[#242B3B]">
            We only process data needed to scan repositories and generate remediation suggestions.
            We do not sell customer data.
          </div>
          <div className="p-6 rounded-3xl bg-[#151925] border border-[#242B3B]">
            Logs and analytics events are stored for service reliability and product improvement.
            Access is restricted to authorized staff.
          </div>
          <div className="p-6 rounded-3xl bg-[#151925] border border-[#242B3B]">
            You can request data removal or export at any time. Contact support to initiate requests.
          </div>
        </div>
      </div>
    </div>
  );
}
