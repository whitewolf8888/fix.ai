"use client";

import { useState, useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface Plan {
  id: string;
  name: string;
  price: number;
  currency: string;
  interval: string;
  features: string[];
  popular?: boolean;
}

interface Subscription {
  active: boolean;
  plan: string;
  status: string;
  trial_days_remaining?: number;
  features?: {
    max_scans: number;
    max_repositories: number;
    remediation_enabled: boolean;
    priority_support: boolean;
  };
}

interface Invoice {
  id: string;
  date: string;
  amount: number;
  status: string;
  invoice_url: string;
}

export default function BillingPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [activeTab, setActiveTab] = useState<"plans" | "subscription" | "invoices">("subscription");

  useEffect(() => {
    fetchBillingData();
  }, []);

  const fetchBillingData = async () => {
    const token = localStorage.getItem("vs_token");
    const headers = {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    try {
      // Fetch subscription details
      const subRes = await fetch(`${API_BASE}/api/billing/subscription`, { headers });
      if (subRes.ok) {
        const subData = await subRes.json();
        setSubscription(subData);
      }

      // Fetch available plans
      const plansRes = await fetch(`${API_BASE}/api/billing/plans`, { headers });
      if (plansRes.ok) {
        const plansData = await plansRes.json();
        setPlans(plansData.plans || []);
      }

      // Fetch invoices
      const invRes = await fetch(`${API_BASE}/api/billing/invoices`, { headers });
      if (invRes.ok) {
        const invData = await invRes.json();
        setInvoices(invData.invoices || []);
      }
    } catch (err) {
      console.error("Failed to fetch billing data:", err);
    }
  };

  const startCheckout = async (planId: string) => {
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
        body: JSON.stringify({ plan: planId, quantity: 1 }),
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

      <div className="max-w-7xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Billing & Subscription</h1>
            <p className="text-[#C4C7C5]">Manage your VulnSentinel plan and billing details</p>
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

        {/* Tabs */}
        <div className="flex gap-4 mb-6 border-b border-[#2F3134]">
          <button
            onClick={() => setActiveTab("subscription")}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === "subscription"
                ? "text-[#8AB4F8] border-b-2 border-[#8AB4F8]"
                : "text-[#C4C7C5] hover:text-[#E3E3E3]"
            }`}
          >
            Current Subscription
          </button>
          <button
            onClick={() => setActiveTab("plans")}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === "plans"
                ? "text-[#8AB4F8] border-b-2 border-[#8AB4F8]"
                : "text-[#C4C7C5] hover:text-[#E3E3E3]"
            }`}
          >
            Available Plans
          </button>
          <button
            onClick={() => setActiveTab("invoices")}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === "invoices"
                ? "text-[#8AB4F8] border-b-2 border-[#8AB4F8]"
                : "text-[#C4C7C5] hover:text-[#E3E3E3]"
            }`}
          >
            Billing History
          </button>
        </div>

        {/* Current Subscription Tab */}
        {activeTab === "subscription" && subscription && (
          <div className="space-y-6">
            <div className="p-6 bg-[#1E1F20] rounded-2xl border border-[#2F3134]">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="text-2xl font-semibold capitalize">{subscription.plan} Plan</h2>
                  <p className={`text-sm mt-1 ${
                    subscription.active ? "text-[#81C995]" : "text-[#C4C7C5]"
                  }`}>
                    Status: {subscription.status}
                  </p>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  subscription.active
                    ? "bg-[#81C995]/10 text-[#81C995]"
                    : "bg-[#C4C7C5]/10 text-[#C4C7C5]"
                }`}>
                  {subscription.active ? "Active" : "Inactive"}
                </span>
              </div>

              {subscription.trial_days_remaining !== undefined && (
                <div className="p-4 bg-[#8AB4F8]/10 border border-[#8AB4F8] rounded-xl mb-4">
                  <p className="text-[#8AB4F8] text-sm">
                    🎉 Trial: {subscription.trial_days_remaining} days remaining
                  </p>
                </div>
              )}

              {subscription.features && (
                <div className="grid grid-cols-2 gap-4 mt-6">
                  <div className="p-4 bg-[#131314] rounded-xl">
                    <p className="text-[#C4C7C5] text-sm">Max Scans/Month</p>
                    <p className="text-2xl font-semibold mt-1">{subscription.features.max_scans}</p>
                  </div>
                  <div className="p-4 bg-[#131314] rounded-xl">
                    <p className="text-[#C4C7C5] text-sm">Repositories</p>
                    <p className="text-2xl font-semibold mt-1">{subscription.features.max_repositories}</p>
                  </div>
                  <div className="p-4 bg-[#131314] rounded-xl">
                    <p className="text-[#C4C7C5] text-sm">Auto Remediation</p>
                    <p className="text-xl font-semibold mt-1">
                      {subscription.features.remediation_enabled ? "✅ Enabled" : "❌ Disabled"}
                    </p>
                  </div>
                  <div className="p-4 bg-[#131314] rounded-xl">
                    <p className="text-[#C4C7C5] text-sm">Priority Support</p>
                    <p className="text-xl font-semibold mt-1">
                      {subscription.features.priority_support ? "✅ Enabled" : "❌ Disabled"}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Available Plans Tab */}
        {activeTab === "plans" && (
          <div className="grid md:grid-cols-3 gap-6">
            {plans.map((plan) => (
              <div
                key={plan.id}
                className={`p-6 rounded-2xl border ${
                  plan.popular
                    ? "bg-gradient-to-b from-[#8AB4F8]/10 to-[#1E1F20] border-[#8AB4F8]"
                    : "bg-[#1E1F20] border-[#2F3134]"
                }`}
              >
                {plan.popular && (
                  <span className="inline-block px-3 py-1 rounded-full bg-[#8AB4F8] text-[#131314] text-xs font-semibold mb-4">
                    MOST POPULAR
                  </span>
                )}
                <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
                <div className="flex items-baseline mb-6">
                  <span className="text-4xl font-bold">${plan.price}</span>
                  <span className="text-[#C4C7C5] ml-2">/{plan.interval}</span>
                </div>
                <ul className="space-y-3 mb-6">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-start">
                      <svg className="w-5 h-5 text-[#81C995] mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      <span className="text-[#C4C7C5] text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => startCheckout(plan.id)}
                  disabled={loading}
                  className={`w-full px-6 py-3 rounded-full font-medium transition-all ${
                    plan.popular
                      ? "gradient-gemini text-white hover:opacity-90"
                      : "bg-[#2F3134] text-[#E3E3E3] hover:bg-[#3A3D40]"
                  } disabled:opacity-60`}
                >
                  {loading ? "Processing..." : "Select Plan"}
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Billing History Tab */}
        {activeTab === "invoices" && (
          <div className="bg-[#1E1F20] rounded-2xl border border-[#2F3134] overflow-hidden">
            {invoices.length === 0 ? (
              <div className="p-12 text-center">
                <p className="text-[#C4C7C5]">No invoices yet</p>
              </div>
            ) : (
              <table className="w-full">
                <thead className="bg-[#131314] border-b border-[#2F3134]">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-semibold">Invoice ID</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold">Date</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold">Amount</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold">Status</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((invoice) => (
                    <tr key={invoice.id} className="border-b border-[#2F3134] last:border-0">
                      <td className="px-6 py-4 text-sm font-mono">{invoice.id}</td>
                      <td className="px-6 py-4 text-sm">{invoice.date}</td>
                      <td className="px-6 py-4 text-sm font-semibold">${invoice.amount.toFixed(2)}</td>
                      <td className="px-6 py-4 text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          invoice.status === "paid"
                            ? "bg-[#81C995]/10 text-[#81C995]"
                            : "bg-[#EA6E74]/10 text-[#EA6E74]"
                        }`}>
                          {invoice.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <a
                          href={invoice.invoice_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[#8AB4F8] hover:underline"
                        >
                          View Invoice →
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
