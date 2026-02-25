"use client";

import { useEffect, useState } from "react";

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

export default function PricingPage() {
  const [plan, setPlan] = useState("starter");
  const [seats, setSeats] = useState(5);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    track("pricing_view", { path: "/pricing" });
  }, []);

  const priceMap: Record<string, number> = {
    starter: 49,
    growth: 129,
    enterprise: 299,
  };

  const estimate = priceMap[plan] * Math.max(seats, 1);

  const startCheckout = async () => {
    setError("");
    setLoading(true);
    try {
      const token = localStorage.getItem("vs_token");
      const res = await fetch(`${API_BASE}/api/billing/checkout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ plan, quantity: seats }),
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
    <div className="min-h-screen bg-[#0F1116] text-[#EAEAEA]">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&display=swap');
        body { font-family: 'Sora', sans-serif; }
      `}</style>

      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="flex items-center justify-between mb-10">
          <div>
            <h1 className="text-4xl font-semibold">Pricing</h1>
            <p className="text-[#9AA0A6] mt-2">Pilot-ready plans for security teams</p>
          </div>
          <a className="text-sm text-[#4A90E2]" href="/landing">← Back</a>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-2xl bg-[#EA6E74]/10 border border-[#EA6E74] text-[#EA6E74] text-sm">
            {error}
          </div>
        )}

        <div className="mb-10 p-6 rounded-3xl bg-[#141721] border border-[#262B38]">
          <div className="text-sm text-[#9AA0A6]">Pricing calculator</div>
          <div className="mt-4 grid md:grid-cols-3 gap-4 items-end">
            <div>
              <label className="text-xs text-[#9AA0A6]">Plan</label>
              <select
                value={plan}
                onChange={(e) => setPlan(e.target.value)}
                className="w-full mt-2 px-3 py-2 rounded-xl bg-[#1B1F2A] border border-[#2C3344]"
              >
                <option value="starter">Starter</option>
                <option value="growth">Growth</option>
                <option value="enterprise">Enterprise</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-[#9AA0A6]">Seats</label>
              <input
                type="number"
                min="1"
                value={seats}
                onChange={(e) => setSeats(Number(e.target.value))}
                className="w-full mt-2 px-3 py-2 rounded-xl bg-[#1B1F2A] border border-[#2C3344]"
              />
            </div>
            <div>
              <div className="text-xs text-[#9AA0A6]">Estimated monthly</div>
              <div className="text-2xl font-semibold mt-2">${estimate}</div>
            </div>
          </div>
          <button
            onClick={startCheckout}
            className="mt-6 px-4 py-2 rounded-full bg-[#4A90E2] text-black"
            disabled={loading}
          >
            {loading ? "Starting checkout..." : "Proceed to Checkout"}
          </button>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          <div className="p-6 rounded-3xl bg-[#141721] border border-[#262B38]">
            <div className="text-xs uppercase text-[#9AA0A6]">Starter</div>
            <div className="text-3xl font-semibold mt-4">$49</div>
            <div className="text-sm text-[#9AA0A6]">per repo / month</div>
            <ul className="mt-4 text-sm text-[#C4C7C5] space-y-2">
              <li>Weekly scans</li>
              <li>Auto-fix PRs</li>
              <li>Email alerts</li>
            </ul>
            <a href="/onboarding" className="mt-6 inline-block px-4 py-2 rounded-full bg-[#4A90E2] text-black">Start Pilot</a>
          </div>

          <div className="p-6 rounded-3xl bg-[#1A1E2A] border border-[#2C3344]">
            <div className="text-xs uppercase text-[#9AA0A6]">Growth</div>
            <div className="text-3xl font-semibold mt-4">$129</div>
            <div className="text-sm text-[#9AA0A6]">per team / month</div>
            <ul className="mt-4 text-sm text-[#C4C7C5] space-y-2">
              <li>Daily scans</li>
              <li>Priority remediation</li>
              <li>Slack alerts</li>
            </ul>
            <a href="/onboarding" className="mt-6 inline-block px-4 py-2 rounded-full bg-[#EA6E74] text-black">Book a Demo</a>
          </div>

          <div className="p-6 rounded-3xl bg-[#141721] border border-[#262B38]">
            <div className="text-xs uppercase text-[#9AA0A6]">Enterprise</div>
            <div className="text-3xl font-semibold mt-4">Custom</div>
            <div className="text-sm text-[#9AA0A6]">SLA + compliance</div>
            <ul className="mt-4 text-sm text-[#C4C7C5] space-y-2">
              <li>Unlimited repos</li>
              <li>Custom policies</li>
              <li>Dedicated support</li>
            </ul>
            <a href="/onboarding" className="mt-6 inline-block px-4 py-2 rounded-full border border-[#2C3344]">Contact Sales</a>
          </div>
        </div>

        {/* Comparison with Competitors */}
        <div className="mt-16 pt-12 border-t border-[#262B38]">
          <div className="mb-8">
            <h2 className="text-3xl font-semibold">How VulnSentinel Compares</h2>
            <p className="text-[#9AA0A6] mt-2">Built for teams who want to fix bugs, not just report them.</p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#262B38]">
                  <th className="text-left py-4 px-4 text-[#9AA0A6] font-semibold">Feature</th>
                  <th className="text-left py-4 px-4 text-[#9AA0A6] font-semibold">Snyk / SonarQube</th>
                  <th className="text-left py-4 px-4 text-[#4A90E2] font-semibold">VulnSentinel</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[#1F2430]">
                  <td className="py-4 px-4 font-semibold">Target Audience</td>
                  <td className="py-4 px-4 text-[#B6BCC8]">Enterprises (Banks, Netflix)</td>
                  <td className="py-4 px-4 text-[#7FD88C]">Agencies, Freelancers, Startups</td>
                </tr>
                <tr className="border-b border-[#1F2430]">
                  <td className="py-4 px-4 font-semibold">Setup</td>
                  <td className="py-4 px-4 text-[#B6BCC8]">Complex (DevOps required)</td>
                  <td className="py-4 px-4 text-[#7FD88C]">1-Click GitHub App</td>
                </tr>
                <tr className="border-b border-[#1F2430]">
                  <td className="py-4 px-4 font-semibold">Main Job</td>
                  <td className="py-4 px-4 text-[#B6BCC8]">Report Bugs</td>
                  <td className="py-4 px-4 text-[#7FD88C]">Fix Bugs (Auto-PR)</td>
                </tr>
                <tr className="border-b border-[#1F2430]">
                  <td className="py-4 px-4 font-semibold">Unique Feature</td>
                  <td className="py-4 px-4 text-[#B6BCC8]">Compliance</td>
                  <td className="py-4 px-4 text-[#7FD88C]">IP Protection (Code Theft Tracking)</td>
                </tr>
                <tr>
                  <td className="py-4 px-4 font-semibold">Pricing</td>
                  <td className="py-4 px-4 text-[#B6BCC8]">$1000s/month</td>
                  <td className="py-4 px-4 text-[#7FD88C]">$29 - $49/month</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="mt-8 p-6 rounded-3xl bg-[#141721] border border-[#262B38]">
            <div className="grid md:grid-cols-3 gap-6">
              <div>
                <div className="text-[#4A90E2] font-semibold mb-2">What's Different</div>
                <ul className="text-sm text-[#B6BCC8] space-y-2">
                  <li>✓ Auto-fix with AI</li>
                  <li>✓ Direct PR generation</li>
                  <li>✓ Code theft protection</li>
                </ul>
              </div>
              <div>
                <div className="text-[#4A90E2] font-semibold mb-2">Who We're For</div>
                <ul className="text-sm text-[#B6BCC8] space-y-2">
                  <li>✓ Growing startups</li>
                  <li>✓ Agencies & freelancers</li>
                  <li>✓ Teams with limited DevOps</li>
                </ul>
              </div>
              <div>
                <div className="text-[#4A90E2] font-semibold mb-2">No Complex Setup</div>
                <ul className="text-sm text-[#B6BCC8] space-y-2">
                  <li>✓ Install GitHub App</li>
                  <li>✓ Authorize repo access</li>
                  <li>✓ Scanning begins immediately</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
