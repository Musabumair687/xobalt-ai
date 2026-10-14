"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  Users, 
  Mail, 
  Send, 
  CheckCircle2, 
  Clock, 
  ArrowLeft, 
  Loader2, 
  RefreshCw, 
  Sparkles, 
  Edit3, 
  Eye, 
  X,
  Building2,
  ShieldCheck,
  Check
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface MessageItem {
  id: string;
  lead_id: string | null;
  subject: string;
  body: string;
  status: string;
  sent_at: string | null;
  created_at: string | null;
  recipient_name: string;
  recipient_title: string;
  recipient_email: string | null;
  company_name: string;
  company_domain: string | null;
  lead_score: number | null;
}

export default function InboxPage() {
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<"all" | "pending" | "sent">("all");
  const [selectedMsg, setSelectedMsg] = useState<MessageItem | null>(null);
  const [sendingId, setSendingId] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Edit fields
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");

  const fetchMessages = async (requestedPage = 1, append = false) => {
    setLoading(true);
    try {
      const res = await apiFetch(`/api/v1/conversations/messages?page=${requestedPage}&page_size=20`);
      if (res.ok) {
        const data = await res.json() as {
          items: MessageItem[];
          page: number;
          pages: number;
          total: number;
        };
        setMessages((current) => append ? [...current, ...data.items] : data.items);
        setPage(data.page);
        setPages(data.pages);
        setTotal(data.total);
      }
    } catch (e) {
      console.error("Failed to load messages:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMessages();
  }, []);

  const openReviewModal = (msg: MessageItem) => {
    setSelectedMsg(msg);
    setEditSubject(msg.subject);
    setEditBody(msg.body);
  };

  const handleSend = async (msgId: string) => {
    setSendingId(msgId);
    setSuccessBanner(null);
    try {
      const res = await apiFetch(`/api/v1/leads/messages/${msgId}/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          edited_subject: editSubject,
          edited_body: editBody,
        }),
      });
      if (res.ok) {
        const result = await res.json();
        setSuccessBanner(`Dispatched live to ${result.delivered_to} via Resend! (ID: ${result.external_id})`);
        setSelectedMsg(null);
        await fetchMessages();
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

  const filtered = messages.filter((m) => {
    if (filter === "pending") return m.status !== "sent";
    if (filter === "sent") return m.status === "sent";
    return true;
  });

  const pendingCount = messages.filter((m) => m.status !== "sent").length;
  const sentCount = messages.filter((m) => m.status === "sent").length;

  return (
    <div className="max-w-7xl mx-auto flex flex-col gap-8 pb-10">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="p-2.5 rounded-full bg-card border border-borderLine hover:bg-accentLight text-textSecondary hover:text-textPrimary transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-textPrimary">Outreach & Approval Center</h1>
            <p className="text-sm text-textSecondary mt-1">
              Review, edit, and authorize Gemini 2.5 Flash personalized email drafts before live Resend dispatch.
            </p>
          </div>
        </div>

        <button 
          onClick={() => fetchMessages()}
          className="flex items-center gap-2 px-5 py-2.5 rounded-full border border-borderLine bg-card hover:bg-accentLight text-xs font-bold text-textPrimary transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      {successBanner && (
        <div className="p-4 rounded-2xl bg-success/10 border border-success/20 flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-success" />
          <span className="text-sm font-bold text-success">{successBanner}</span>
        </div>
      )}

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card rounded-[2rem] p-6 border border-borderLine flex flex-col justify-between">
          <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
            <span>TOTAL GENERATED</span>
            <Mail className="w-4 h-4 text-accent" />
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-textPrimary">            {total}</span>
            <span className="text-xs text-textSecondary block mt-1">AI hyper-personalized drafts</span>
          </div>
        </div>

        <div className="bg-card rounded-[2rem] p-6 border border-borderLine flex flex-col justify-between">
          <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
            <span>AWAITING APPROVAL</span>
            <Clock className="w-4 h-4 text-accent" />
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-accent">{pendingCount}</span>
            <span className="text-xs text-textSecondary block mt-1">Pending human verification</span>
          </div>
        </div>

        <div className="bg-card rounded-[2rem] p-6 border border-borderLine flex flex-col justify-between">
          <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
            <span>DISPATCHED LIVE</span>
            <Send className="w-4 h-4 text-success" />
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-success">{sentCount}</span>
            <span className="text-xs text-textSecondary block mt-1">Sent via Resend mail delivery</span>
          </div>
        </div>

        <div className="bg-card rounded-[2rem] p-6 border border-borderLine flex flex-col justify-between">
          <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
            <span>GUARDRAIL STATUS</span>
            <ShieldCheck className="w-4 h-4 text-success" />
          </div>
          <div className="mt-3">
            <span className="text-sm font-bold text-success flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" /> 100% Guardrails Active
            </span>
            <span className="text-xs text-textSecondary block mt-1">Zero unauthorized automated sends</span>
          </div>
        </div>
      </div>

      {/* Filter Tabs & Messages List */}
      <div className="bg-card rounded-[2rem] p-8 shadow-sm border border-borderLine">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <div className="flex items-center gap-2 p-1 rounded-full bg-background border border-borderLine">
            <button 
              onClick={() => setFilter("all")}
              className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
                filter === "all" ? "bg-accent text-card shadow-sm" : "text-textSecondary hover:text-textPrimary"
              }`}
            >
              All Messages ({messages.length})
            </button>
            <button 
              onClick={() => setFilter("pending")}
              className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
                filter === "pending" ? "bg-accent text-card shadow-sm" : "text-textSecondary hover:text-textPrimary"
              }`}
            >
              Pending Approval ({pendingCount})
            </button>
            <button 
              onClick={() => setFilter("sent")}
              className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
                filter === "sent" ? "bg-accent text-card shadow-sm" : "text-textSecondary hover:text-textPrimary"
              }`}
            >
              Sent Live ({sentCount})
            </button>
          </div>

          <span className="text-xs font-bold text-textSecondary uppercase tracking-wider">
            1-Click Resend Dispatch
          </span>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-textSecondary">
            <Loader2 className="w-8 h-8 animate-spin text-accent" />
            <p className="text-sm font-medium">Loading outbound message streams...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16">
            <Mail className="w-12 h-12 text-textSecondary mx-auto mb-3 opacity-40" />
            <h4 className="text-base font-bold text-textPrimary">No Messages Found in this View</h4>
            <p className="text-xs text-textSecondary mt-1 mb-6">
              Discover leads on the Dashboard to automatically draft hyper-personalized pitches.
            </p>
            <Link href="/" className="px-6 py-2.5 rounded-full bg-accent text-card text-xs font-bold shadow-md hover:opacity-90">
              Run Hunter Pipeline
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.map((msg) => {
              const isSent = msg.status === "sent";
              const score = Math.round(msg.lead_score || 0);

              return (
                <div 
                  key={msg.id}
                  className="p-6 rounded-[1.8rem] bg-background border border-borderLine hover:border-accent/40 transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-6"
                >
                  <div className="flex-1 space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        isSent ? "bg-success/15 text-success" : "bg-accentLight text-accent"
                      }`}>
                        {isSent ? "DELIVERED LIVE" : "READY FOR APPROVAL"}
                      </span>

                      {msg.lead_score && (
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-card border border-borderLine text-textPrimary flex items-center gap-1">
                          <Sparkles className="w-3 h-3 text-accent" /> Score: {score}/100
                        </span>
                      )}

                      <span className="text-xs text-textSecondary">
                        To: <strong className="text-textPrimary">{msg.recipient_name}</strong> ({msg.recipient_title}) at <strong className="text-textPrimary">{msg.company_name}</strong>
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-textPrimary">
                      {msg.subject || "Outreach Pitch"}
                    </h4>

                    <p className="text-xs text-textSecondary line-clamp-2 leading-relaxed">
                      {msg.body}
                    </p>

                    <div className="flex items-center gap-2 text-[11px] text-textSecondary pt-1">
                      <span>Delivery Target: <strong className="text-textPrimary">{msg.recipient_email || "Verified Domain Contact"}</strong></span>
                      {msg.sent_at && (
                        <>
                          <span>•</span>
                          <span>Dispatched: {new Date(msg.sent_at).toLocaleString()}</span>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {isSent ? (
                      <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-success text-white text-xs font-bold">
                        <CheckCircle2 className="w-4 h-4" /> Delivered Live
                      </span>
                    ) : (
                      <>
                        <button
                          onClick={() => openReviewModal(msg)}
                          className="px-4 py-2 rounded-full border border-borderLine hover:bg-accentLight text-textPrimary text-xs font-bold transition-colors inline-flex items-center gap-1.5"
                        >
                          <Edit3 className="w-3.5 h-3.5" /> Edit Pitch
                        </button>
                        <button
                          onClick={() => handleSend(msg.id)}
                          disabled={sendingId === msg.id}
                          className="px-5 py-2 rounded-full bg-accent text-card text-xs font-bold shadow-md hover:opacity-90 disabled:opacity-50 inline-flex items-center gap-1.5 transition-all"
                        >
                          {sendingId === msg.id ? (
                            <>
                              <Loader2 className="w-3.5 h-3.5 animate-spin" /> Sending...
                            </>
                          ) : (
                            <>
                              <Send className="w-3.5 h-3.5" /> Approve & Send
                            </>
                          )}
                        </button>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
        {!loading && page < pages && (
          <div className="flex justify-center pt-6">
            <button
              onClick={() => fetchMessages(page + 1, true)}
              className="px-5 py-2.5 rounded-full border border-borderLine text-xs font-bold text-textPrimary"
            >
              Load more messages
            </button>
          </div>
        )}
      </div>

      {/* Review & Edit Modal */}
      {selectedMsg && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-card w-full max-w-2xl rounded-[2.5rem] p-8 shadow-2xl border border-borderLine animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-accentLight text-accent flex items-center justify-center font-bold">
                  <Mail className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-textPrimary">Review & Authorize Outreach</h3>
                  <p className="text-xs text-textSecondary">
                    Recipient: {selectedMsg.recipient_name} ({selectedMsg.recipient_email})
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedMsg(null)}
                className="p-2 rounded-full hover:bg-accentLight text-textSecondary"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-bold text-textPrimary block mb-1.5">Email Subject</label>
                <input 
                  type="text" 
                  value={editSubject}
                  onChange={(e) => setEditSubject(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-full border border-borderLine bg-background text-textPrimary text-xs focus:outline-none focus:border-accent"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-textPrimary block mb-1.5">Email Body</label>
                <textarea 
                  value={editBody}
                  onChange={(e) => setEditBody(e.target.value)}
                  rows={8}
                  className="w-full px-4 py-3 rounded-2xl border border-borderLine bg-background text-textPrimary text-xs focus:outline-none focus:border-accent leading-relaxed resize-none"
                />
              </div>

              <div className="p-3.5 rounded-2xl bg-background border border-borderLine flex items-center gap-3 text-xs text-textSecondary">
                <ShieldCheck className="w-4 h-4 text-success shrink-0" />
                <span>Email will be delivered immediately through the live configured Resend API sandbox.</span>
              </div>

              <div className="pt-4 flex items-center justify-end gap-3">
                <button 
                  onClick={() => setSelectedMsg(null)}
                  className="px-5 py-2.5 rounded-full border border-borderLine text-textSecondary hover:text-textPrimary text-xs font-bold"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => handleSend(selectedMsg.id)}
                  disabled={sendingId === selectedMsg.id}
                  className="px-6 py-2.5 rounded-full bg-accent text-card text-xs font-bold shadow-md hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
                >
                  {sendingId === selectedMsg.id ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" /> Dispatching via Resend...
                    </>
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" /> Approve & Dispatch Now
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
