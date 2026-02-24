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

export default function LandingPage() {
  useEffect(() => {
    track("landing_view", { path: "/landing" });
  }, []);

  return (
    <div className="min-h-screen bg-[#0B0C10] text-[#EAEAEA]">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
        body { font-family: 'Space Grotesk', sans-serif; }
        .mono { font-family: 'JetBrains Mono', monospace; }
        .glow { box-shadow: 0 0 40px rgba(74, 144, 226, 0.2); }
        .hero-bg { background: radial-gradient(circle at top left, rgba(74,144,226,0.25), transparent 40%),
                    radial-gradient(circle at bottom right, rgba(234,110,116,0.2), transparent 35%),
                    linear-gradient(180deg, #0B0C10 0%, #11131A 100%); }
      `}</style>

      <div className="hero-bg">
        <div className="max-w-6xl mx-auto px-6 py-14">
          <div className="flex items-center justify-between">
            <div className="text-sm mono text-[#7C8DB5]">VulnSentinel Enterprise</div>
            <div className="flex gap-3 text-sm">
              <a className="hover:text-white" href="/pricing">Pricing</a>
              <a className="hover:text-white" href="/security">Security</a>
              <a className="hover:text-white" href="/privacy">Privacy</a>
              <a className="hover:text-white" href="/demo">Demo</a>
            </div>
          </div>

          <div className="mt-14 grid md:grid-cols-2 gap-10 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#171A22] text-xs mono text-[#9AA0A6]">
                AI security + auto-fix + GitHub PRs
              </div>
              <h1 className="text-4xl md:text-5xl font-semibold mt-6 leading-tight">
                Stop shipping vulnerabilities. Fix them before they land.
              </h1>
              <p className="text-[#B6BCC8] mt-4 text-lg">
                VulnSentinel scans real repos, generates AI patches, and opens PRs
                your team can review. Built for engineering teams who want speed without risk.
              </p>

              <div className="mt-6 flex flex-wrap gap-3">
                <a
                  href="/onboarding"
                  className="px-5 py-3 rounded-full bg-[#4A90E2] text-black font-semibold glow"
                >
                  Start Pilot
                </a>
                <a
                  href="/demo"
                  className="px-5 py-3 rounded-full border border-[#2D3240] text-[#EAEAEA]"
                >
                  Watch Demo
                </a>
              </div>

              <div className="mt-8 grid grid-cols-3 gap-4">
                <div className="p-4 rounded-2xl bg-[#141721]">
                  <div className="text-2xl font-semibold">30m</div>
                  <div className="text-xs text-[#9AA0A6]">Setup time</div>
                </div>
                <div className="p-4 rounded-2xl bg-[#141721]">
                  <div className="text-2xl font-semibold">80%</div>
                  <div className="text-xs text-[#9AA0A6]">Auto-fix coverage</div>
                </div>
                <div className="p-4 rounded-2xl bg-[#141721]">
                  <div className="text-2xl font-semibold">3x</div>
                  <div className="text-xs text-[#9AA0A6]">Faster remediation</div>
                </div>
              </div>
            </div>

            <div className="p-6 rounded-3xl bg-[#10131A] border border-[#1F2430]">
              <div className="text-xs mono text-[#9AA0A6]">Live Scan Preview</div>
              <div className="mt-4 space-y-3">
                <div className="p-3 rounded-xl bg-[#171B24]">
                  <div className="text-sm">Finding: SQL Injection</div>
                  <div className="text-xs text-[#9AA0A6]">/api/orders.py:74</div>
                </div>
                <div className="p-3 rounded-xl bg-[#171B24]">
                  <div className="text-sm">Patch: Parameterized query</div>
                  <div className="text-xs text-[#9AA0A6]">PR ready in 42s</div>
                </div>
                <div className="p-3 rounded-xl bg-[#171B24]">
                  <div className="text-sm">Action: Open PR</div>
                  <div className="text-xs text-[#9AA0A6]">Review + merge</div>
                </div>
              </div>
              <a
                href="/onboarding"
                className="mt-6 inline-flex items-center gap-2 text-sm text-[#4A90E2]"
              >
                Book a 15-min pilot call →
              </a>
            </div>
          </div>

          <div className="mt-16 grid md:grid-cols-3 gap-6">
            <div className="p-6 rounded-2xl bg-[#121520] border border-[#1F2430]">
              <h3 className="text-lg font-semibold">AI remediation</h3>
              <p className="text-[#9AA0A6] mt-2">Generate safe patches with guardrails and context.</p>
            </div>
            <div className="p-6 rounded-2xl bg-[#121520] border border-[#1F2430]">
              <h3 className="text-lg font-semibold">Enterprise controls</h3>
              <p className="text-[#9AA0A6] mt-2">Auth, RBAC, audit logs, licensing, and usage analytics.</p>
            </div>
            <div className="p-6 rounded-2xl bg-[#121520] border border-[#1F2430]">
              <h3 className="text-lg font-semibold">GitHub PR workflow</h3>
              <p className="text-[#9AA0A6] mt-2">Ship fixes as reviewable pull requests.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
