"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  Briefcase, 
  FileText, 
  Building2, 
  Users, 
  Grid, 
  PieChart, 
  Settings 
} from "lucide-react";

const mainLinks = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Leads", href: "/leads", icon: Briefcase },
  { name: "Campaigns", href: "/campaigns", icon: FileText },
  { name: "Companies", href: "/companies", icon: Building2 },
  { name: "Inbox", href: "/inbox", icon: Users },
  { name: "Appointments", href: "/appointments", icon: Grid },
  { name: "Analytics", href: "/analytics", icon: PieChart },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="w-64 h-screen bg-sidebar flex flex-col pt-8 pb-6 px-4">
      {/* Logo */}
      <div className="flex items-center px-4 mb-10">
        <div className="flex -space-x-1 mr-3">
          <div className="w-4 h-4 bg-accent rounded-sm transform rotate-45"></div>
          <div className="w-4 h-4 border-2 border-accent rounded-sm transform rotate-45"></div>
        </div>
        <span className="font-bold text-textPrimary text-xl tracking-tight">Xobalt AI</span>
      </div>
      
      {/* Navigation */}
      <div className="flex-1 overflow-y-auto">
        <nav className="space-y-2">
          {mainLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.name}
                href={link.href}
                className={`flex items-center px-5 py-3 rounded-full transition-all duration-200 ${
                  isActive 
                    ? "bg-accent text-card font-semibold shadow-md" 
                    : "text-textSecondary hover:bg-accentLight hover:text-textPrimary font-medium"
                }`}
              >
                <link.icon className={`mr-4 h-5 w-5 ${isActive ? "text-card" : "text-textSecondary"}`} />
                <span className="text-sm">{link.name}</span>
              </Link>
            )
          })}
        </nav>
      </div>

      {/* User Profile Pill */}
      <div className="mt-auto px-2">
        <div className="flex items-center justify-between p-2 rounded-full border border-borderLine hover:bg-accentLight cursor-pointer transition-colors">
          <div className="flex items-center">
            <div className="relative">
              <div className="w-10 h-10 rounded-full bg-accentLight flex items-center justify-center text-textPrimary font-bold overflow-hidden">
                <img src="https://api.dicebear.com/7.x/notionists/svg?seed=Musab" alt="User" className="w-full h-full object-cover" />
              </div>
              <div className="absolute -top-1 -right-1 w-4 h-4 bg-accent text-card text-[10px] flex items-center justify-center rounded-full font-bold border-2 border-sidebar">
                12
              </div>
            </div>
            <div className="ml-3 flex flex-col justify-center">
              <span className="text-sm font-semibold text-textPrimary leading-none mb-1">Musab U.</span>
              <span className="text-xs text-textSecondary leading-none">admin@xobalt.ai</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
