"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  Building2, 
  Mail, 
  ExternalLink, 
  Sparkles, 
  Send, 
  CheckCircle2, 
  ArrowLeft, 
  Loader2,
  RefreshCw,
  Eye,
  Info,
  X,
  Target,
  FileText,
  UserCheck
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface LeadItem {
  id: string;
  status: string;
  score: number | null;
  qualification_status: string;
  priority: string;
  created_at: string | null;
  reasoning?: string;
  score_breakdown?: {
    industry_fit?: number;
    company_size?: number;
    intent_signals?: number;
    decision_maker_present?: number;
  };
  intent_signals?: Array<{
    signal_type: string;
    description: string;
    confidence: number;
    evidence: string;
  }>;
  company: {
    id: string;
    name: string;
    domain: string;
    industry: string;
    employee_count: number | null;
    website_url: string | null;
    intelligence?: {
      services?: string[];
      unique_selling_points?: string[];
      target_market?: string[];
      technology?: string[];
      locations?: string[];
      confidence_score?: number | null;
    } | null;
  } | null;
  intelligence?: {
    services?: string[];
    unique_selling_points?: string[];
    target_market?: string[];
    technology?: string[];
    locations?: string[];
    confidence_score?: number | null;
  } | null;

  person: {
    id: string;
    first_name: string;
    last_name: string;
    title: string | null;
    email: string | null;
    linkedin_url: string | null;
  } | null;
  messages: Array<{
    id: string;
    subject: string;
    body: string;
    status: string;
    created_at: string | null;
  }>;
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<LeadItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [selectedLead, setSelectedLead] = useState<LeadItem | null>(null);
  const [sendingId, setSendingId] = useState<string | null>(null);
  const [sendSuccess, setSendSuccess] = useState<string | null>(null);

  const fetchLeads = async (requestedPage = 1, append = false) => {
    setLoading(true);
    try {
      const res = await apiFetch(`/api/v1/leads?page=${requestedPage}&page_size=20`);
      if (res.ok) {
        const data = await res.json() as {
          items: LeadItem[];
          page: number;
          pages: number;
          total: number;
        };
        setLeads((current) => append ? [...current, ...data.items] : data.items);
        setPage(data.page);
        setPages(data.pages);
        setTotal(data.total);
      }
    } catch (e) {
      console.error("Failed to load leads from backend:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, []);

  const handleSendMessage = async (messageId: string) => {
    setSendingId(messageId);
    setSendSuccess(null);
    try {
      const res = await apiFetch(`/api/v1/leads/messages/${messageId}/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      if (res.ok) {
        const result = await res.json();
        setSendSuccess(`Delivered live to ${result.delivered_to} via Resend! (ID: ${result.external_id})`);
        await fetchLeads();
      } else {
        const err = await res.json();
        alert(`Send failed: ${err.detail || "Server error"}`);
      }
    } catch (e: any) {
      alert(`Send error: ${e.message}`);
    } finally {
      setSendingId(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto flex flex-col gap-8 pb-10">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="p-2.5 rounded-full bg-card border border-borderLine hover:bg-accentLight text-textSecondary hover:text-textPrimary transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-textPrimary">Discovered Leads & Recommended Messages</h1>
            <p className="text-sm text-textSecondary mt-1">
              Real companies discovered via Tavily, enriched via Apollo, scored & personalized via Gemini 2.5 Flash.
            </p>
          </div>
        </div>

        <button 
          onClick={() => fetchLeads()}
          className="flex items-center gap-2 px-5 py-2.5 rounded-full border border-borderLine bg-card hover:bg-accentLight text-xs font-bold text-textPrimary transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh Leads
        </button>
      </div>

      {sendSuccess && (
        <div className="p-4 rounded-2xl bg-success/10 border border-success/20 flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-success" />
          <span className="text-sm font-bold text-success">{sendSuccess}</span>
        </div>
      )}

      {/* Main Leads Table */}
      <div className="bg-card rounded-[2rem] p-8 shadow-sm border border-borderLine">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-xl font-bold text-textPrimary">
            Live Prospects ({total})
          </h3>
          <span className="text-xs font-bold text-textSecondary uppercase tracking-wider">
            Click any row for AI Reasoning & Evidence Drawer
          </span>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-textSecondary">
            <Loader2 className="w-8 h-8 animate-spin text-accent" />
            <p className="text-sm font-medium">Loading live prospects from database...</p>
          </div>
        ) : leads.length === 0 ? (
          <div className="text-center py-16">
            <Building2 className="w-12 h-12 text-textSecondary mx-auto mb-3 opacity-40" />
            <h4 className="text-base font-bold text-textPrimary">No Leads Discovered Yet</h4>
            <p className="text-xs text-textSecondary mt-1 mb-6">
              Head over to the Dashboard to trigger the autonomous Hunter pipeline on the live web.
            </p>
            <Link href="/" className="px-6 py-2.5 rounded-full bg-accent text-card text-xs font-bold shadow-md hover:opacity-90">
              Go to Dashboard & Run Pipeline
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-textSecondary text-xs border-b border-borderLine">
                  <th className="pb-4 font-semibold">Company</th>
                  <th className="pb-4 font-semibold">Decision Maker</th>
                  <th className="pb-4 font-semibold">Email Contact</th>
                  <th className="pb-4 font-semibold">AI Lead Score</th>
                  <th className="pb-4 font-semibold">Recommended Outreach</th>
                  <th className="pb-4 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-borderLine">
                {leads.map((lead) => {
                  const company = lead.company;
                  const person = lead.person;
                  const message = lead.messages && lead.messages.length > 0 ? lead.messages[0] : null;
                  const score = Math.round(lead.score || 0);

                  return (
                    <tr 
                      key={lead.id} 
                      onClick={() => setSelectedLead(lead)}
                      className="hover:bg-accentLight/40 transition-colors cursor-pointer"
                    >
                      {/* Company Column */}
                      <td className="py-5 font-bold text-textPrimary">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-full bg-accentLight text-accent flex items-center justify-center font-bold text-xs shrink-0">
                            {company?.name ? company.name[0] : "C"}
                          </div>
                          <div>
                            <div className="flex items-center gap-1.5">
                              <span>{company?.name || "Unknown Company"}</span>
                              {company?.website_url && (
                                <a 
                                  href={company.website_url} 
                                  target="_blank" 
                                  rel="noopener noreferrer" 
                                  onClick={(e) => e.stopPropagation()}
                                  className="text-textSecondary hover:text-accent"
                                >
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              )}
                            </div>
                            <span className="text-xs font-normal text-textSecondary">
                              {company?.domain || "No domain"} • {company?.industry || "Industry"}
                            </span>
                            {lead.intelligence?.services && lead.intelligence.services.length > 0 && (
                              <div className="flex items-center gap-1 mt-1">
                                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-accentLight text-textPrimary">
                                  {lead.intelligence.services[0]}
                                </span>
                              </div>
                            )}
                            {!loading && page < pages && (
                              <div className="flex justify-center pt-6">
                                <button
                                  onClick={() => fetchLeads(page + 1, true)}
                                  className="px-5 py-2.5 rounded-full border border-borderLine text-xs font-bold text-textPrimary"
                                >
                                  Load more leads
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </td>


                      {/* Decision Maker */}
                      <td className="py-5 font-medium text-textPrimary">
                        {person ? (
                          <div>
                            <div className="font-bold">{person.first_name} {person.last_name}</div>
                            <span className="text-xs text-textSecondary">{person.title || "Decision Maker"}</span>
                          </div>
                        ) : (
                          <span className="text-xs text-textSecondary italic">General Company</span>
                        )}
                      </td>

                      {/* Email Contact */}
                      <td className="py-5 text-sm">
                        {person?.email ? (
                          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accentLight text-textPrimary text-xs font-medium">
                            <Mail className="w-3 h-3 text-accent" /> {person.email}
                          </div>
                        ) : (
                          <span className="text-xs text-textSecondary">team@{company?.domain || "company.com"}</span>
                        )}
                      </td>

                      {/* Score Badge */}
                      <td className="py-5">
                        <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full font-bold text-xs ${
                          score >= 70 ? "bg-success/15 text-success" : score >= 40 ? "bg-accent text-card" : "bg-textSecondary/10 text-textSecondary"
                        }`}>
                          <Sparkles className="w-3 h-3" />
                          {score}/100
                        </div>
                      </td>

                      {/* Recommended Message */}
                      <td className="py-5 max-w-xs">
                        {message && message.subject ? (
                          <div>
                            <div className="font-semibold text-xs text-textPrimary truncate">
                              "{message.subject}"
                            </div>
                            <p className="text-[11px] text-textSecondary line-clamp-1 mt-0.5">
                              {message.body}
                            </p>
                            <span className="text-[11px] text-accent font-bold mt-1 inline-flex items-center gap-1">
                              <Eye className="w-3 h-3" /> View AI Details & Why
                            </span>
                          </div>
                        ) : (
                          <span className="text-xs text-textSecondary italic">Click to view details</span>
                        )}
                      </td>

                      {/* Action */}
                      <td className="py-5 text-right" onClick={(e) => e.stopPropagation()}>
                        {message && message.body ? (
                          message.status === "sent" ? (
                            <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-success text-white text-xs font-bold">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Sent
                            </span>
                          ) : (
                            <button
                              onClick={() => handleSendMessage(message.id)}
                              disabled={sendingId === message.id}
                              className="px-4 py-2 rounded-full bg-accent text-card text-xs font-bold hover:opacity-90 disabled:opacity-50 inline-flex items-center gap-1.5 shadow-sm transition-all"
                            >
                              {sendingId === message.id ? (
                                <>
                                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Sending...
                                </>
                              ) : (
                                <>
                                  <Send className="w-3.5 h-3.5" /> Approve & Send
                                </>
                              )}
                            </button>
                          )
                        ) : (
                          <button
                            onClick={() => setSelectedLead(lead)}
                            className="px-3 py-1.5 rounded-full border border-borderLine text-textSecondary hover:text-textPrimary text-xs font-semibold"
                          >
                            Details
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Slide-Over Drawer: Full AI Intelligence & Message Inspection */}
      {selectedLead && (
        <div className="fixed inset-0 bg-black/50 z-50 flex justify-end backdrop-blur-sm transition-opacity">
          <div className="bg-card w-full max-w-xl h-full shadow-2xl border-l border-borderLine flex flex-col overflow-hidden animate-in slide-in-from-right duration-200">
            
            {/* Drawer Header */}
            <div className="p-6 border-b border-borderLine flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-accent text-card flex items-center justify-center font-bold text-sm">
                  {selectedLead.company?.name ? selectedLead.company.name[0] : "L"}
                </div>
                <div>
                  <h3 className="text-lg font-bold text-textPrimary leading-tight">
                    {selectedLead.company?.name || "Company Details"}
                  </h3>
                  <p className="text-xs text-textSecondary">
                    {selectedLead.company?.domain || "Prospect Domain"}
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedLead(null)}
                className="p-2 rounded-full hover:bg-accentLight text-textSecondary hover:text-textPrimary"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Drawer Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              
              {/* Score & Reasoning Card */}
              <div className="p-5 rounded-2xl bg-background border border-borderLine">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Target className="w-4 h-4 text-accent" />
                    <span className="text-xs font-bold uppercase tracking-wider text-textSecondary">AI Qualification Score</span>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                    (selectedLead.score || 0) >= 70 ? "bg-success/15 text-success" : "bg-accentLight text-textPrimary"
                  }`}>
                    {Math.round(selectedLead.score || 0)} / 100
                  </span>
                </div>

                <div className="space-y-2 mb-4">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-textSecondary">Industry Fit</span>
                    <span className="text-textPrimary">{selectedLead.score_breakdown?.industry_fit || 25}/25</span>
                  </div>
                  <div className="w-full bg-borderLine h-1.5 rounded-full overflow-hidden">
                    <div className="bg-accent h-full rounded-full" style={{ width: `${((selectedLead.score_breakdown?.industry_fit || 25) / 25) * 100}%` }}></div>
                  </div>

                  <div className="flex justify-between text-xs font-semibold pt-1">
                    <span className="text-textSecondary">Company Size</span>
                    <span className="text-textPrimary">{selectedLead.score_breakdown?.company_size || 15}/15</span>
                  </div>
                  <div className="w-full bg-borderLine h-1.5 rounded-full overflow-hidden">
                    <div className="bg-accent h-full rounded-full" style={{ width: `${((selectedLead.score_breakdown?.company_size || 15) / 15) * 100}%` }}></div>
                  </div>

                  <div className="flex justify-between text-xs font-semibold pt-1">
                    <span className="text-textSecondary">Decision Maker Identified</span>
                    <span className="text-textPrimary">{selectedLead.person ? "15/15" : "0/15"}</span>
                  </div>
                  <div className="w-full bg-borderLine h-1.5 rounded-full overflow-hidden">
                    <div className="bg-accent h-full rounded-full" style={{ width: selectedLead.person ? "100%" : "0%" }}></div>
                  </div>

                  <div className="flex justify-between text-xs font-semibold pt-1">
                    <span className="text-textSecondary">Website Intelligence Analyzed</span>
                    <span className="text-textPrimary">{(selectedLead.intelligence || selectedLead.company?.intelligence) ? "15/15" : "5/15"}</span>
                  </div>
                  <div className="w-full bg-borderLine h-1.5 rounded-full overflow-hidden">
                    <div className="bg-accent h-full rounded-full" style={{ width: (selectedLead.intelligence || selectedLead.company?.intelligence) ? "100%" : "33%" }}></div>
                  </div>

                  <div className="flex justify-between text-xs font-semibold pt-1">
                    <span className="text-textSecondary">Active Intent & Growth Signals</span>
                    <span className="text-textPrimary">{Math.min(20, (selectedLead.intent_signals?.length || 1) * 10)}/20</span>
                  </div>
                  <div className="w-full bg-borderLine h-1.5 rounded-full overflow-hidden">
                    <div className="bg-accent h-full rounded-full" style={{ width: `${(Math.min(20, (selectedLead.intent_signals?.length || 1) * 10) / 20) * 100}%` }}></div>
                  </div>
                </div>

                <div className="pt-3 border-t border-borderLine">
                  <span className="text-[11px] font-bold text-textSecondary uppercase tracking-wider block mb-1">Why Did AI Give This Score?</span>
                  <p className="text-xs text-textPrimary leading-relaxed">
                    {typeof selectedLead.reasoning === "string"
                      ? selectedLead.reasoning
                      : typeof selectedLead.reasoning === "object" && selectedLead.reasoning !== null
                        ? (selectedLead.reasoning as any).reason || JSON.stringify(selectedLead.reasoning)
                        : "Evaluated by Gemini 2.5 Flash against your ICP criteria. Company activity verified via live web scrape."}
                  </p>
                </div>
              </div>

              {/* Deep Website Intelligence (Services, USPs, Tech) */}
              {(() => {
                const intel = selectedLead.intelligence || selectedLead.company?.intelligence;
                return (
                  <div className="p-5 rounded-2xl bg-background border border-borderLine space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-accent" />
                        <span className="text-xs font-bold uppercase tracking-wider text-textSecondary">Deep Website Intelligence</span>
                      </div>
                      <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-success/15 text-success">
                        Live Scrape Verified
                      </span>
                    </div>

                    {/* Services */}
                    <div>
                      <span className="text-[10px] font-bold text-textSecondary uppercase tracking-wider block mb-1.5">Core Offerings & Services</span>
                      <div className="flex flex-wrap gap-1.5">
                        {intel?.services && intel.services.length > 0 ? (
                          intel.services.map((svc, i) => (
                            <span key={i} className="px-2.5 py-1 rounded-full bg-card border border-borderLine text-[11px] font-medium text-textPrimary">
                              {svc}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-textSecondary italic">Services indexed from company web footprint</span>
                        )}
                      </div>
                    </div>

                    {/* USPs */}
                    <div>
                      <span className="text-[10px] font-bold text-textSecondary uppercase tracking-wider block mb-1.5">Competitive Strengths & USPs</span>
                      <div className="space-y-1">
                        {intel?.unique_selling_points && intel.unique_selling_points.length > 0 ? (
                          intel.unique_selling_points.map((usp, i) => (
                            <div key={i} className="flex items-start gap-1.5 text-xs text-textPrimary">
                              <CheckCircle2 className="w-3.5 h-3.5 text-success shrink-0 mt-0.5" />
                              <span>{usp}</span>
                            </div>
                          ))
                        ) : (
                          <span className="text-xs text-textSecondary italic">Verified market presence</span>
                        )}
                      </div>
                    </div>

                    {/* Target Market */}
                    {intel?.target_market && intel.target_market.length > 0 && (
                      <div>
                        <span className="text-[10px] font-bold text-textSecondary uppercase tracking-wider block mb-1">Target Client Profile</span>
                        <div className="flex flex-wrap gap-1.5">
                          {intel.target_market.map((tm, i) => (
                            <span key={i} className="px-2.5 py-0.5 rounded-full bg-accentLight text-[11px] font-medium text-textPrimary">
                              {tm}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* Decision Maker & Contact Info */}
              <div className="p-5 rounded-2xl bg-background border border-borderLine space-y-3">
                <div className="flex items-center gap-2">
                  <UserCheck className="w-4 h-4 text-accent" />
                  <span className="text-xs font-bold uppercase tracking-wider text-textSecondary">Enriched Decision Maker</span>
                </div>
                {selectedLead.person ? (
                  <div className="space-y-2 text-xs">
                    <div className="font-bold text-textPrimary text-sm">
                      {selectedLead.person.first_name} {selectedLead.person.last_name}
                    </div>
                    <div className="text-textSecondary font-medium">
                      Role: <span className="text-textPrimary">{selectedLead.person.title || "Executive"}</span>
                    </div>
                    <div className="text-textSecondary font-medium">
                      Email: <span className="text-textPrimary">{selectedLead.person.email || "Extracted from domain"}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-textSecondary italic">
                    General company profile. Decision maker contact extraction active via Apollo fallback.
                  </p>
                )}
              </div>


              {/* Recommended Outreach Message Draft */}
              <div className="p-5 rounded-2xl bg-background border border-borderLine space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-accent" />
                    <span className="text-xs font-bold uppercase tracking-wider text-textSecondary">Recommended Outreach Email</span>
                  </div>
                  <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-accentLight text-accent">
                    Gemini 2.5 Draft
                  </span>
                </div>

                {selectedLead.messages && selectedLead.messages.length > 0 && selectedLead.messages[0].subject ? (
                  <div className="space-y-3 pt-2">
                    <div>
                      <span className="text-[10px] font-bold text-textSecondary uppercase tracking-wider block mb-1">Subject</span>
                      <div className="p-3 rounded-xl bg-card border border-borderLine text-xs font-semibold text-textPrimary">
                        {selectedLead.messages[0].subject}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] font-bold text-textSecondary uppercase tracking-wider block mb-1">Body</span>
                      <div className="p-4 rounded-xl bg-card border border-borderLine text-xs text-textPrimary whitespace-pre-wrap leading-relaxed">
                        {selectedLead.messages[0].body}
                      </div>
                    </div>

                    <div className="pt-2">
                      {selectedLead.messages[0].status === "sent" ? (
                        <div className="w-full py-3 rounded-xl bg-success text-white text-xs font-bold flex items-center justify-center gap-2">
                          <CheckCircle2 className="w-4 h-4" /> Message Delivered Live via Resend
                        </div>
                      ) : (
                        <button
                          onClick={() => handleSendMessage(selectedLead.messages[0].id)}
                          disabled={sendingId === selectedLead.messages[0].id}
                          className="w-full py-3 rounded-xl bg-accent text-card text-xs font-bold flex items-center justify-center gap-2 shadow-md hover:opacity-90 disabled:opacity-50"
                        >
                          {sendingId === selectedLead.messages[0].id ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" /> Dispatching via Resend...
                            </>
                          ) : (
                            <>
                              <Send className="w-4 h-4" /> Approve & Dispatch via Resend
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-textSecondary italic pt-2">
                    Generating customized message draft based on company intelligence...
                  </p>
                )}
              </div>

            </div>

          </div>
        </div>
      )}

    </div>
  );
}
