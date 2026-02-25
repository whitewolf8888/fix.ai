"use client";

import { useState, useEffect, useRef, useCallback } from "react";

// ============================================================================
// API Configuration & Safe Fetching
// ============================================================================

const DEFAULT_API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface ApiFetchOptions extends RequestInit {
  baseOverride?: string;
}

async function apiFetch(
  path: string,
  options: ApiFetchOptions = {},
  baseOverride?: string
): Promise<any> {
  const base = baseOverride || DEFAULT_API_BASE;
  const url = `${base}${path}`;
  const token = typeof window !== "undefined" ? localStorage.getItem("vs_token") : null;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });

    // Check Content-Type before parsing JSON
    const contentType = response.headers.get("Content-Type");
    if (!contentType?.includes("application/json")) {
      throw new Error(
        `Expected JSON but got ${contentType} from ${url} (${response.status})`
      );
    }

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || data.error || `HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    throw error instanceof Error
      ? error
      : new Error(`Failed to fetch ${url}`);
  }
}

// ============================================================================
// Types
// ============================================================================

interface Finding {
  rule_id: string;
  rule_name: string;
  severity: string;
  file_path: string;
  line_start: number;
  code_snippet: string;
  description: string;
  _index?: number;
}

interface PatchReport {
  finding: Finding;
  patched_content?: string;
  patch_error?: string;
  skipped: boolean;
}

interface ScanResponse {
  task_id: string;
  status: string;
  poll_url: string;
}

interface StatusResponse {
  task_id: string;
  status: string;
  findings: any[];
  patch_reports: any[];
  error_message?: string;
}

// ============================================================================
// Diff Modal Component
// ============================================================================

interface DiffModalProps {
  finding: Finding;
  isOpen: boolean;
  onClose: () => void;
  apiBase: string;
}

function DiffModal({ finding, isOpen, onClose, apiBase }: DiffModalProps) {
  const [fileContent, setFileContent] = useState("");
  const [patchState, setPatchState] = useState<
    "idle" | "loading" | "done" | "error"
  >("idle");
  const [patchedCode, setPatchedCode] = useState("");
  const [patchError, setPatchError] = useState("");

  if (!isOpen) return null;

  const handleRemediatClick = async () => {
    setPatchState("loading");

    try {
      const response = await apiFetch(
        "/api/remediate",
        {
          method: "POST",
          body: JSON.stringify({
            task_id: (window as any).currentTaskId,
            finding_index: finding._index || 0,
            file_content: fileContent || undefined,
          }),
        },
        apiBase
      );

      if (response.status === "success") {
        setPatchedCode(response.patched_file_content || "");
        setPatchState("done");
      } else {
        setPatchError(response.patch_error || "Unknown error");
        setPatchState("error");
      }
    } catch (err) {
      setPatchError(err instanceof Error ? err.message : "Failed to generate patch");
      setPatchState("error");
    }
  };

  const handleClose = () => {
    setPatchState("idle");
    setPatchedCode("");
    setPatchError("");
    setFileContent("");
    onClose();
  };

  const vulnerableLines = finding.code_snippet.split("\n").map((line, i) => (
    <div key={i} className="flex font-mono text-xs">
      <span className="w-8 text-right pr-2 text-[#9AA0A6] select-none">
        {finding.line_start + i}
      </span>
      <span className="flex-1 text-[#EA6E74]">{line}</span>
    </div>
  ));

  const patchedLines = patchedCode.split("\n").map((line, i) => (
    <div key={i} className="flex font-mono text-xs">
      <span className="w-8 text-right pr-2 text-[#9AA0A6] select-none">
        {i + 1}
      </span>
      <span className="flex-1 text-[#72CFA1]">{line}</span>
    </div>
  ));

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={handleClose}
    >
      <div
        className="bg-[#1E1F20] rounded-3xl w-full max-w-6xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6 border-b border-[#2F3134]">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-xl font-semibold text-[#E3E3E3]">
              {finding.rule_id}
            </h3>
            <button
              onClick={handleClose}
              className="text-[#C4C7C5] hover:text-[#E3E3E3]"
            >
              ✕
            </button>
          </div>
          <p className="text-[#C4C7C5]">{finding.file_path}</p>
        </div>

        <div className="p-6">
          {patchState === "idle" && (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">✦</div>
              <p className="text-[#C4C7C5] mb-4">
                Paste the full source file (optional) for context-aware patching
              </p>
              <textarea
                value={fileContent}
                onChange={(e) => setFileContent(e.target.value)}
                placeholder="# Paste full Python file here (optional)"
                className="w-full h-48 p-4 rounded-2xl bg-[#282A2C] text-[#E3E3E3] font-mono text-sm border-none focus:ring-1 focus:ring-[#A87FFB]"
              />
              <button
                onClick={handleRemediatClick}
                className="gradient-gemini text-white px-6 py-2 rounded-full mt-4 hover:opacity-90 active:scale-95"
              >
                Generate Fix
              </button>
            </div>
          )}

          {patchState === "loading" && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin">⟳</div>
              <span className="ml-3 text-[#C4C7C5]">Generating patch...</span>
            </div>
          )}

          {patchState === "done" && (
            <div className="grid grid-cols-2 gap-6">
              <div>
                <h4 className="font-semibold text-[#E3E3E3] mb-3">Vulnerable</h4>
                <div className="bg-[#0E1012] rounded-2xl p-4 overflow-x-auto">
                  {vulnerableLines}
                </div>
              </div>
              <div>
                <h4 className="font-semibold text-[#E3E3E3] mb-3">Fixed</h4>
                <div className="bg-[#0E1012] rounded-2xl p-4 overflow-x-auto">
                  {patchedLines}
                </div>
              </div>
            </div>
          )}

          {patchState === "error" && (
            <div className="bg-[#EA6E74]/10 border border-[#EA6E74] rounded-2xl p-4 text-[#EA6E74]">
              {patchError}
            </div>
          )}
        </div>

        {patchState === "done" && (
          <div className="p-6 border-t border-[#2F3134] flex gap-3">
            <button
              onClick={() => {
                navigator.clipboard.writeText(patchedCode);
                alert("Patch copied!");
              }}
              className="flex-1 bg-[#2F3134] text-[#E3E3E3] px-4 py-2 rounded-full hover:bg-[#333538]"
            >
              Copy Patch
            </button>
            <button
              onClick={handleClose}
              className="gradient-gemini text-white px-6 py-2 rounded-full hover:opacity-90"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Main Dashboard Component
// ============================================================================

export default function VulnSentinelDashboard() {
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [availableBranches, setAvailableBranches] = useState<string[]>([]);
  const [loadingBranches, setLoadingBranches] = useState(false);
  const [apiBase, setApiBase] = useState(DEFAULT_API_BASE);
  const [apiToken, setApiToken] = useState("");
  const [showApiConfig, setShowApiConfig] = useState(false);
  const [phase, setPhase] = useState<
    "idle" | "submitted" | "polling" | "done" | "error"
  >("idle");
  const [currentTaskId, setCurrentTaskId] = useState("");
  const [findings, setFindings] = useState<Finding[]>([]);
  const [errorMsg, setErrorMsg] = useState("");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [selectedFindingIdx, setSelectedFindingIdx] = useState<number | null>(
    null
  );
  const [prStates, setPrStates] = useState<Record<number, string>>({});
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const elapsedRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setApiToken(localStorage.getItem("vs_token") || "");
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (apiToken) {
      localStorage.setItem("vs_token", apiToken);
    } else {
      localStorage.removeItem("vs_token");
    }
  }, [apiToken]);

  // Fetch available branches when repo URL changes
  useEffect(() => {
    if (!repoUrl.trim() || !repoUrl.includes("github.com")) {
      setAvailableBranches([]);
      return;
    }

    const fetchBranches = async () => {
      setLoadingBranches(true);
      try {
        const result = await apiFetch(
          `/api/branches?repo_url=${encodeURIComponent(repoUrl)}`,
          {},
          apiBase
        );
        if (result.branches && result.branches.length > 0) {
          setAvailableBranches(result.branches);
          // Set to default branch if available
          if (result.default && !branch) {
            setBranch(result.default);
          }
        }
      } catch (err) {
        console.warn("Failed to fetch branches:", err);
        setAvailableBranches([]);
      } finally {
        setLoadingBranches(false);
      }
    };

    const timer = setTimeout(fetchBranches, 500);
    return () => clearTimeout(timer);
  }, [repoUrl, apiBase]);

  (window as any).currentTaskId = currentTaskId;

  const stopPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (elapsedRef.current) clearInterval(elapsedRef.current);
  }, []);

  const startPolling = useCallback((taskId: string) => {
    (window as any).currentTaskId = taskId;

    elapsedRef.current = setInterval(() => {
      setElapsedSeconds((s) => s + 1);
    }, 1000);

    pollRef.current = setInterval(async () => {
      try {
        const status = await apiFetch(`/api/status/${taskId}`, {}, apiBase);

        if (status.status === "completed") {
          setPhase("done");
          setFindings(status.findings || []);
          stopPolling();
        } else if (status.status === "failed") {
          setErrorMsg(status.error_message);
          setPhase("error");
          stopPolling();
        }
      } catch (err) {
        setErrorMsg(
          err instanceof Error ? err.message : "Failed to fetch status"
        );
        setPhase("error");
        stopPolling();
      }
    }, 3000);
  }, [apiBase, stopPolling]);

  const handleStartAudit = useCallback(async () => {
    if (!repoUrl.trim()) {
      setErrorMsg("Please enter a repository URL");
      return;
    }

    setErrorMsg("");
    setPhase("submitted");
    setElapsedSeconds(0);

    try {
      const response: ScanResponse = await apiFetch(
        "/api/scan",
        {
          method: "POST",
          body: JSON.stringify({
            repo_url: repoUrl,
            branch: branch || "main",
            auto_remediate: true,
          }),
        },
        apiBase
      );

      setCurrentTaskId(response.task_id);
      setPhase("polling");
      startPolling(response.task_id);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Failed to start scan";
      
      // Better error messaging for branch issues
      if (errorMsg.includes("not found in repository") || errorMsg.includes("not found")) {
        const branchSuggestion = availableBranches.length > 0 
          ? ` Try: ${availableBranches.slice(0, 3).join(", ")}`
          : "";
        setErrorMsg(`❌ Branch "${branch}" not found.${branchSuggestion}`);
      } else {
        setErrorMsg(`❌ ${errorMsg}`);
      }
      setPhase("error");
    }
  }, [apiBase, branch, repoUrl, startPolling, availableBranches]);

  // Terminal lines for polling phase
  const terminalLines = [
    "  ╔═══════════════════════════════════════╗",
    "  ║      VULNSENTINEL SECURITY AUDIT      ║",
    "  ╚═══════════════════════════════════════╝",
    `  Scanning: ${repoUrl || "[waiting...]"}`,
    `  Branch: ${branch || "main"}`,
    `  Status: Analyzing code...`,
    "",
    `  ✦ Initializing scanner...`,
    `  ✦ Running security analysis...  ▋`,
  ];

  // Severity stats
  const highCount = findings.filter((f) =>
    ["ERROR", "HIGH"].includes(f.severity)
  ).length;
  const mediumCount = findings.filter(
    (f) => f.severity === "WARNING"
  ).length;
  const lowCount = findings.length - highCount - mediumCount;

  return (
    <div className="min-h-screen bg-[#131314] text-[#E3E3E3] font-sans">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Roboto+Mono:wght@400;500&display=swap');
        body { font-family: 'Outfit', sans-serif; }
        .font-mono { font-family: 'Roboto Mono', monospace; }
      `}</style>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">VulnSentinel</h1>
          <p className="text-[#C4C7C5]">
            Enterprise Security Audit Platform
          </p>
        </div>

        <div className="mb-8 flex flex-wrap gap-3">
          <a
            href="/analytics"
            className="px-4 py-2 rounded-full bg-[#1E1F20] border border-[#2F3134] text-sm hover:bg-[#2A2C2F]"
          >
            Analytics
          </a>
          <a
            href="/billing"
            className="px-4 py-2 rounded-full bg-[#1E1F20] border border-[#2F3134] text-sm hover:bg-[#2A2C2F]"
          >
            Billing
          </a>
          <a
            href="/auth"
            className="px-4 py-2 rounded-full bg-[#1E1F20] border border-[#2F3134] text-sm hover:bg-[#2A2C2F]"
          >
            Auth
          </a>
          <a
            href="/licenses"
            className="px-4 py-2 rounded-full bg-[#1E1F20] border border-[#2F3134] text-sm hover:bg-[#2A2C2F]"
          >
            Licenses
          </a>
          <a
            href="/leads"
            className="px-4 py-2 rounded-full bg-[#1E1F20] border border-[#2F3134] text-sm hover:bg-[#2A2C2F]"
          >
            Leads
          </a>
          <a
            href="/pilots"
            className="px-4 py-2 rounded-full bg-[#1E1F20] border border-[#2F3134] text-sm hover:bg-[#2A2C2F]"
          >
            Pilots
          </a>
          <a
            href="/landing"
            className="px-4 py-2 rounded-full bg-[#1E1F20] border border-[#2F3134] text-sm hover:bg-[#2A2C2F]"
          >
            Marketing
          </a>
        </div>

        {/* Input Card */}
        {phase === "idle" || phase === "error" ? (
          <div className="surface-default rounded-3xl p-8 mb-8 border-soft">
            <h2 className="text-xl font-semibold mb-6">Start Security Audit</h2>

            <div className="space-y-4">
              <input
                type="text"
                placeholder="https://github.com/owner/repo"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                className="w-full px-4 py-3 rounded-2xl bg-[#282A2C] text-[#E3E3E3] border-none focus:ring-1 focus:ring-[#A87FFB] font-mono text-sm"
              />

              {availableBranches.length > 0 ? (
                <select
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  className="w-full px-4 py-3 rounded-2xl bg-[#282A2C] text-[#E3E3E3] border-none focus:ring-1 focus:ring-[#A87FFB] font-mono text-sm"
                >
                  {availableBranches.map((b) => (
                    <option key={b} value={b}>
                      {b}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  placeholder={loadingBranches ? "Loading branches..." : "Branch (default: main)"}
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  disabled={loadingBranches}
                  className="w-full px-4 py-3 rounded-2xl bg-[#282A2C] text-[#E3E3E3] border-none focus:ring-1 focus:ring-[#A87FFB] font-mono text-sm disabled:opacity-50"
                />
              )}

              {showApiConfig && (
                <div className="p-4 bg-[#26282B] rounded-2xl space-y-3">
                  <input
                    type="text"
                    placeholder="Backend URL (default: /api via proxy)"
                    value={apiBase}
                    onChange={(e) => setApiBase(e.target.value)}
                    className="w-full px-4 py-3 rounded-2xl bg-[#282A2C] text-[#E3E3E3] border-none focus:ring-1 focus:ring-[#A87FFB] font-mono text-sm"
                  />
                  <input
                    type="password"
                    placeholder="API Token (optional)"
                    value={apiToken}
                    onChange={(e) => setApiToken(e.target.value)}
                    className="w-full px-4 py-3 rounded-2xl bg-[#282A2C] text-[#E3E3E3] border-none focus:ring-1 focus:ring-[#A87FFB] font-mono text-sm"
                  />
                  <button
                    onClick={async () => {
                      try {
                        await apiFetch("/health", {}, apiBase);
                        alert("✓ Backend connected!");
                      } catch {
                        alert("✕ Backend unreachable");
                      }
                    }}
                    className="text-sm px-3 py-1 rounded-full bg-[#2F3134] hover:bg-[#333538]"
                  >
                    Test Connection
                  </button>
                </div>
              )}

              <button
                onClick={() => setShowApiConfig(!showApiConfig)}
                className="text-xs text-[#9AA0A6] hover:text-[#C4C7C5]"
              >
                {showApiConfig ? "Hide" : "Show"} Backend Config
              </button>

              <button
                onClick={handleStartAudit}
                className="w-full gradient-gemini text-white py-3 rounded-full font-semibold hover:opacity-90 active:scale-95"
              >
                Start Audit
              </button>

              {errorMsg && (
                <div className="p-4 bg-[#EA6E74]/10 border border-[#EA6E74] rounded-2xl text-[#EA6E74]">
                  {errorMsg}
                </div>
              )}
            </div>
          </div>
        ) : null}

        {/* Polling Terminal */}
        {phase === "polling" ? (
          <div className="surface-default rounded-3xl p-8 mb-8 font-mono text-sm text-[#4A90E2]">
            {terminalLines.map((line, i) => (
              <div key={i} className="opacity-60 mb-1">
                {line}
              </div>
            ))}
            <div className="mt-4 h-1 bg-[#26282B] rounded-full overflow-hidden">
              <div
                className="h-full gradient-gemini transition-all"
                style={{ width: `${(Math.min(elapsedSeconds, 30) / 30) * 100}%` }}
              />
            </div>
            <p className="text-[#C4C7C5] text-xs mt-2">
              Elapsed: {elapsedSeconds}s
            </p>
          </div>
        ) : null}

        {/* Results */}
        {phase === "done" && findings.length === 0 ? (
          <div className="surface-default rounded-3xl p-12 text-center mb-8 border-soft">
            <div className="text-5xl mb-4">✓</div>
            <h3 className="text-2xl font-semibold mb-2">
              Security Audit Passed
            </h3>
            <p className="text-[#C4C7C5]">
              No vulnerabilities detected. Great work maintaining secure code!
            </p>
          </div>
        ) : phase === "done" && findings.length > 0 ? (
          <>
            {/* Metrics */}
            <div className="grid grid-cols-4 gap-4 mb-8">
              <div className="surface-default rounded-3xl p-4">
                <div className="text-2xl font-bold text-[#EA6E74] pulsing">
                  ●
                </div>
                <p className="text-[#C4C7C5] text-sm mt-1">HIGH</p>
                <p className="text-2xl font-bold">{highCount}</p>
              </div>
              <div className="surface-default rounded-3xl p-4">
                <div className="text-2xl font-bold text-[#F4B183]">●</div>
                <p className="text-[#C4C7C5] text-sm mt-1">MEDIUM</p>
                <p className="text-2xl font-bold">{mediumCount}</p>
              </div>
              <div className="surface-default rounded-3xl p-4">
                <div className="text-2xl font-bold text-[#FFE082]">●</div>
                <p className="text-[#C4C7C5] text-sm mt-1">LOW</p>
                <p className="text-2xl font-bold">{lowCount}</p>
              </div>
              <div className="surface-default rounded-3xl p-4">
                <div className="text-2xl font-bold text-[#72CFA1]">●</div>
                <p className="text-[#C4C7C5] text-sm mt-1">PATCHED</p>
                <p className="text-2xl font-bold">
                  {Object.keys(prStates).length}
                </p>
              </div>
            </div>

            {/* Table */}
            <div className="surface-default rounded-3xl overflow-hidden border-soft">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#2F3134]">
                    <th className="p-6 text-left text-[#C4C7C5] font-semibold">
                      Severity
                    </th>
                    <th className="p-6 text-left text-[#C4C7C5] font-semibold">
                      File
                    </th>
                    <th className="p-6 text-left text-[#C4C7C5] font-semibold">
                      Rule
                    </th>
                    <th className="p-6 text-left text-[#C4C7C5] font-semibold">
                      Description
                    </th>
                    <th className="p-6 text-center text-[#C4C7C5] font-semibold">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {findings.map((finding, i) => (
                    <tr
                      key={i}
                      className="border-b border-[#2F3134] hover:bg-[#26282B]/30 transition-colors"
                      style={{ animation: `rowFade 0.3s ease-out ${i * 0.03}s` }}
                    >
                      <td className="p-6">
                        <span
                          className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${
                            finding.severity === "ERROR" ||
                            finding.severity === "HIGH"
                              ? "bg-[#EA6E74]/20 text-[#EA6E74]"
                              : finding.severity === "WARNING"
                              ? "bg-[#F4B183]/20 text-[#F4B183]"
                              : "bg-[#FFE082]/20 text-[#FFE082]"
                          }`}
                        >
                          {finding.severity}
                        </span>
                      </td>
                      <td className="p-6 font-mono text-sm text-[#C4C7C5]">
                        {finding.file_path.split("/").slice(-2).join("/")}
                      </td>
                      <td className="p-6 font-mono text-sm text-[#4A90E2]">
                        {finding.rule_id}
                      </td>
                      <td className="p-6 text-sm text-[#9AA0A6] truncate">
                        {finding.description}
                      </td>
                      <td className="p-6 text-center space-x-2">
                        <button
                          onClick={() =>
                            setSelectedFindingIdx(i === selectedFindingIdx ? null : i)
                          }
                          className="px-3 py-1 rounded-full text-xs bg-[#2F3134] hover:bg-[#A87FFB]/20"
                        >
                          View & Patch
                        </button>
                        {prStates[i] && (
                          <span className="text-xs text-[#72CFA1]">
                            ✓ PR Created
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <style>{`
              @keyframes rowFade {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
              }
              .pulsing { animation: pulse 2s infinite; }
              @keyframes pulse {
                50% { opacity: 0.5; }
              }
            `}</style>
          </>
        ) : null}

        {/* Modal */}
        {selectedFindingIdx !== null && findings[selectedFindingIdx] && (
          <DiffModal
            finding={{
              ...findings[selectedFindingIdx],
              _index: selectedFindingIdx,
            }}
            isOpen={true}
            onClose={() => setSelectedFindingIdx(null)}
            apiBase={apiBase}
          />
        )}
      </div>
    </div>
  );
}
