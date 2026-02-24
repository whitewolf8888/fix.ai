"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function AuthPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("viewer");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const submit = async () => {
    setError("");
    setMessage("");

    try {
      if (mode === "register") {
        const res = await fetch(`${API_BASE}/api/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password, role }),
        });
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || `HTTP ${res.status}`);
        }
        setMessage("Registered successfully. Now login.");
        setMode("login");
        return;
      }

      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      localStorage.setItem("vs_token", data.access_token);
      setMessage("Login successful. Token saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    }
  };

  return (
    <div className="min-h-screen bg-[#131314] text-[#E3E3E3] font-sans">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap');
        body { font-family: 'Outfit', sans-serif; }
      `}</style>

      <div className="max-w-md mx-auto px-6 py-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold">Authentication</h1>
          <p className="text-[#C4C7C5]">Access secure API endpoints</p>
        </div>

        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setMode("login")}
            className={`px-4 py-2 rounded-full text-sm ${
              mode === "login" ? "bg-[#A87FFB] text-white" : "bg-[#1E1F20]"
            }`}
          >
            Login
          </button>
          <button
            onClick={() => setMode("register")}
            className={`px-4 py-2 rounded-full text-sm ${
              mode === "register" ? "bg-[#A87FFB] text-white" : "bg-[#1E1F20]"
            }`}
          >
            Register
          </button>
        </div>

        <div className="p-6 bg-[#1E1F20] rounded-2xl border border-[#2F3134] space-y-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-3 rounded-2xl bg-[#282A2C] text-[#E3E3E3] border-none focus:ring-1 focus:ring-[#A87FFB] text-sm"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-3 rounded-2xl bg-[#282A2C] text-[#E3E3E3] border-none focus:ring-1 focus:ring-[#A87FFB] text-sm"
          />

          {mode === "register" && (
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full px-4 py-3 rounded-2xl bg-[#282A2C] text-[#E3E3E3] border-none text-sm"
            >
              <option value="viewer">viewer</option>
              <option value="analyst">analyst</option>
              <option value="admin">admin</option>
            </select>
          )}

          <button
            onClick={submit}
            className="w-full gradient-gemini text-white py-3 rounded-full font-semibold hover:opacity-90"
          >
            {mode === "login" ? "Login" : "Register"}
          </button>

          {message && (
            <div className="p-3 rounded-xl bg-[#72CFA1]/10 text-[#72CFA1] text-sm">
              {message}
            </div>
          )}
          {error && (
            <div className="p-3 rounded-xl bg-[#EA6E74]/10 text-[#EA6E74] text-sm">
              {error}
            </div>
          )}
        </div>

        <a
          href="/"
          className="inline-block mt-6 text-sm text-[#C4C7C5] hover:text-[#E3E3E3]"
        >
          ← Back to Dashboard
        </a>
      </div>
    </div>
  );
}
