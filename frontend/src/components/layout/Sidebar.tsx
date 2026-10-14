"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  Briefcase, 
  FileText, 
  Building2, 
  Mail, 
  Calendar, 
  PieChart, 
  Settings,
  Layers,
  LogOut,
} from "lucide-react";
import { clearAccessToken } from "@/lib/api";

const navGroups = [
  {
    title: "WORKSPACE",
    links: [
      { name: "Dashboard", href: "/", icon: LayoutDashboard },
      { name: "Leads", href: "/leads", icon: Briefcase },
      { name: "Companies", href: "/companies", icon: Building2 },
      { name: "Campaigns", href: "/campaigns", icon: FileText },
      { name: "Inbox", href: "/inbox", icon: Mail },
      { name: "Appointments", href: "/appointments", icon: Calendar },
    ],
  },
  {
    title: "INSIGHTS",
    links: [
      { name: "Analytics", href: "/analytics", icon: PieChart },
    ],
  },
  {
    title: "CONFIGURATION",
    links: [
      { name: "Integrations", href: "/integrations", icon: Layers },
      { name: "Settings", href: "/settings", icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  const handleLogout = () => {
    clearAccessToken();
    window.location.assign("/login");
  };

  return (
    <div className="w-64 h-screen bg-sidebar flex flex-col pt-7 pb-6 px-4 border-r border-borderLine select-none">
      {/* Brand / Logo */}
      <div className="flex items-center px-4 mb-6">
        <div className="flex -space-x-1 mr-3">
          <div className="w-4 h-4 bg-accent rounded-sm transform rotate-45 shadow-sm"></div>
          <div className="w-4 h-4 border-2 border-accent rounded-sm transform rotate-45"></div>
        </div>
        <div>
          <span className="font-bold text-textPrimary text-lg tracking-tight block leading-tight">Xobalt AI</span>
          <span className="text-[10px] font-semibold text-textSecondary uppercase tracking-widest block">Autonomous Revenue</span>
        </div>
      </div>
      
      {/* Grouped Navigation */}
      <div className="flex-1 overflow-y-auto space-y-6 pr-1 custom-scrollbar">
        {navGroups.map((group) => (
          <div key={group.title}>
            <div className="text-[10px] font-bold text-textSecondary uppercase tracking-widest px-4 pb-2">
              {group.title}
            </div>
            <nav className="space-y-1">
              {group.links.map((link) => {
                const isActive = pathname === link.href;
                return (
                  <Link
                    key={link.name}
                    href={link.href}
                    className={`flex items-center px-4 py-2.5 rounded-full transition-all duration-150 ${
                      isActive 
                        ? "bg-accent text-card font-semibold shadow-sm" 
                        : "text-textSecondary hover:bg-accentLight hover:text-textPrimary font-medium"
                    }`}
                  >
                    <link.icon className={`mr-3.5 h-4 w-4 shrink-0 ${isActive ? "text-card" : "text-textSecondary"}`} />
                    <span className="text-xs font-semibold">{link.name}</span>
                  </Link>
                );
              })}
            </nav>
          </div>
        ))}
      </div>

      {/* User Profile Pill */}
      <div className="mt-auto pt-4 border-t border-borderLine px-1">
        <div className="flex items-center justify-between p-2 rounded-full border border-borderLine">
          <div className="flex items-center min-w-0">
            <div className="relative shrink-0">
              <div className="w-8 h-8 rounded-full bg-accentLight flex items-center justify-center text-textPrimary font-bold overflow-hidden border border-borderLine">
                <img 
                  src="https://api.dicebear.com/7.x/notionists/svg?seed=Musab" 
                  alt="User" 
                  className="w-full h-full object-cover" 
                />
              </div>
              <div className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-success rounded-full border-2 border-sidebar" />
            </div>
            <div className="ml-3 flex flex-col justify-center min-w-0">
              <span className="text-xs font-bold text-textPrimary leading-none truncate">Musab U.</span>
              <span className="text-[10px] text-textSecondary leading-none truncate mt-0.5">Admin Workspace</span>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              aria-label="Sign out"
              title="Sign out"
              className="ml-2 rounded-full p-2 text-textSecondary transition-colors hover:bg-accentLight hover:text-textPrimary"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
