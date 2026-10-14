"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  PieChart, 
  TrendingUp, 
  Sparkles, 
  ArrowLeft, 
  Loader2, 
  RefreshCw, 
  CheckCircle2, 
  BarChart3, 
  Zap, 
  Activity, 
  ShieldCheck,
  Target,
  Send,
  Calendar,
  Users
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface AnalyticsData {
  funnel: Array<{
    stage: string;
    count: number;
    color: string;
  }>;
  score_distribution: {
    high_priority: number;
    qualified: number;
    nurture: number;
    disqualified: number;
    unscored: number;
  };
  rates: {
    qualification_rate: number;
    outreach_dispatch_rate: number;
    meeting_conversion_rate: number;
  };
  integrations_status: Record<string, {
    provider: string;
    status: string;
    latency_ms?: number;
    quota?: string;
  }>;
  rate_counts: Record<string, { numerator: number; denominator: number }>;
  rate_definitions: Record<string, string>;
  data_scope: string;
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const res = await apiFetch("/api/v1/analytics/overview");
      if (res.ok) {
        const d = await res.json();
        setData(d);
      }
    } catch (e) {
      console.error("Failed to load analytics:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const totalScores = data
    ? (data.score_distribution.high_priority +
       data.score_distribution.qualified +
       data.score_distribution.nurture +
       data.score_distribution.disqualified +
       data.score_distribution.unscored) || 1
    : 1;

  const maxFunnelCount = data?.funnel?.[0]?.count || 1;

  return (
    <div className="max-w-7xl mx-auto flex flex-col gap-8 pb-10">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="p-2.5 rounded-full bg-card border border-borderLine hover:bg-accentLight text-textSecondary hover:text-textPrimary transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-textPrimary">Revenue Analytics & Funnel Velocity</h1>
            <p className="text-sm text-textSecondary mt-1">
              Organization-scoped totals and conversion rates calculated from persisted records.
            </p>
          </div>
        </div>

        <button 
          onClick={fetchAnalytics} 
          className="flex items-center gap-2 px-5 py-2.5 rounded-full border border-borderLine bg-card hover:bg-accentLight text-xs font-bold text-textPrimary transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 gap-3 text-textSecondary">
          <Loader2 className="w-8 h-8 animate-spin text-accent" />
          <p className="text-sm font-medium">Aggregating real pipeline metrics...</p>
        </div>
      ) : data ? (
        <>
          {/* Conversion Rates Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-card rounded-[2rem] p-6 border border-borderLine">
              <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
                <span>AI QUALIFICATION RATE</span>
                <Target className="w-4 h-4 text-accent" />
              </div>
              <div className="mt-3">
                <span className="text-3xl font-bold text-textPrimary">{data.rates.qualification_rate}%</span>
                <span className="text-xs text-textSecondary block mt-1">Discovered accounts scoring ≥ 70</span>
              </div>
            </div>

            <div className="bg-card rounded-[2rem] p-6 border border-borderLine">
              <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
                <span>OUTREACH DISPATCH RATE</span>
                <Send className="w-4 h-4 text-accent" />
              </div>
              <div className="mt-3">
                <span className="text-3xl font-bold text-textPrimary">{data.rates.outreach_dispatch_rate}%</span>
                <span className="text-xs text-textSecondary block mt-1">{data.rate_counts.outreach_dispatch_rate.numerator} sent / {data.rate_counts.outreach_dispatch_rate.denominator} outbound messages</span>
              </div>
            </div>

            <div className="bg-card rounded-[2rem] p-6 border border-borderLine">
              <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
                <span>MEETING CONVERSION VELOCITY</span>
                <Calendar className="w-4 h-4 text-success" />
              </div>
              <div className="mt-3">
                <span className="text-3xl font-bold text-success">{data.rates.meeting_conversion_rate}%</span>
                <span className="text-xs text-textSecondary block mt-1">{data.rate_counts.meeting_conversion_rate.numerator} meetings / {data.rate_counts.meeting_conversion_rate.denominator} sent messages</span>
              </div>
            </div>
          </div>

          {/* Pipeline Funnel Visualizer */}
          <div className="bg-card rounded-[2rem] p-8 shadow-sm border border-borderLine">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h3 className="text-xl font-bold text-textPrimary">Autonomous Pipeline Funnel</h3>
                <p className="text-xs text-textSecondary mt-0.5">{data.data_scope}</p>
              </div>
              <span className="text-xs font-bold text-textSecondary uppercase tracking-wider">
              Database counts
              </span>
            </div>

            <div className="space-y-4">
              {data.funnel.map((f, i) => {
                const percent = Math.max(8, Math.round((f.count / maxFunnelCount) * 100));

                return (
                  <div key={i} className="p-4 rounded-2xl bg-background border border-borderLine space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2 font-bold text-textPrimary">
                        <span className="w-6 h-6 rounded-full bg-accentLight text-accent flex items-center justify-center text-[10px]">
                          0{i + 1}
                        </span>
                        <span>{f.stage}</span>
                      </div>
                      <span className="text-sm font-bold text-textPrimary">{f.count} Accounts</span>
                    </div>

                    <div className="w-full bg-card h-2.5 rounded-full overflow-hidden border border-borderLine">
                      <div 
                        className="bg-accent h-full rounded-full transition-all duration-500" 
                        style={{ width: `${percent}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Grid: 2 Columns (Score Distribution & Live Provider Health) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            
            {/* Score Distribution */}
            <div className="bg-card rounded-[2rem] p-8 shadow-sm border border-borderLine flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-9 h-9 rounded-full bg-accentLight text-accent flex items-center justify-center">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-textPrimary">Lead Score Breakdown</h3>
                    <p className="text-xs text-textSecondary">Stored lead scores; unscored leads are reported separately.</p>
                  </div>
                </div>

                <div className="space-y-4">
                  {/* High Priority */}
                  <div className="flex items-center justify-between p-3.5 rounded-2xl bg-background border border-borderLine">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-success"></span>
                        <span className="text-xs font-bold text-textPrimary">High Priority (Score 85–100)</span>
                      </div>
                      <span className="text-[11px] text-textSecondary mt-0.5 block">Perfect ICP, decision maker identified</span>
                    </div>
                    <span className="text-base font-bold text-success">{data.score_distribution.high_priority}</span>
                  </div>

                  {/* Qualified */}
                  <div className="flex items-center justify-between p-3.5 rounded-2xl bg-background border border-borderLine">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-accent"></span>
                        <span className="text-xs font-bold text-textPrimary">Qualified (Score 70–84)</span>
                      </div>
                      <span className="text-[11px] text-textSecondary mt-0.5 block">Solid industry match, verified web presence</span>
                    </div>
                    <span className="text-base font-bold text-textPrimary">{data.score_distribution.qualified}</span>
                  </div>

                  {/* Nurture */}
                  <div className="flex items-center justify-between p-3.5 rounded-2xl bg-background border border-borderLine">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-textSecondary"></span>
                        <span className="text-xs font-bold text-textPrimary">Nurture (Score 40–69)</span>
                      </div>
                      <span className="text-[11px] text-textSecondary mt-0.5 block">Emerging prospect or missing executive info</span>
                    </div>
                    <span className="text-base font-bold text-textSecondary">{data.score_distribution.nurture}</span>
                  </div>

                  {/* Disqualified */}
                  <div className="flex items-center justify-between p-3.5 rounded-2xl bg-background border border-borderLine">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-red-400"></span>
                        <span className="text-xs font-bold text-textPrimary">Disqualified (&lt; 40)</span>
                      </div>
                      <span className="text-[11px] text-textSecondary mt-0.5 block">Outside ICP parameters</span>
                    </div>
                    <span className="text-base font-bold text-red-500">{data.score_distribution.disqualified}</span>
                  </div>
                  <div className="flex items-center justify-between p-3.5 rounded-2xl bg-background border border-borderLine">
                    <span className="text-xs font-bold text-textPrimary">Unscored</span>
                    <span className="text-base font-bold text-textSecondary">{data.score_distribution.unscored}</span>
                  </div>
                </div>
              </div>

              <div className="pt-6 border-t border-borderLine mt-6 flex items-center justify-between text-xs text-textSecondary">
                <span>Total Evaluated Prospects:</span>
                <strong className="text-textPrimary">{totalScores}</strong>
              </div>
            </div>

            {/* Provider Health & Latencies */}
            <div className="bg-card rounded-[2rem] p-8 shadow-sm border border-borderLine flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-9 h-9 rounded-full bg-accentLight text-accent flex items-center justify-center">
                    <Activity className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-textPrimary">Provider Diagnostics & Latencies</h3>
                    <p className="text-xs text-textSecondary">Configuration only unless a provider probe is explicitly reported.</p>
                  </div>
                </div>

                <div className="space-y-3">
                  {Object.entries(data.integrations_status).map(([k, v]) => (
                    <div key={k} className="p-3.5 rounded-2xl bg-background border border-borderLine flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <Activity className="w-4 h-4 text-textSecondary" />
                          <span className="text-xs font-bold text-textPrimary">{v.provider}</span>
                        </div>
                        <span className="text-[11px] text-textSecondary mt-0.5 block">
                          {v.latency_ms ? `Probe latency: ${v.latency_ms}ms` : "Connectivity not tested"}
                        </span>
                      </div>
                      <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-500 uppercase">
                      {v.status.replaceAll("_", " ")}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-6 border-t border-borderLine mt-6">
                <Link 
                  href="/settings"
                  className="w-full py-2.5 rounded-full border border-borderLine hover:bg-accentLight text-textPrimary text-xs font-bold text-center block transition-colors"
                >
                  Configure Live Keys & Policies →
                </Link>
              </div>
            </div>

          </div>
        </>
      ) : null}

    </div>
  );
}
