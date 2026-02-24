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

export default function SecurityPage() {
  useEffect(() => {
    track("security_view", { path: "/security" });
  }, []);

  return (
    <div className="min-h-screen bg-[#0B0C10] text-[#EAEAEA]">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Work+Sans:wght@400;600;700&display=swap');
        body { font-family: 'Work Sans', sans-serif; }
      `}</style>

      <div className="max-w-5xl mx-auto px-6 py-12">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-semibold">Security Posture</h1>
            <p className="text-[#9AA0A6]">Controls and safeguards for enterprise teams</p>
          </div>
          <a className="text-sm text-[#4A90E2]" href="/landing">← Back</a>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div className="p-6 rounded-3xl bg-[#141721] border border-[#262B38]">
            <h2 className="text-lg font-semibold">Access Control</h2>
            <ul className="text-sm text-[#C4C7C5] mt-3 space-y-2">
              <li>Role-based access control (RBAC).</li>
              <li>License enforcement with IP thresholds.</li>
              <li>Audit logs and usage tracking.</li>
            </ul>
          </div>
          <div className="p-6 rounded-3xl bg-[#141721] border border-[#262B38]">
            <h2 className="text-lg font-semibold">Data Handling</h2>
            <ul className="text-sm text-[#C4C7C5] mt-3 space-y-2">
              <li>Encrypted secrets via environment variables.</li>
              <li>Minimal data retention by configuration.</li>
              <li>Secure webhook validation for GitHub.</li>
            </ul>
          </div>
          <div className="p-6 rounded-3xl bg-[#141721] border border-[#262B38]">
            <h2 className="text-lg font-semibold">Infrastructure</h2>
            <ul className="text-sm text-[#C4C7C5] mt-3 space-y-2">
              <li>Dockerized services and health checks.</li>
              <li>Rate limiting and security headers.</li>
              <li>Dedicated worker queues for scan tasks.</li>
            </ul>
          </div>
          <div className="p-6 rounded-3xl bg-[#141721] border border-[#262B38]">
            <h2 className="text-lg font-semibold">Incident Response</h2>
            <ul className="text-sm text-[#C4C7C5] mt-3 space-y-2">
              <li>Alerting via Slack or email.</li>
              <li>License anomaly detection.</li>
              <li>Support SLAs for enterprise customers.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
