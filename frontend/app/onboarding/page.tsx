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

export default function OnboardingPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [teamSize, setTeamSize] = useState("");
  const [useCase, setUseCase] = useState("");
  const [status, setStatus] = useState<"idle" | "sent" | "error">("idle");

  useEffect(() => {
    track("onboarding_view", { path: "/onboarding" });
  }, []);

  const submit = async () => {
    setStatus("idle");
    try {
      const res = await fetch(`${API_BASE}/api/marketing/lead`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, company, team_size: teamSize, use_case: useCase }),
      });
      if (!res.ok) {
        setStatus("error");
        return;
      }
      setStatus("sent");
      track("onboarding_submit", { email, company, team_size: teamSize });
    } catch {
      setStatus("error");
    }
  };

  return (
    <div className="min-h-screen bg-[#0F1116] text-[#EAEAEA]">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700&display=swap');
        body { font-family: 'Manrope', sans-serif; }
      `}</style>

      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-semibold">Pilot Onboarding</h1>
            <p className="text-[#9AA0A6]">Tell us about your team and we will set up a pilot.</p>
          </div>
          <a className="text-sm text-[#4A90E2]" href="/landing">← Back</a>
        </div>

        <div className="p-8 rounded-3xl bg-[#151925] border border-[#242B3B] space-y-4">
          <input
            type="text"
            placeholder="Full name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-4 py-3 rounded-2xl bg-[#1D2230] border border-[#262C3A]"
          />
          <input
            type="email"
            placeholder="Work email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-3 rounded-2xl bg-[#1D2230] border border-[#262C3A]"
          />
          <input
            type="text"
            placeholder="Company"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            className="w-full px-4 py-3 rounded-2xl bg-[#1D2230] border border-[#262C3A]"
          />
          <input
            type="text"
            placeholder="Team size"
            value={teamSize}
            onChange={(e) => setTeamSize(e.target.value)}
            className="w-full px-4 py-3 rounded-2xl bg-[#1D2230] border border-[#262C3A]"
          />
          <textarea
            placeholder="Primary use case"
            value={useCase}
            onChange={(e) => setUseCase(e.target.value)}
            className="w-full px-4 py-3 rounded-2xl bg-[#1D2230] border border-[#262C3A] h-32"
          />

          <button
            onClick={submit}
            className="px-6 py-3 rounded-full bg-[#4A90E2] text-black font-semibold"
          >
            Submit Pilot Request
          </button>

          {status === "sent" && (
            <div className="text-sm text-[#72CFA1]">Thanks! We will reach out within 24 hours.</div>
          )}
          {status === "error" && (
            <div className="text-sm text-[#EA6E74]">Something went wrong. Please try again.</div>
          )}
        </div>
      </div>
    </div>
  );
}
