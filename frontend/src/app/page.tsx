"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { 
  Users, 
  Briefcase,
  Building2, 
  Mail, 
  Calendar, 
  Sparkles, 
  Loader2, 
  ArrowRight, 
  CheckCircle2,
  ExternalLink,
  ShieldCheck,
  Search,
  Target,
  Clock,
  Layers,
  Settings,
  RefreshCw,
  Check,
  AlertCircle,
  FileText,
  UserCheck,
  HelpCircle
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface DiscoveryLead {
  id: string;
  company_name: string;
  company_domain: string;
  website_url: string;
  industry: string;
  decision_maker_name: string;
  decision_maker_title: string;
  email: string | null;
  email_status: "verified" | "deliverable" | "domain_contact";
  score: number | null;
  qualification_status: "Qualified" | "Review" | "New";
  message_status: string;
  created_at: string | null;
}

interface IntegrationInfo {
  name: string;
  status: string;
  provider: string;
}

interface DashboardSummary {
  total_leads: number;
  qualified_leads: number;
  total_companies: number;
  messages_sent: number;
  messages_drafted: number;
  meetings_booked: number;
  active_model?: string;
  llm_provider?: string;
  recent_discoveries: DiscoveryLead[];
  integrations?: Record<string, IntegrationInfo>;
}

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Pipeline Execution State
  const [pipelineState, setPipelineState] = useState<"ready" | "running" | "completed" | "error">("ready");
  const [pipelineStep, setPipelineStep] = useState(1);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const [runResult, setRunResult] = useState<{
    count?: number;
    qualifiedCount?: number;
    draftCount?: number;
    steps?: Record<string, { status: string; reason?: string }>;
    message: string;
  } | null>(null);

  // Form State for Autonomous Discovery
  const [industry, setIndustry] = useState("Real Estate");
  const [country, setCountry] = useState("United States");
  const [maxCompanies, setMaxCompanies] = useState(3);
  const [offer, setOffer] = useState("Strategic partnership & business development collaboration");

  // Live Stats State
  const [stats, setStats] = useState<DashboardSummary>({
    total_leads: 0,
    qualified_leads: 0,
    total_companies: 0,
    messages_drafted: 0,
    messages_sent: 0,
    meetings_booked: 0,
    active_model: "gemini-2.5-flash",
    llm_provider: "Gemini",
    recent_discoveries: [],
    integrations: {
      llm: { name: "LLM", status: "unknown", provider: "unknown" },
      search: { name: "Discovery", status: "unknown", provider: "unknown" },
      enrichment: { name: "Enrichment", status: "unknown", provider: "unknown" },
      verification: { name: "Verification", status: "unknown", provider: "unknown" },
      email: { name: "Email", status: "unknown", provider: "unknown" },
    }
  });

  const integrationStatusText = (status?: string) => {
    if (status === "configured") return "Configured — not tested";
    if (status === "mock") return "Mock mode";
    if (status === "not_configured" || status === "unconfigured") return "Not configured";
    return "Unknown";
  };

  const fetchSummary = async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const res = await apiFetch("/api/v1/dashboard/summary");
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      } else {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
    } catch (e: any) {
      console.error("Dashboard fetch error:", e);
      setFetchError(e.message || "Could not connect to backend server");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  // Timer handling for running pipeline
  useEffect(() => {
    if (pipelineState === "running") {
      setElapsedSeconds(0);
      timerRef.current = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [pipelineState]);

  const handleRunPipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pipelineState === "running") return;

    setPipelineState("running");
    setRunResult(null);
    setPipelineStep(1);

    // Realistic visual stage progression matching backend LangGraph execution
    const t1 = setTimeout(() => setPipelineStep(2), 2500);
    const t2 = setTimeout(() => setPipelineStep(3), 5500);
    const t3 = setTimeout(() => setPipelineStep(4), 9000);

    try {
      const res = await apiFetch("/api/v1/leads/find-and-generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          industry,
          country,
          max_companies: Number(maxCompanies),
          offer,
          decision_maker_roles: ["CEO", "Founder", "Director", "Owner", "President"]
        })
      });

      if (!res.ok) {
        const failure = await res.json().catch(() => null);
        const details = failure?.detail;
        setRunResult({
          steps: details?.steps,
          message: details?.run_id
            ? `Pipeline run ${details.run_id} failed (HTTP ${res.status}).`
            : `Pipeline failed with HTTP ${res.status}.`,
        });
        setPipelineState("error");
        return;
      }

      const resData = await res.json();
      await fetchSummary();

      const newLeads = Array.isArray(resData.leads) ? resData.leads : [];
      const discoveredCount = Number(resData.lead_count ?? newLeads.length);
      const draftCount = Number(resData.draft_count ?? 0);
      const qualified = newLeads.filter((l: any) => (l.score || 0) >= 70).length;

      setRunResult({
        count: discoveredCount,
        qualifiedCount: qualified,
        draftCount,
        steps: resData.steps,
        message: `Pipeline run ${resData.run_id} finished with status ${resData.status}: ${discoveredCount} leads persisted, ${draftCount} drafts saved.`
      });
      setPipelineState(resData.status === "failed" ? "error" : "completed");
    } catch (err: any) {
      setRunResult({
        message: `Execution failed: ${err.message}. Ensure backend is active at http://127.0.0.1:8000.`
      });
      setPipelineState("error");
    } finally {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    }
  };

  const statCards = [
    { 
      label: "Total Leads", 
      value: stats.total_leads, 
      sub: "Active in CRM repository", 
      icon: Users,
      href: "/leads",
      badge: "Database",
      accent: "text-textPrimary"
    },
    { 
      label: "Qualified Leads", 
      value: stats.qualified_leads, 
      sub: "ICP score ≥ 70 threshold", 
      icon: Sparkles,
      href: "/leads",
      badge: "Qualified",
      accent: "text-success"
    },
    { 
      label: "Emails Sent", 
      value: stats.messages_sent, 
      sub: `${stats.messages_drafted} drafts awaiting review`, 
      icon: Mail,
      href: "/inbox",
      badge: "Outreach",
      accent: "text-textPrimary"
    },
    { 
      label: "Meetings Booked", 
      value: stats.meetings_booked, 
      sub: "Confirmed calendar appointments", 
      icon: Calendar,
      href: "/appointments",
      badge: "Conversions",
      accent: "text-textPrimary"
    },
  ];

  return (
    <div className="w-full max-w-[1440px] mx-auto flex flex-col gap-8 pb-14 px-2 sm:px-4">
      
      {/* Top Header & Overview Bar */}
      <div className="flex flex-col gap-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accentLight text-textPrimary text-xs font-bold mb-2.5">
              <span className="w-2 h-2 rounded-full bg-success animate-pulse"></span>
              Autonomous Revenue Engine
            </div>
            <h1 className="text-3xl lg:text-4xl font-extrabold tracking-tight text-textPrimary">Command Dashboard</h1>
            <p className="text-sm lg:text-base text-textSecondary mt-1.5 max-w-2xl">
              Live intelligence overview, multi-stage lead acquisition, and real-time revenue pipeline telemetry.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button 
              onClick={fetchSummary}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2.5 rounded-full border border-borderLine bg-card hover:bg-accentLight text-xs font-bold text-textPrimary transition-colors shadow-sm cursor-pointer"
              title="Refresh live metrics from backend"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Refresh Metrics</span>
            </button>
            <Link 
              href="/leads"
              className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-accent text-card text-xs font-bold hover:opacity-90 transition-opacity shadow-sm"
            >
              <span>Review CRM Leads</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        {/* 4 Interactive Business-Oriented KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
          {statCards.map((stat, idx) => (
            <Link 
              key={idx} 
              href={stat.href}
              className="group bg-card rounded-[2rem] p-6 lg:p-7 flex flex-col justify-between shadow-sm border border-borderLine hover:shadow-md hover:border-textPrimary/25 hover:-translate-y-0.5 transition-all duration-200 cursor-pointer"
            >
              <div className="flex items-start justify-between mb-5">
                <div className="w-12 h-12 bg-accentLight rounded-full flex items-center justify-center group-hover:bg-accent group-hover:text-card transition-colors">
                  <stat.icon className="w-5 h-5 text-accent group-hover:text-card transition-colors" />
                </div>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-background border border-borderLine text-textSecondary">
                  {stat.badge}
                </span>
              </div>
              <div>
                <h2 className="text-3xl lg:text-4xl font-black text-textPrimary tracking-tight">{stat.value}</h2>
                <p className="text-xs font-bold text-textPrimary mt-1.5">{stat.label}</p>
                <p className="text-[11px] text-textSecondary mt-0.5">{stat.sub}</p>
              </div>
              <div className="mt-5 pt-3.5 border-t border-borderLine flex items-center justify-between text-[11px] font-bold text-textSecondary group-hover:text-textPrimary transition-colors">
                <span>View details</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Live Pipeline Controller Card */}
      <div className="bg-card rounded-[2rem] p-7 lg:p-9 shadow-sm border border-borderLine">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 pb-6 border-b border-borderLine">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-accent text-card text-[11px] font-bold">
                <Sparkles className="w-3.5 h-3.5" /> LIVE PIPELINE CONTROLLER
              </span>
              <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-accentLight text-textPrimary border border-borderLine">
                Model: {stats.active_model || "gemini-2.5-flash"}
              </span>
              {pipelineState === "running" && (
                <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-accent text-card animate-pulse flex items-center gap-1">
                  <Clock className="w-3 h-3" /> {elapsedSeconds}s elapsed
                </span>
              )}
            </div>
            <h2 className="text-2xl font-bold text-textPrimary">Autonomous Discovery & Outreach Synthesizer</h2>
            <p className="text-sm text-textSecondary mt-1">
              End-to-end execution: Company discovery, decision-maker extraction, deliverability validation, and draft outreach preparation.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link 
              href="/settings"
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-full border border-borderLine hover:bg-accentLight text-xs font-bold text-textSecondary transition-colors"
            >
              <Settings className="w-3.5 h-3.5" /> Configure Integrations
            </Link>
          </div>
        </div>

        {/* 4 Stage Workflow Pipeline Visualizer with Live State */}
        <div className="mb-8">
          <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-textSecondary mb-3">
            <span>Workflow Stages</span>
            <span className="text-[11px] text-textSecondary font-semibold">
              Drafts prepared for human review &bull; Never sends without approval
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 lg:gap-4">
            <div className={`p-4 rounded-2xl border transition-all ${
              pipelineState === "running" && pipelineStep === 1 
                ? "bg-accent text-card border-accent shadow-sm scale-[1.02]" 
                : "bg-background border-borderLine"
            }`}>
              <div className="flex items-center gap-2 font-bold text-xs mb-1">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                  pipelineState === "running" && pipelineStep === 1 ? "bg-card text-accent font-black" : "bg-accentLight text-textPrimary"
                }`}>1</span>
                <span>Discover Companies</span>
              </div>
              <p className={`text-[11px] leading-relaxed ${pipelineState === "running" && pipelineStep === 1 ? "text-card/85" : "text-textSecondary"}`}>
                Tavily Live commercial web search filtered for genuine commercial domains.
              </p>
            </div>

            <div className={`p-4 rounded-2xl border transition-all ${
              pipelineState === "running" && pipelineStep === 2 
                ? "bg-accent text-card border-accent shadow-sm scale-[1.02]" 
                : "bg-background border-borderLine"
            }`}>
              <div className="flex items-center gap-2 font-bold text-xs mb-1">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                  pipelineState === "running" && pipelineStep === 2 ? "bg-card text-accent font-black" : "bg-accentLight text-textPrimary"
                }`}>2</span>
                <span>Find Decision-Makers</span>
              </div>
              <p className={`text-[11px] leading-relaxed ${pipelineState === "running" && pipelineStep === 2 ? "text-card/85" : "text-textSecondary"}`}>
                Apollo.io enrichment targeting C-level executives, Founders, and Owners.
              </p>
            </div>

            <div className={`p-4 rounded-2xl border transition-all ${
              pipelineState === "running" && pipelineStep === 3 
                ? "bg-accent text-card border-accent shadow-sm scale-[1.02]" 
                : "bg-background border-borderLine"
            }`}>
              <div className="flex items-center gap-2 font-bold text-xs mb-1">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                  pipelineState === "running" && pipelineStep === 3 ? "bg-card text-accent font-black" : "bg-accentLight text-textPrimary"
                }`}>3</span>
                <span>Enrich & Verify</span>
              </div>
              <p className={`text-[11px] leading-relaxed ${pipelineState === "running" && pipelineStep === 3 ? "text-card/85" : "text-textSecondary"}`}>
                Website intelligence extraction and real-time DNS MX handshake deliverability.
              </p>
            </div>

            <div className={`p-4 rounded-2xl border transition-all ${
              pipelineState === "running" && pipelineStep === 4 
                ? "bg-accent text-card border-accent shadow-sm scale-[1.02]" 
                : "bg-background border-borderLine"
            }`}>
              <div className="flex items-center gap-2 font-bold text-xs mb-1">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                  pipelineState === "running" && pipelineStep === 4 ? "bg-card text-accent font-black" : "bg-accentLight text-textPrimary"
                }`}>4</span>
                <span>Score & Draft Outreach</span>
              </div>
              <p className={`text-[11px] leading-relaxed ${pipelineState === "running" && pipelineStep === 4 ? "text-card/85" : "text-textSecondary"}`}>
                ICP scoring with tailored email generation ready for human sign-off in CRM.
              </p>
            </div>
          </div>
        </div>

        {/* Input Form with Configurable Value Proposition */}
        <form onSubmit={handleRunPipeline} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-textSecondary mb-2">
                Target Industry
              </label>
              <input 
                type="text" 
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                disabled={pipelineState === "running"}
                className="w-full px-4 py-3 rounded-xl border border-borderLine bg-background text-textPrimary text-sm font-medium focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-60"
                placeholder="e.g. Real Estate, Commercial Architecture, Fintech"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-textSecondary mb-2">
                Country / Region
              </label>
              <input 
                type="text" 
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                disabled={pipelineState === "running"}
                className="w-full px-4 py-3 rounded-xl border border-borderLine bg-background text-textPrimary text-sm font-medium focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-60"
                placeholder="e.g. United States, United Kingdom"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-textSecondary mb-2">
                Discovery Volume (Companies)
              </label>
              <input 
                type="number" 
                value={maxCompanies}
                onChange={(e) => setMaxCompanies(Math.max(1, Math.min(10, Number(e.target.value))))}
                min={1}
                max={10}
                disabled={pipelineState === "running"}
                className="w-full px-4 py-3 rounded-xl border border-borderLine bg-background text-textPrimary text-sm font-medium focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-60"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-textSecondary mb-2">
              Your Offer / Outreach Angle <span className="text-[10px] text-textSecondary font-normal lowercase">(Shapes personalized messaging instead of generic templates)</span>
            </label>
            <input 
              type="text" 
              value={offer}
              onChange={(e) => setOffer(e.target.value)}
              disabled={pipelineState === "running"}
              className="w-full px-4 py-3 rounded-xl border border-borderLine bg-background text-textPrimary text-sm font-medium focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-60"
              placeholder="e.g. Exploring strategic client acquisition synergies and property listing partnerships"
              required
            />
          </div>

          <div className="pt-2">
            <button 
              type="submit" 
              disabled={pipelineState === "running"}
              className="w-full py-4 px-6 rounded-full bg-accent text-card font-bold text-sm shadow-md hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-2 transition-all cursor-pointer"
            >
              {pipelineState === "running" ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>
                    Executing Pipeline ({
                      pipelineStep === 1 ? "Stage 1: Searching Commercial Companies via Tavily..." :
                      pipelineStep === 2 ? "Stage 2: Enriching and verifying contacts..." :
                      pipelineStep === 3 ? "Stage 3: Persisting leads and analyzing company evidence..." :
                      "Stage 4: Scoring leads and generating draft messages..."
                    }) &bull; {elapsedSeconds}s
                  </span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Execute Autonomous Pipeline</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Completion or Error State Banner */}
        {pipelineState === "completed" && runResult && (
          <div className="mt-6 p-5 rounded-2xl bg-success/10 border border-success/30 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-6 h-6 text-success shrink-0" />
              <div>
                <p className="text-sm font-bold text-textPrimary">{runResult.message}</p>
                <p className="text-xs text-textSecondary mt-0.5">
                  {runResult.count === 0 || runResult.draftCount === 0
                    ? "The counts above are from persisted records; no missing results are inferred as successes."
                    : "Drafts are saved for human review. No email is sent automatically."}
                </p>
                {runResult.steps && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {Object.entries(runResult.steps).map(([step, result]) => (
                      <span key={step} className="text-[10px] px-2 py-1 rounded bg-background border border-borderLine text-textSecondary">
                        {step.replaceAll("_", " ")}: {result.status}
                        {result.reason ? ` (${result.reason})` : ""}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Link 
                href="/leads" 
                className="flex items-center gap-2 px-4 py-2 rounded-full bg-accent text-card text-xs font-bold hover:opacity-90 transition-opacity"
              >
                <span>Review Generated Leads</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        )}

        {pipelineState === "error" && runResult && (
          <div className="mt-6 p-5 rounded-2xl bg-red-500/10 border border-red-500/30 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-6 h-6 text-red-500 shrink-0" />
              <div>
                <p className="text-sm font-bold text-textPrimary">{runResult.message}</p>
                <p className="text-xs text-textSecondary mt-0.5">
                  Check the run's stage details and provider configuration before retrying.
                </p>
                {runResult.steps && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {Object.entries(runResult.steps).map(([step, result]) => (
                      <span key={step} className="text-[10px] px-2 py-1 rounded bg-background border border-borderLine text-textSecondary">
                        {step.replaceAll("_", " ")}: {result.status}
                        {result.reason ? ` (${result.reason})` : ""}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <button 
              onClick={() => setPipelineState("ready")}
              className="shrink-0 px-4 py-2 rounded-full border border-borderLine bg-card hover:bg-accentLight text-xs font-bold text-textPrimary transition-colors"
            >
              Dismiss & Retry
            </button>
          </div>
        )}
      </div>

      {/* Bottom Section: Recent Discoveries Table & Live Integrations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Recent Discoveries Detailed Table (2 Columns) */}
        <div className="lg:col-span-2 bg-card rounded-[2rem] p-7 lg:p-8 shadow-sm border border-borderLine flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-xl font-bold text-textPrimary">Recent Live Discoveries</h3>
              <p className="text-xs text-textSecondary mt-0.5">
                Companies and decision-maker leads captured by autonomous execution.
              </p>
            </div>
            <Link 
              href="/leads" 
              className="text-xs font-bold text-textSecondary hover:text-textPrimary flex items-center gap-1 transition-colors"
            >
              <span>View All CRM Records ({stats.total_leads})</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {fetchError ? (
            <div className="text-center py-12 flex-1 flex flex-col items-center justify-center bg-red-500/5 rounded-2xl border border-dashed border-red-500/20 p-6">
              <AlertCircle className="w-8 h-8 text-red-400 mb-2" />
              <p className="text-sm font-bold text-textPrimary">Failed to Load Recent Discoveries</p>
              <p className="text-xs text-textSecondary max-w-sm mt-1 mb-4">
                {fetchError}. Ensure FastAPI backend is active on port 8000.
              </p>
              <button 
                onClick={fetchSummary}
                className="px-4 py-2 rounded-full bg-accent text-card text-xs font-bold hover:opacity-90 transition-opacity"
              >
                Retry Connection
              </button>
            </div>
          ) : stats.recent_discoveries && stats.recent_discoveries.length > 0 ? (
            <div className="overflow-x-auto -mx-7 lg:-mx-8 px-7 lg:px-8">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-borderLine text-textSecondary font-bold uppercase tracking-wider text-[10px]">
                    <th className="pb-3.5 font-semibold">Company</th>
                    <th className="pb-3.5 font-semibold">Decision-Maker</th>
                    <th className="pb-3.5 font-semibold">Lead Score</th>
                    <th className="pb-3.5 font-semibold">Contact Email</th>
                    <th className="pb-3.5 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-borderLine">
                  {stats.recent_discoveries.map((lead) => {
                    const score = lead.score ?? 0;
                    const isQualified = score >= 70;
                    const isReview = score >= 50 && score < 70;

                    return (
                      <tr key={lead.id} className="hover:bg-accentLight/50 transition-colors">
                        {/* Company */}
                        <td className="py-3.5 pr-4">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-full bg-accentLight border border-borderLine flex items-center justify-center font-bold text-xs text-textPrimary shrink-0">
                              {lead.company_name[0]}
                            </div>
                            <div className="min-w-0">
                              <span className="font-bold text-textPrimary block truncate">
                                {lead.company_name}
                              </span>
                              {lead.website_url ? (
                                <a 
                                  href={lead.website_url.startsWith("http") ? lead.website_url : `https://${lead.website_url}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-[10px] text-textSecondary hover:underline flex items-center gap-1 truncate"
                                >
                                  {lead.company_domain || "website"} <ExternalLink className="w-2.5 h-2.5 inline" />
                                </a>
                              ) : (
                                <span className="text-[10px] text-textSecondary">
                                  {lead.industry}
                                </span>
                              )}
                            </div>
                          </div>
                        </td>

                        {/* Decision-Maker */}
                        <td className="py-3.5 pr-4">
                          <span className="font-bold text-textPrimary block">
                            {lead.decision_maker_name}
                          </span>
                          <span className="text-[10px] text-textSecondary block truncate">
                            {lead.decision_maker_title}
                          </span>
                        </td>

                        {/* Lead Score */}
                        <td className="py-3.5 pr-4">
                          <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold ${
                            isQualified 
                              ? "bg-success/10 text-success border border-success/20" 
                              : isReview 
                              ? "bg-accentLight text-textPrimary border border-borderLine" 
                              : "bg-background text-textSecondary border border-borderLine"
                          }`}>
                            <Sparkles className="w-3 h-3" />
                            {score}/100 &bull; {lead.qualification_status}
                          </span>
                        </td>

                        {/* Contact Email Status */}
                        <td className="py-3.5 pr-4">
                          <div className="flex items-center gap-1.5">
                            {lead.email_status === "verified" ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-success/10 text-success text-[10px] font-bold">
                                <Check className="w-3 h-3" /> Verified
                              </span>
                            ) : lead.email ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-accentLight text-textPrimary text-[10px] font-bold border border-borderLine">
                                Deliverable
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-background text-textSecondary text-[10px] font-medium border border-borderLine">
                                Domain Inbox
                              </span>
                            )}
                          </div>
                          {lead.email && (
                            <span className="text-[10px] text-textSecondary block truncate mt-0.5 font-mono">
                              {lead.email}
                            </span>
                          )}
                        </td>

                        {/* Action Link */}
                        <td className="py-3.5 text-right">
                          <Link 
                            href="/leads"
                            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-accentLight hover:bg-accent hover:text-card text-textPrimary text-[11px] font-bold transition-all"
                          >
                            Review Lead
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-14 flex-1 flex flex-col items-center justify-center bg-background rounded-2xl border border-dashed border-borderLine p-6">
              <div className="w-12 h-12 rounded-full bg-accentLight flex items-center justify-center mb-3">
                <Building2 className="w-6 h-6 text-textSecondary" />
              </div>
              <p className="text-sm font-bold text-textPrimary">No Discoveries Recorded Yet</p>
              <p className="text-xs text-textSecondary max-w-sm mt-1 mb-4 leading-relaxed">
                Companies represent target organizations, while Leads represent individual decision-makers. Enter your criteria above and run the pipeline to populate verified records here.
              </p>
              <button
                onClick={() => {
                  window.scrollTo({ top: 350, behavior: "smooth" });
                }}
                className="px-4 py-2 rounded-full border border-borderLine bg-card hover:bg-accentLight text-xs font-bold text-textPrimary transition-colors"
              >
                Configure Pipeline Criteria &uarr;
              </button>
            </div>
          )}
        </div>

        {/* Live Setup & Integrations Telemetry Card (1 Column) */}
        <div className="bg-card rounded-[2rem] p-7 lg:p-8 shadow-sm border border-borderLine flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xl font-bold text-textPrimary">Integration Telemetry</h3>
              <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-500">
                Configuration only
              </span>
            </div>
            <p className="text-xs text-textSecondary mb-6">
              Selected providers; connectivity is not implied
            </p>

            <div className="space-y-4 text-xs font-medium">
              <div className="flex items-center justify-between pb-3 border-b border-borderLine">
                <span className="text-textSecondary">LLM Provider</span>
                <span className="text-textPrimary font-semibold text-right">
                  {stats.integrations?.llm?.name || "LLM"} — {integrationStatusText(stats.integrations?.llm?.status)}
                </span>
              </div>
              
              <div className="flex items-center justify-between pb-3 border-b border-borderLine">
                <span className="text-textSecondary">Web Search</span>
                <span className="text-textPrimary font-semibold text-right">
                  {stats.integrations?.search?.name || "Discovery"} — {integrationStatusText(stats.integrations?.search?.status)}
                </span>
              </div>

              <div className="flex items-center justify-between pb-3 border-b border-borderLine">
                <span className="text-textSecondary">Decision Makers</span>
                <span className="text-textPrimary font-semibold text-right">
                  {stats.integrations?.enrichment?.name || "Enrichment"} — {integrationStatusText(stats.integrations?.enrichment?.status)}
                </span>
              </div>

              <div className="flex items-center justify-between pb-3 border-b border-borderLine">
                <span className="text-textSecondary">Deliverability</span>
                <span className="text-textPrimary font-semibold text-right">
                  {stats.integrations?.verification?.name || "Verification"} — {integrationStatusText(stats.integrations?.verification?.status)}
                </span>
              </div>

              <div className="flex items-center justify-between pb-1">
                <span className="text-textSecondary">Email Outreach</span>
                <span className="text-textPrimary font-semibold text-right">
                  {stats.integrations?.email?.name || "Email"} — {integrationStatusText(stats.integrations?.email?.status)}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-8 pt-4 border-t border-borderLine flex flex-col gap-2.5">
            <Link 
              href="/settings"
              className="w-full py-2.5 rounded-full border border-borderLine hover:bg-accentLight text-textPrimary text-xs font-bold flex items-center justify-center gap-2 transition-colors"
            >
              <Settings className="w-3.5 h-3.5" /> Manage Connections in Settings
            </Link>
            <Link 
              href="/leads"
              className="w-full py-3 rounded-full bg-accent text-card text-xs font-bold flex items-center justify-center gap-2 hover:opacity-90 transition-opacity shadow-sm"
            >
              <span>Open Human Approval Queue</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

      </div>

    </div>
  );
}
