"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  ShieldCheck, 
  CheckCircle2, 
  AlertCircle, 
  Save, 
  RefreshCw,
  ArrowLeft
} from "lucide-react";

import { apiFetch } from "@/lib/api";
import { IntegrationConfigurationPanel } from "./IntegrationConfigurationPanel";

type SettingsStatus = {
  guardrails?: {
    require_human_approval?: boolean;
    min_lead_score?: number;
    daily_send_limit?: number;
  };
};

type IntegrationDiagnostic = {
  status: string;
  latency_ms?: number;
  message?: string;
  connection_tested?: boolean;
  provider?: string;
};

export default function SettingsPage() {
  const [saved, setSaved] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    summary: string;
    details?: Record<string, IntegrationDiagnostic>;
  } | null>(null);

  // Settings State
  const [requireApproval, setRequireApproval] = useState(true);
  const [minScore, setMinScore] = useState(70);
  const [dailyLimit, setDailyLimit] = useState(50);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await apiFetch("/api/v1/settings/status");
        if (res.ok) {
          const d = await res.json() as SettingsStatus;
          if (d.guardrails) {
            if (typeof d.guardrails.require_human_approval === "boolean") {
              setRequireApproval(d.guardrails.require_human_approval);
            }
            if (typeof d.guardrails.min_lead_score === "number") {
              setMinScore(d.guardrails.min_lead_score);
            }
            if (typeof d.guardrails.daily_send_limit === "number") {
              setDailyLimit(d.guardrails.daily_send_limit);
            }
          }
        }
      } catch (e) {
        console.error("Failed to fetch settings status:", e);
      }
    };
    fetchStatus();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await apiFetch("/api/v1/settings/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          require_human_approval: requireApproval,
          min_lead_score: minScore,
          daily_send_limit: dailyLimit
        })
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Could not save settings");
      }
      const savedSettings = await response.json() as SettingsStatus;
      setRequireApproval(savedSettings.guardrails?.require_human_approval ?? requireApproval);
      setMinScore(savedSettings.guardrails?.min_lead_score ?? minScore);
      setDailyLimit(savedSettings.guardrails?.daily_send_limit ?? dailyLimit);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      console.error("Error saving settings:", e);
      setSaved(false);
      alert(e instanceof Error ? e.message : "Could not save settings");
    }
  };

  const handleTestIntegrations = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await apiFetch("/api/v1/settings/test-live", { method: "POST" });
      if (res.ok) {
        const data = await res.json() as {
          summary: string;
          diagnostics: Record<string, IntegrationDiagnostic>;
        };
        setTestResult({
          summary: data.summary,
          details: data.diagnostics,
        });
      } else {
        setTestResult({
          summary: "Diagnostic failed: Server returned error status",
        });
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : String(e);
      setTestResult({ summary: "Live diagnostic network error: " + message });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto flex flex-col gap-8 pb-12">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="p-2.5 rounded-full bg-card border border-borderLine hover:bg-accentLight text-textSecondary hover:text-textPrimary transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-textPrimary">System Settings & Provider Configuration</h1>
            <p className="text-sm text-textSecondary mt-1">
              Set organization-specific providers and credentials securely from your workspace.
            </p>
          </div>
        </div>

        <button 
          onClick={handleTestIntegrations}
          disabled={testing}
          className="flex items-center gap-2 px-5 py-2.5 rounded-full border border-borderLine bg-card hover:bg-accentLight text-xs font-bold text-textPrimary transition-colors cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${testing ? "animate-spin" : ""}`} /> 
          {testing ? "Checking..." : "Check Provider Status"}
        </button>
      </div>

      {testResult && (
        <div className={`p-5 rounded-2xl bg-card border shadow-sm space-y-3 ${
          testResult.summary.includes("operational") ? "border-success/30" : "border-borderLine"
        }`}>
          <div className="flex items-center gap-3">
            {testResult.summary.includes("operational") ? (
              <CheckCircle2 className="w-5 h-5 text-success shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-accent shrink-0" />
            )}
            <span className="text-sm font-bold text-textPrimary">{testResult.summary}</span>
          </div>
          {testResult.details && (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 pt-2 border-t border-borderLine text-xs">
              {Object.entries(testResult.details).map(([provider, diagnostic]) => (
                <div key={provider} className="p-3 rounded-xl bg-background border border-borderLine">
                  <span className="font-bold text-textPrimary block capitalize">
                    {provider.replaceAll("_", " ")}
                  </span>
                  <span className="font-semibold block text-amber-500">
                    {diagnostic.status} · {diagnostic.connection_tested
                      ? "connectivity probed"
                      : "configuration only"}
                  </span>
                  <span className="block text-textSecondary mt-1">{diagnostic.message}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {saved && (
        <div className="p-4 rounded-2xl bg-success/10 border border-success/20 flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-success" />
          <span className="text-sm font-bold text-success">Settings saved successfully!</span>
        </div>
      )}

      {/* Grid: 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Col (2 cols): integrations and credentials */}
        <div className="lg:col-span-2 space-y-6">
          <IntegrationConfigurationPanel />
        </div>

        {/* Right Col: Autonomous Guardrails & Policy */}
        <div className="space-y-6">
          <div className="bg-card rounded-[2rem] p-8 shadow-sm border border-borderLine">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-9 h-9 rounded-full bg-accentLight text-accent flex items-center justify-center">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-textPrimary">Safety Guardrails</h3>
                <p className="text-xs text-textSecondary">Control AI autonomy & sending limits.</p>
              </div>
            </div>

            <form onSubmit={handleSave} className="space-y-6">
              {/* Human Approval Toggle */}
              <div className="flex items-center justify-between p-4 rounded-xl bg-background border border-borderLine">
                <div>
                  <label className="text-xs font-bold text-textPrimary block">Human Review Required</label>
                  <span className="text-[11px] text-textSecondary">Never send emails without 1-click human review.</span>
                </div>
                <input 
                  type="checkbox"
                  checked={requireApproval}
                  onChange={(e) => setRequireApproval(e.target.checked)}
                  className="w-5 h-5 accent-accent cursor-pointer"
                />
              </div>

              {/* Min Qualification Score */}
              <div>
                <label className="text-xs font-bold text-textPrimary block mb-1">
                  Minimum Qualification Score: <span className="text-accent">{minScore}/100</span>
                </label>
                <input 
                  type="range"
                  min={30}
                  max={95}
                  value={minScore}
                  onChange={(e) => setMinScore(Number(e.target.value))}
                  className="w-full accent-accent cursor-pointer"
                />
                <span className="text-[11px] text-textSecondary mt-1 block">
                  Leads scoring below {minScore} will not have messages drafted.
                </span>
              </div>

              {/* Daily Send Limit */}
              <div>
                <label className="text-xs font-bold text-textPrimary block mb-1">Daily Send Rate Limit</label>
                <input 
                  type="number"
                  value={dailyLimit}
                  onChange={(e) => setDailyLimit(Number(e.target.value))}
                  className="w-full px-4 py-2.5 rounded-xl border border-borderLine bg-background text-textPrimary text-xs font-semibold"
                />
                <span className="text-[11px] text-textSecondary mt-1 block">
                  Protects email deliverability and domain reputation.
                </span>
              </div>

              <button 
                type="submit"
                className="w-full py-3 rounded-full bg-accent text-card text-xs font-bold flex items-center justify-center gap-2 shadow-md hover:opacity-90 cursor-pointer"
              >
                <Save className="w-4 h-4" /> Save System Settings
              </button>
            </form>
          </div>

          {/* Database Info Card */}
          <div className="bg-card rounded-[2rem] p-6 shadow-sm border border-borderLine space-y-3">
            <h4 className="text-sm font-bold text-textPrimary">Local Storage & Database</h4>
            <div className="text-xs text-textSecondary space-y-1">
              <div>Mode: <span className="font-bold text-textPrimary">Async SQLite (xobalt.db)</span></div>
              <div>Status: <span className="font-bold text-textPrimary">Health not checked here</span></div>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
