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

export default function DemoPage() {
  useEffect(() => {
    track("demo_view", { path: "/demo" });
  }, []);

  return (
    <div className="min-h-screen bg-[#0D1016] text-[#EAEAEA]">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@500;700&family=IBM+Plex+Mono:wght@400;600&display=swap');
        body { font-family: 'Fraunces', serif; }
        .mono { font-family: 'IBM Plex Mono', monospace; }
      `}</style>

      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-semibold">Demo Script</h1>
            <p className="text-[#9AA0A6]">A 6-minute walkthrough you can use for pilots.</p>
          </div>
          <a className="text-sm text-[#4A90E2]" href="/landing">← Back</a>
        </div>

        <div className="space-y-6">
          <div className="p-6 rounded-3xl bg-[#151925] border border-[#242B3B]">
            <h2 className="text-xl font-semibold">1) The Problem</h2>
            <p className="text-[#C4C7C5] mt-2">
              Teams ship vulnerabilities because manual audits do not scale. VulnSentinel automates
              detection and fixes, while keeping the PR review flow developers trust.
            </p>
          </div>
          <div className="p-6 rounded-3xl bg-[#151925] border border-[#242B3B]">
            <h2 className="text-xl font-semibold">2) Live Scan</h2>
            <p className="text-[#C4C7C5] mt-2">
              Paste a repo URL, start a scan, and show findings in under a minute. Highlight a critical
              issue and open the patch preview.
            </p>
          </div>
          <div className="p-6 rounded-3xl bg-[#151925] border border-[#242B3B]">
            <h2 className="text-xl font-semibold">3) Auto-fix PRs</h2>
            <p className="text-[#C4C7C5] mt-2">
              Generate a patch and click “Open PR”. The code review stays in GitHub and teams
              retain full control.
            </p>
          </div>
          <div className="p-6 rounded-3xl bg-[#151925] border border-[#242B3B]">
            <h2 className="text-xl font-semibold">4) Enterprise Controls</h2>
            <p className="text-[#C4C7C5] mt-2">
              Show RBAC, licensing, and analytics pages. Explain how audits and alerts are logged.
            </p>
          </div>
          <div className="p-6 rounded-3xl bg-[#151925] border border-[#242B3B]">
            <h2 className="text-xl font-semibold">5) Close</h2>
            <p className="text-[#C4C7C5] mt-2">
              Confirm next steps: pilot setup, repo access, and timeline for results.
            </p>
          </div>
        </div>

        <div className="mt-8 p-6 rounded-3xl bg-[#111521] border border-[#242B3B]">
          <div className="text-sm mono text-[#9AA0A6]">Demo checklist</div>
          <ul className="mt-3 text-sm text-[#C4C7C5] space-y-2">
            <li>Use a real repo with known findings.</li>
            <li>Show scan time and remediation coverage.</li>
            <li>Collect questions for pilot setup.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
