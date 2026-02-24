"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function ScheduleEditor() {
  const [reminderDays, setReminderDays] = useState("3,7,14");
  const [status, setStatus] = useState<"idle" | "saved" | "error">("idle");

  const token = typeof window !== "undefined" ? localStorage.getItem("vs_token") : "";

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/settings/pilot-reminder-days`, {
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });
        if (!res.ok) {
          return;
        }
        const data = await res.json();
        if (data.reminder_days) {
          setReminderDays(data.reminder_days);
        }
      } catch {
        // ignore
      }
    };
    load();
  }, [token]);

  const save = async () => {
    setStatus("idle");
    try {
      const res = await fetch(`${API_BASE}/api/settings/pilot-reminder-days`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ reminder_days: reminderDays }),
      });
      if (!res.ok) {
        setStatus("error");
        return;
      }
      setStatus("saved");
    } catch {
      setStatus("error");
    }
  };

  return (
    <div className="p-4 rounded-2xl bg-[#1B212C] border border-[#2A3343]">
      <div className="text-sm text-[#9AA0A6]">Reminder Schedule</div>
      <div className="mt-3 flex flex-wrap gap-3 items-center">
        <input
          type="text"
          value={reminderDays}
          onChange={(e) => setReminderDays(e.target.value)}
          className="px-3 py-2 rounded-xl bg-[#11151C] border border-[#2A3343] text-sm"
          placeholder="3,7,14"
        />
        <button
          onClick={save}
          className="text-xs px-3 py-1 rounded-full bg-[#4A90E2] text-black"
        >
          Save schedule
        </button>
        {status === "saved" && <span className="text-xs text-[#72CFA1]">Saved</span>}
        {status === "error" && <span className="text-xs text-[#EA6E74]">Failed</span>}
      </div>
      <div className="text-xs text-[#6D768A] mt-2">Days after pilot start to send reminders.</div>
    </div>
  );
}
