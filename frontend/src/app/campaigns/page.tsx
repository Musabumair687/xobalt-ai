"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  FileText, 
  Plus, 
  Sparkles, 
  Users, 
  Send, 
  CheckCircle2, 
  ArrowLeft, 
  Loader2, 
  RefreshCw, 
  Target, 
  Play, 
  X,
  ChevronRight,
  ShieldCheck,
  TrendingUp
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface CampaignItem {
  id: string;
  name: string;
  description: string | null;
  status: string;
  target_industry: string;
  daily_limit: number;
  settings: {
    offer?: string;
  };
  lead_count: number;
  message_count: number;
  sent_count: number;
  created_at: string | null;
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<CampaignItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [creating, setCreating] = useState(false);

  // New Campaign Form
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("Real Estate");
  const [offer, setOffer] = useState("Strategic business development & partnership expansion");
  const [dailyLimit, setDailyLimit] = useState(30);

  const fetchCampaigns = async (requestedPage = 1, append = false) => {
    setLoading(true);
    try {
      const res = await apiFetch(`/api/v1/campaigns?page=${requestedPage}&page_size=20`);
      if (res.ok) {
        const data = await res.json() as {
          items: CampaignItem[];
          page: number;
          pages: number;
          total: number;
        };
        setCampaigns((current) => append ? [...current, ...data.items] : data.items);
        setPage(data.page);
        setPages(data.pages);
        setTotal(data.total);
      }
    } catch (e) {
      console.error("Failed to load campaigns:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const res = await apiFetch("/api/v1/campaigns", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          target_industry: industry,
          offer,
          daily_limit: dailyLimit,
        }),
      });
      if (res.ok) {
        setShowModal(false);
        setName("");
        await fetchCampaigns();
      } else {
        const err = await res.json();
        alert(`Creation failed: ${err.detail || "Server error"}`);
      }
    } catch (e: any) {
      alert(`Error creating campaign: ${e.message}`);
    } finally {
      setCreating(false);
    }
  };

  const totalLeads = campaigns.reduce((acc, c) => acc + (c.lead_count || 0), 0);
  const totalSent = campaigns.reduce((acc, c) => acc + (c.sent_count || 0), 0);

  return (
    <div className="max-w-7xl mx-auto flex flex-col gap-8 pb-10">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="p-2.5 rounded-full bg-card border border-borderLine hover:bg-accentLight text-textSecondary hover:text-textPrimary transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-textPrimary">Outbound Campaigns & Growth Plays</h1>
            <p className="text-sm text-textSecondary mt-1">
              Automated multi-stage outreach campaigns segmented by target industry and ICP criteria.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={() => fetchCampaigns()}
            className="flex items-center gap-2 px-5 py-2.5 rounded-full border border-borderLine bg-card hover:bg-accentLight text-xs font-bold text-textPrimary transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
          </button>
          <button 
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-accent text-card text-xs font-bold shadow-md hover:opacity-90 transition-opacity"
          >
            <Plus className="w-4 h-4" /> New Campaign
          </button>
        </div>
      </div>

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card rounded-[2rem] p-6 border border-borderLine flex flex-col justify-between">
          <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
            <span>ACTIVE CAMPAIGNS</span>
            <FileText className="w-4 h-4 text-accent" />
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-textPrimary">{campaigns.length}</span>
            <span className="text-xs text-textSecondary block mt-1">Targeting unique ICP sectors</span>
          </div>
        </div>

        <div className="bg-card rounded-[2rem] p-6 border border-borderLine flex flex-col justify-between">
          <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
            <span>TOTAL ENROLLED LEADS</span>
            <Users className="w-4 h-4 text-accent" />
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-textPrimary">{totalLeads}</span>
            <span className="text-xs text-textSecondary block mt-1">Discovered via live Hunter search</span>
          </div>
        </div>

        <div className="bg-card rounded-[2rem] p-6 border border-borderLine flex flex-col justify-between">
          <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
            <span>DELIVERED OUTREACH</span>
            <Send className="w-4 h-4 text-accent" />
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-textPrimary">{totalSent}</span>
            <span className="text-xs text-textSecondary block mt-1">Dispatched live via Resend API</span>
          </div>
        </div>

        <div className="bg-card rounded-[2rem] p-6 border border-borderLine flex flex-col justify-between">
          <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
            <span>AI ENFORCER POLICY</span>
            <ShieldCheck className="w-4 h-4 text-success" />
          </div>
          <div className="mt-3">
            <span className="text-sm font-bold text-success flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" /> Human Review Enforced
            </span>
            <span className="text-xs text-textSecondary block mt-1">Zero unauthorized spam</span>
          </div>
        </div>
      </div>

      {/* Campaigns Grid */}
      <div className="bg-card rounded-[2rem] p-8 shadow-sm border border-borderLine">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-xl font-bold text-textPrimary">All Campaigns</h3>
          <span className="text-xs font-bold text-textSecondary uppercase tracking-wider">
            {total} Campaigns
          </span>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-textSecondary">
            <Loader2 className="w-8 h-8 animate-spin text-accent" />
            <p className="text-sm font-medium">Loading campaign records...</p>
          </div>
        ) : campaigns.length === 0 ? (
          <div className="text-center py-16">
            <Target className="w-12 h-12 text-textSecondary mx-auto mb-3 opacity-40" />
            <h4 className="text-base font-bold text-textPrimary">No Campaigns Created Yet</h4>
            <p className="text-xs text-textSecondary mt-1 mb-6">
              Create your first outbound campaign to define value propositions and industry targeting.
            </p>
            <button 
              onClick={() => setShowModal(true)} 
              className="px-6 py-2.5 rounded-full bg-accent text-card text-xs font-bold shadow-md hover:opacity-90"
            >
              + Create First Campaign
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {campaigns.map((c) => (
              <div 
                key={c.id} 
                className="p-6 rounded-[1.8rem] bg-background border border-borderLine flex flex-col justify-between hover:border-accent/40 transition-all hover:shadow-md"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="px-3 py-1 rounded-full text-[10px] font-bold bg-success/15 text-success uppercase">
                      {c.status}
                    </span>
                    <span className="text-[11px] text-textSecondary font-semibold">
                      Max {c.daily_limit}/day
                    </span>
                  </div>

                  <h4 className="text-lg font-bold text-textPrimary mb-1">{c.name}</h4>
                  <div className="flex items-center gap-1.5 text-xs text-textSecondary mb-4">
                    <span className="font-semibold text-textPrimary">{c.target_industry}</span>
                    <span>•</span>
                    <span>Created {c.created_at ? new Date(c.created_at).toLocaleDateString() : "Recently"}</span>
                  </div>

                  <div className="p-3.5 rounded-2xl bg-card border border-borderLine mb-4">
                    <span className="text-[10px] font-bold text-textSecondary uppercase tracking-wider block mb-1">Target Offer</span>
                    <p className="text-xs text-textPrimary line-clamp-2">
                      {c.settings?.offer || "AI-powered automated client acquisition pipeline"}
                    </p>
                  </div>

                  <div className="grid grid-cols-3 gap-2 py-3 border-t border-borderLine text-center mb-4">
                    <div>
                      <span className="text-lg font-bold text-textPrimary block">{c.lead_count}</span>
                      <span className="text-[10px] text-textSecondary font-medium uppercase">Leads</span>
                    </div>
                    <div>
                      <span className="text-lg font-bold text-textPrimary block">{c.message_count}</span>
                      <span className="text-[10px] text-textSecondary font-medium uppercase">Drafts</span>
                    </div>
                    <div>
                      <span className="text-lg font-bold text-success block">{c.sent_count}</span>
                      <span className="text-[10px] text-textSecondary font-medium uppercase">Sent</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-2">
                  <Link 
                    href="/leads"
                    className="flex-1 py-2.5 rounded-full bg-accent text-card text-xs font-bold text-center hover:opacity-90 transition-opacity"
                  >
                    View Prospects
                  </Link>
                  <Link 
                    href="/inbox"
                    className="px-4 py-2.5 rounded-full border border-borderLine hover:bg-accentLight text-textSecondary hover:text-textPrimary text-xs font-bold transition-colors"
                  >
                    Outbox
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
        {!loading && page < pages && (
          <div className="flex justify-center pt-6">
            <button
              onClick={() => fetchCampaigns(page + 1, true)}
              className="px-5 py-2.5 rounded-full border border-borderLine text-xs font-bold text-textPrimary"
            >
              Load more campaigns
            </button>
          </div>
        )}
      </div>

      {/* Create Campaign Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-card w-full max-w-lg rounded-[2.5rem] p-8 shadow-2xl border border-borderLine animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-accentLight text-accent flex items-center justify-center font-bold">
                  <Target className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-textPrimary">Create Outbound Campaign</h3>
                  <p className="text-xs text-textSecondary">Configure your target ICP industry and value offer.</p>
                </div>
              </div>
              <button 
                onClick={() => setShowModal(false)}
                className="p-2 rounded-full hover:bg-accentLight text-textSecondary"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateCampaign} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-textPrimary block mb-1.5">Campaign Name</label>
                <input 
                  type="text" 
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Q4 Real Estate Acquisition"
                  required
                  className="w-full px-4 py-3 rounded-full border border-borderLine bg-background text-textPrimary text-xs focus:outline-none focus:border-accent"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-textPrimary block mb-1.5">Target Industry / ICP</label>
                <input 
                  type="text" 
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  placeholder="e.g. Real Estate, SaaS, Fintech, Healthcare"
                  required
                  className="w-full px-4 py-3 rounded-full border border-borderLine bg-background text-textPrimary text-xs focus:outline-none focus:border-accent"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-textPrimary block mb-1.5">Value Proposition / Offer</label>
                <textarea 
                  value={offer}
                  onChange={(e) => setOffer(e.target.value)}
                  rows={3}
                  placeholder="Describe what value or services the AI should pitch to these accounts..."
                  required
                  className="w-full px-4 py-3 rounded-2xl border border-borderLine bg-background text-textPrimary text-xs focus:outline-none focus:border-accent resize-none"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-textPrimary block mb-1.5">Daily Outbound Sending Cap</label>
                <input 
                  type="number" 
                  min={1} 
                  max={200}
                  value={dailyLimit}
                  onChange={(e) => setDailyLimit(Number(e.target.value))}
                  className="w-full px-4 py-3 rounded-full border border-borderLine bg-background text-textPrimary text-xs focus:outline-none focus:border-accent"
                />
                <span className="text-[11px] text-textSecondary mt-1 block">Protects sender reputation across provider mailboxes.</span>
              </div>

              <div className="pt-4 flex items-center justify-end gap-3">
                <button 
                  type="button" 
                  onClick={() => setShowModal(false)}
                  className="px-5 py-2.5 rounded-full border border-borderLine text-textSecondary hover:text-textPrimary text-xs font-bold"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={creating}
                  className="px-6 py-2.5 rounded-full bg-accent text-card text-xs font-bold shadow-md hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
                >
                  {creating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                  {creating ? "Creating Campaign..." : "Create Campaign"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
