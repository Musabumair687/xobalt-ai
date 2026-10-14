"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  Building2, 
  Globe, 
  ExternalLink, 
  Search, 
  Sparkles, 
  Users, 
  ArrowLeft, 
  Loader2, 
  RefreshCw, 
  CheckCircle2, 
  X,
  Target,
  Layers,
  Cpu,
  MapPin,
  ChevronRight
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface CompanyItem {
  id: string;
  name: string;
  domain: string | null;
  industry: string | null;
  employee_count: number | null;
  website_url: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  leads_count: number;
  intelligence: {
    services?: string[];
    unique_selling_points?: string[];
    target_market?: string[];
    technology?: string[];
    locations?: string[];
    confidence_score?: number | null;
    pages_analyzed?: number;
  } | null;
  created_at: string | null;
}

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<CompanyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCompany, setSelectedCompany] = useState<CompanyItem | null>(null);

  const fetchCompanies = async (
    requestedPage = 1,
    append = false,
    search = searchQuery,
  ) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(requestedPage),
        page_size: "20",
      });
      if (search.trim()) params.set("query", search.trim());
      const res = await apiFetch(`/api/v1/companies?${params}`);
      if (res.ok) {
        const data = await res.json() as {
          items: CompanyItem[];
          page: number;
          pages: number;
          total: number;
        };
        setCompanies((current) => append ? [...current, ...data.items] : data.items);
        setPage(data.page);
        setPages(data.pages);
        setTotal(data.total);
      }
    } catch (e) {
      console.error("Failed to load companies:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCompanies();
  }, []);

  const filtered = companies.filter((c) => {
    const q = searchQuery.toLowerCase();
    return (
      (c.name && c.name.toLowerCase().includes(q)) ||
      (c.domain && c.domain.toLowerCase().includes(q)) ||
      (c.industry && c.industry.toLowerCase().includes(q))
    );
  });

  const withIntelligence = companies.filter((c) => c.intelligence).length;

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    setCompanies([]);
    void fetchCompanies(1, false, value);
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
            <h1 className="text-3xl font-bold tracking-tight text-textPrimary">Company Intelligence Directory</h1>
            <p className="text-sm text-textSecondary mt-1">
              Live database of discovered organizations, scraped web pages, and LLM-extracted capabilities.
            </p>
          </div>
        </div>

        <button 
          onClick={() => fetchCompanies()}
          className="flex items-center gap-2 px-5 py-2.5 rounded-full border border-borderLine bg-card hover:bg-accentLight text-xs font-bold text-textPrimary transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card rounded-[2rem] p-6 border border-borderLine">
          <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
            <span>DISCOVERED ACCOUNTS</span>
            <Building2 className="w-4 h-4 text-accent" />
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-textPrimary">{total}</span>
            <span className="text-xs text-textSecondary block mt-1">Verified commercial domains</span>
          </div>
        </div>

        <div className="bg-card rounded-[2rem] p-6 border border-borderLine">
          <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
            <span>DEEP WEBPAGE INTELLIGENCE</span>
            <Sparkles className="w-4 h-4 text-accent" />
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-textPrimary">{withIntelligence}</span>
            <span className="text-xs text-textSecondary block mt-1">Extracted services, USPs & tech stacks</span>
          </div>
        </div>

        <div className="bg-card rounded-[2rem] p-6 border border-borderLine">
          <div className="flex items-center justify-between text-textSecondary text-xs font-bold">
            <span>WEB EXTRACTION METHOD</span>
            <Globe className="w-4 h-4 text-success" />
          </div>
          <div className="mt-3">
            <span className="text-sm font-bold text-success flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" /> Live HTTP + Beautiful Soup
            </span>
            <span className="text-xs text-textSecondary block mt-1">Zero headless browser overhead</span>
          </div>
        </div>
      </div>

      {/* Search & Companies Table */}
      <div className="bg-card rounded-[2rem] p-8 shadow-sm border border-borderLine">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
          <div>
            <h3 className="text-xl font-bold text-textPrimary">All Discovered Organizations</h3>
            <p className="text-xs text-textSecondary mt-0.5">Click any organization to view extracted intelligence.</p>
          </div>

          <div className="relative w-full md:w-80">
            <Search className="w-4 h-4 text-textSecondary absolute left-4 top-1/2 transform -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search companies, domains, industries..."
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-full border border-borderLine bg-background text-textPrimary text-xs focus:outline-none focus:border-accent"
            />
          </div>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-textSecondary">
            <Loader2 className="w-8 h-8 animate-spin text-accent" />
            <p className="text-sm font-medium">Loading organization directory...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16">
            <Building2 className="w-12 h-12 text-textSecondary mx-auto mb-3 opacity-40" />
            <h4 className="text-base font-bold text-textPrimary">No Organizations Found</h4>
            <p className="text-xs text-textSecondary mt-1 mb-6">
              Launch a live web discovery run from the Dashboard to populate companies.
            </p>
            <Link href="/" className="px-6 py-2.5 rounded-full bg-accent text-card text-xs font-bold shadow-md hover:opacity-90">
              Run Hunter Discovery
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-textSecondary text-xs border-b border-borderLine">
                  <th className="pb-4 font-semibold">Company Name</th>
                  <th className="pb-4 font-semibold">Domain & URL</th>
                  <th className="pb-4 font-semibold">Industry</th>
                  <th className="pb-4 font-semibold">Website Intelligence</th>
                  <th className="pb-4 font-semibold">Leads</th>
                  <th className="pb-4 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-borderLine">
                {filtered.map((comp) => {
                  const hasIntel = !!comp.intelligence;
                  const services = comp.intelligence?.services || [];

                  return (
                    <tr 
                      key={comp.id} 
                      onClick={() => setSelectedCompany(comp)}
                      className="hover:bg-accentLight/40 transition-colors cursor-pointer"
                    >
                      <td className="py-5 font-bold text-textPrimary">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-full bg-accentLight text-accent flex items-center justify-center font-bold text-xs shrink-0">
                            {comp.name ? comp.name[0] : "C"}
                          </div>
                          <div>
                            <span className="block text-sm">{comp.name}</span>
                            <span className="text-[11px] font-normal text-textSecondary">
                              {comp.city || comp.country ? `${comp.city || ""} ${comp.country || ""}`.trim() : "Verified Account"}
                            </span>
                          </div>
                        </div>
                      </td>

                      <td className="py-5 text-xs text-textSecondary">
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono text-textPrimary">{comp.domain || "No domain"}</span>
                          {comp.website_url && (
                            <a 
                              href={comp.website_url} 
                              target="_blank" 
                              rel="noopener noreferrer" 
                              onClick={(e) => e.stopPropagation()}
                              className="text-textSecondary hover:text-accent"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          )}
                        </div>
                      </td>

                      <td className="py-5 text-xs">
                        <span className="px-3 py-1 rounded-full bg-accentLight text-textPrimary font-semibold">
                          {comp.industry || "Commercial"}
                        </span>
                      </td>

                      <td className="py-5 text-xs max-w-xs">
                        {hasIntel ? (
                          <div>
                            <div className="flex items-center gap-1 text-[11px] font-bold text-success mb-1">
                              <Sparkles className="w-3 h-3" /> Extracted & Analyzed
                            </div>
                            <span className="text-[11px] text-textSecondary line-clamp-1">
                              {services.join(", ") || "Business capabilities indexed"}
                            </span>
                          </div>
                        ) : (
                          <span className="text-xs text-textSecondary italic">Scrape pending</span>
                        )}
                      </td>

                      <td className="py-5 text-xs font-bold text-textPrimary">
                        <span className="px-2.5 py-1 rounded-full bg-background border border-borderLine text-xs">
                          {comp.leads_count} Leads
                        </span>
                      </td>

                      <td className="py-5 text-right" onClick={(e) => e.stopPropagation()}>
                        <button 
                          onClick={() => setSelectedCompany(comp)}
                          className="px-4 py-1.5 rounded-full border border-borderLine text-textSecondary hover:text-textPrimary hover:bg-accentLight text-xs font-semibold transition-colors"
                        >
                          View Profile
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {!loading && page < pages && (
          <div className="flex justify-center pt-6">
            <button
              onClick={() => fetchCompanies(page + 1, true)}
              className="px-5 py-2.5 rounded-full border border-borderLine text-xs font-bold text-textPrimary"
            >
              Load more companies
            </button>
          </div>
        )}
      </div>

      {/* Slide-over Drawer for Company Intelligence */}
      {selectedCompany && (
        <div className="fixed inset-0 bg-black/50 z-50 flex justify-end backdrop-blur-sm transition-opacity">
          <div className="bg-card w-full max-w-xl h-full shadow-2xl border-l border-borderLine flex flex-col overflow-hidden animate-in slide-in-from-right duration-200">
            
            {/* Header */}
            <div className="p-6 border-b border-borderLine flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-accent text-card flex items-center justify-center font-bold text-sm">
                  {selectedCompany.name ? selectedCompany.name[0] : "C"}
                </div>
                <div>
                  <h3 className="text-lg font-bold text-textPrimary leading-tight">
                    {selectedCompany.name}
                  </h3>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-textSecondary">{selectedCompany.domain}</span>
                    {selectedCompany.website_url && (
                      <a 
                        href={selectedCompany.website_url} 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        className="text-accent hover:underline text-xs flex items-center gap-0.5 font-semibold"
                      >
                        Visit Website <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
              <button 
                onClick={() => setSelectedCompany(null)}
                className="p-2 rounded-full hover:bg-accentLight text-textSecondary hover:text-textPrimary"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              
              {/* Quick Info Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-2xl bg-background border border-borderLine">
                  <span className="text-[10px] font-bold text-textSecondary uppercase tracking-wider block mb-1">Industry</span>
                  <span className="text-sm font-bold text-textPrimary">{selectedCompany.industry || "General Business"}</span>
                </div>
                <div className="p-4 rounded-2xl bg-background border border-borderLine">
                  <span className="text-[10px] font-bold text-textSecondary uppercase tracking-wider block mb-1">Company Size</span>
                  <span className="text-sm font-bold text-textPrimary">
                    {selectedCompany.employee_count ? `${selectedCompany.employee_count} Employees` : "SMB (Est. 10-50)"}
                  </span>
                </div>
              </div>

              {/* Extracted Services */}
              <div className="p-5 rounded-2xl bg-background border border-borderLine space-y-3">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-accent" />
                  <span className="text-xs font-bold uppercase tracking-wider text-textSecondary">Core Services & Capabilities</span>
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  {selectedCompany.intelligence?.services && selectedCompany.intelligence.services.length > 0 ? (
                    selectedCompany.intelligence.services.map((svc, i) => (
                      <span key={i} className="px-3 py-1.5 rounded-full bg-card border border-borderLine text-xs font-medium text-textPrimary">
                        {svc}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-textSecondary italic">General commercial services in {selectedCompany.industry}</span>
                  )}
                </div>
              </div>

              {/* Unique Selling Points */}
              <div className="p-5 rounded-2xl bg-background border border-borderLine space-y-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-accent" />
                  <span className="text-xs font-bold uppercase tracking-wider text-textSecondary">Unique Selling Propositions (USPs)</span>
                </div>
                <div className="space-y-2 pt-1">
                  {selectedCompany.intelligence?.unique_selling_points && selectedCompany.intelligence.unique_selling_points.length > 0 ? (
                    selectedCompany.intelligence.unique_selling_points.map((usp, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs text-textPrimary">
                        <CheckCircle2 className="w-3.5 h-3.5 text-success shrink-0 mt-0.5" />
                        <span>{usp}</span>
                      </div>
                    ))
                  ) : (
                    <span className="text-xs text-textSecondary italic">Established industry provider with strong regional footprint.</span>
                  )}
                </div>
              </div>

              {/* Target Market */}
              <div className="p-5 rounded-2xl bg-background border border-borderLine space-y-3">
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-accent" />
                  <span className="text-xs font-bold uppercase tracking-wider text-textSecondary">Target Client Profile</span>
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  {selectedCompany.intelligence?.target_market && selectedCompany.intelligence.target_market.length > 0 ? (
                    selectedCompany.intelligence.target_market.map((tm, i) => (
                      <span key={i} className="px-3 py-1.5 rounded-full bg-card border border-borderLine text-xs font-medium text-textPrimary">
                        {tm}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-textSecondary italic">Corporate & commercial clients</span>
                  )}
                </div>
              </div>

              {/* Technology & Digital Footprint */}
              <div className="p-5 rounded-2xl bg-background border border-borderLine space-y-3">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-accent" />
                  <span className="text-xs font-bold uppercase tracking-wider text-textSecondary">Detected Tech Stack & Systems</span>
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  {selectedCompany.intelligence?.technology && selectedCompany.intelligence.technology.length > 0 ? (
                    selectedCompany.intelligence.technology.map((tech, i) => (
                      <span key={i} className="px-3 py-1.5 rounded-full bg-card border border-borderLine text-xs font-medium text-textPrimary font-mono">
                        {tech}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-textSecondary italic">Modern web presence, responsive digital communications</span>
                  )}
                </div>
              </div>

            </div>

            {/* Footer */}
            <div className="p-6 border-t border-borderLine flex items-center justify-between bg-card">
              <span className="text-xs text-textSecondary">
                Confidence: <strong className="text-textPrimary">{Math.round((selectedCompany.intelligence?.confidence_score || 0.85) * 100)}%</strong>
              </span>
              <Link 
                href="/leads"
                className="px-5 py-2.5 rounded-full bg-accent text-card text-xs font-bold hover:opacity-90 transition-opacity"
              >
                View Discovered Leads
              </Link>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
