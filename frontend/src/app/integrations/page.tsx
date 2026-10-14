"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  Sparkles, 
  CheckCircle2, 
  AlertCircle, 
  RefreshCw,
  Search,
  Users,
  Mail, 
  ArrowLeft, 
  ShieldCheck,
  Calendar,
} from "lucide-react";
import { apiFetch } from "@/lib/api";

type IntegrationInfo = {
  id: string;
  provider: string;
  status: string;
  model?: string;
};

type BackendSettingsStatus = {
  integrations: IntegrationInfo[];
};

type ProviderDiagnostic = {
  status: string;
  connection_tested: boolean;
};

export default function IntegrationsPage() {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    summary: string;
    details?: Record<string, ProviderDiagnostic>;
  } | null>(null);
  const [backendStatus, setBackendStatus] = useState<BackendSettingsStatus | null>(null);

  const integrationFor = (id: string) => {
    const aliases: Record<string, string[]> = {
      llm: ["llm"],
      discovery: ["discovery"],
      enrichment: ["enrichment"],
      email: ["email"],
    };
    const ids = aliases[id] ?? [id];
    return backendStatus?.integrations.find((item) => ids.includes(item.id));
  };

  const statusLabel = (status?: string) => {
    if (status === "configured") return "Configured — not tested";
    if (status === "mock") return "Mock mode";
    if (status === "not_configured") return "Not configured";
    if (status === "operational") return "Probe succeeded";
    if (status === "error") return "Probe failed";
    return "Unknown";
  };

  const statusClass = (status?: string) =>
    status === "mock"
      ? "bg-accentLight text-accent"
      : status === "configured" || status === "operational"
        ? "bg-amber-500/15 text-amber-500"
        : "bg-red-400/15 text-red-400";

  useEffect(() => {
    let active = true;
    const loadStatus = async () => {
      try {
        const res = await apiFetch("/api/v1/settings/status");
        if (res.ok) {
          const data = (await res.json()) as BackendSettingsStatus;
          if (active) setBackendStatus(data);
        }
      } catch (error: unknown) {
        console.error("Failed to fetch settings status:", error);
      }
    };
    void loadStatus();
    return () => {
      active = false;
    };
  }, []);

  const handleTestIntegrations = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await apiFetch("/api/v1/settings/test-live", { method: "POST" });
      if (res.ok) {
        const data = (await res.json()) as {
          summary: string;
          diagnostics: Record<string, ProviderDiagnostic>;
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
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setTestResult({ summary: "Live diagnostic network error: " + message });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="w-full max-w-[1440px] mx-auto flex flex-col gap-8 pb-14 px-2 sm:px-4">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link href="/" className="p-2.5 rounded-full bg-card border border-borderLine hover:bg-accentLight text-textSecondary hover:text-textPrimary transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-textPrimary">Integrations Management</h1>
            <p className="text-sm text-textSecondary mt-1">
              Provider selection and configuration are shown separately from actual connectivity checks.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={handleTestIntegrations}
            disabled={testing}
            className="flex items-center gap-2 px-5 py-2.5 rounded-full border border-borderLine bg-card hover:bg-accentLight text-xs font-bold text-textPrimary transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${testing ? "animate-spin" : ""}`} /> 
            {testing ? "Checking..." : "Check Provider Status"}
          </button>
          <Link
            href="/settings"
            className="px-5 py-2.5 rounded-full bg-accent text-card text-xs font-bold hover:opacity-90 transition-opacity"
          >
            Settings & Guardrails &rarr;
          </Link>
        </div>
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
                <div key={provider} className="p-3.5 rounded-xl bg-background border border-borderLine">
                  <span className="font-bold text-textPrimary block capitalize">{provider}</span>
                  <span className={`font-semibold block ${statusClass(diagnostic.status)}`}>
                    {statusLabel(diagnostic.status)}
                  </span>
                  <span className="block text-textSecondary mt-1">
                    {diagnostic.connection_tested
                      ? "Connectivity probed."
                      : "Configuration only; not a connection test."}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Grid of Providers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Gemini */}
        <div className="bg-card rounded-[2rem] p-7 shadow-sm border border-borderLine flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-accentLight text-accent flex items-center justify-center">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-textPrimary">{integrationFor("llm")?.provider || "LLM"} Provider</h3>
                  <p className="text-xs text-textSecondary">Language model</p>
                </div>
              </div>
              <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${statusClass(integrationFor("llm")?.status)}`}>
                {statusLabel(integrationFor("llm")?.status)}
              </span>
            </div>
            <p className="text-xs text-textSecondary leading-relaxed mb-4">
              Used for evidence extraction, scoring signals, and draft generation. Configuration is not a connection test.
            </p>
          </div>
          <div className="pt-3 border-t border-borderLine text-xs font-mono text-textSecondary flex items-center justify-between">
            <span>Model: {integrationFor("llm")?.model || "not reported"}</span>
            <span>Connection probe available below</span>
          </div>
        </div>

        {/* Tavily */}
        <div className="bg-card rounded-[2rem] p-7 shadow-sm border border-borderLine flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-accentLight text-accent flex items-center justify-center">
                  <Search className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-textPrimary">{integrationFor("discovery")?.provider || "Discovery"} Search</h3>
                  <p className="text-xs text-textSecondary">Commercial Domain Hunter</p>
                </div>
              </div>
              <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${statusClass(integrationFor("discovery")?.status)}`}>
                {statusLabel(integrationFor("discovery")?.status)}
              </span>
            </div>
            <p className="text-xs text-textSecondary leading-relaxed mb-4">
              Provider selected for company discovery. Mock mode returns no live search results.
            </p>
          </div>
          <div className="pt-3 border-t border-borderLine text-xs font-mono text-textSecondary flex items-center justify-between">
            <span>Selected: {integrationFor("discovery")?.provider || "unknown"}</span>
            <span>Connectivity not assumed</span>
          </div>
        </div>

        {/* Apollo */}
        <div className="bg-card rounded-[2rem] p-7 shadow-sm border border-borderLine flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-accentLight text-accent flex items-center justify-center">
                  <Users className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-textPrimary">{integrationFor("enrichment")?.provider || "Enrichment"} Provider</h3>
                  <p className="text-xs text-textSecondary">Decision-Maker Prospecting</p>
                </div>
              </div>
              <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${statusClass(integrationFor("enrichment")?.status)}`}>
                {statusLabel(integrationFor("enrichment")?.status)}
              </span>
            </div>
            <p className="text-xs text-textSecondary leading-relaxed mb-4">
              Enrichment configuration for company and decision-maker data. Provider errors are recorded in pipeline runs.
            </p>
          </div>
          <div className="pt-3 border-t border-borderLine text-xs font-mono text-textSecondary flex items-center justify-between">
            <span>Selected: {integrationFor("enrichment")?.provider || "unknown"}</span>
            <span>Connectivity not assumed</span>
          </div>
        </div>

        {/* Resend */}
        <div className="bg-card rounded-[2rem] p-7 shadow-sm border border-borderLine flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-accentLight text-accent flex items-center justify-center">
                  <Mail className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-textPrimary">{integrationFor("email")?.provider || "Email"} Provider</h3>
                  <p className="text-xs text-textSecondary">Outbound SMTP / REST Relay</p>
                </div>

                {/* Verification */}
                <div className="bg-card rounded-[2rem] p-7 shadow-sm border border-borderLine flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-accentLight text-accent flex items-center justify-center">
                          <ShieldCheck className="w-5 h-5" />
                        </div>
                        <div>
                          <h3 className="text-base font-bold text-textPrimary">{integrationFor("verification")?.provider || "Verification"} Provider</h3>
                          <p className="text-xs text-textSecondary">Email validation</p>
                        </div>
                      </div>
                      <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${statusClass(integrationFor("verification")?.status)}`}>
                        {statusLabel(integrationFor("verification")?.status)}
                      </span>
                    </div>
                    <p className="text-xs text-textSecondary leading-relaxed mb-4">
                      Configurable Hunter, DNS, or explicit mock verification for pipeline contacts.
                    </p>
                  </div>
                  <div className="pt-3 border-t border-borderLine text-xs font-mono text-textSecondary flex items-center justify-between">
                    <span>Selected: {integrationFor("verification")?.provider || "unknown"}</span>
                    <span>Connectivity not assumed</span>
                  </div>
                </div>

                {/* Calendar */}
                <div className="bg-card rounded-[2rem] p-7 shadow-sm border border-borderLine flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-accentLight text-accent flex items-center justify-center">
                          <Calendar className="w-5 h-5" />
                        </div>
                        <div>
                          <h3 className="text-base font-bold text-textPrimary">{integrationFor("calendar")?.provider || "Calendar"} Provider</h3>
                          <p className="text-xs text-textSecondary">Availability and booking</p>
                        </div>
                      </div>
                      <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${statusClass(integrationFor("calendar")?.status)}`}>
                        {statusLabel(integrationFor("calendar")?.status)}
                      </span>
                    </div>
                    <p className="text-xs text-textSecondary leading-relaxed mb-4">
                      Google Calendar credentials are stored per organization; mock mode never creates real events.
                    </p>
                  </div>
                  <div className="pt-3 border-t border-borderLine text-xs font-mono text-textSecondary flex items-center justify-between">
                    <span>Selected: {integrationFor("calendar")?.provider || "unknown"}</span>
                    <span>Connectivity not assumed</span>
                  </div>
                </div>
              </div>
              <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${statusClass(integrationFor("email")?.status)}`}>
                {statusLabel(integrationFor("email")?.status)}
              </span>
            </div>
            <p className="text-xs text-textSecondary leading-relaxed mb-4">
              Used only for approved messages. Mock mode does not deliver emails.
            </p>
          </div>
          <div className="pt-3 border-t border-borderLine text-xs font-mono text-textSecondary flex items-center justify-between">
            <span>Selected: {integrationFor("email")?.provider || "unknown"}</span>
            <span>Delivery requires configured provider</span>
          </div>
        </div>
      </div>
    </div>
  );
}
