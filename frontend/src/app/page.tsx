"use client";

import React from "react";
import { Users, Building, MousePointerClick, Calendar, ArrowUpRight, MoreHorizontal } from "lucide-react";

export default function Dashboard() {
  const stats = [
    { label: "Total Leads", value: "124K", sub: "For 1 week period", icon: Users },
    { label: "Companies", value: "3.2K", sub: "Found today", icon: Building },
    { label: "Replies", value: "850", sub: "Active conversations", icon: MousePointerClick },
    { label: "Meetings", value: "28", sub: "Booked this week", icon: Calendar },
  ];

  const aiActivity = [
    { title: "Apple", sub: "Meeting booked for tomorrow", time: "10:30 AM", status: "Success" },
    { title: "Figma", sub: "Message awaiting approval", time: "09:15 AM", status: "Pending" },
    { title: "Tesla", sub: "High intent detected", time: "08:45 AM", status: "Action" },
  ];

  const campaigns = [
    { title: "US Real Estate Outreach", company: "Multiple", location: "Florida", status: "Active", date: "Oct 10 03:20 PM" },
    { title: "Enterprise SaaS Follow-up", company: "Multiple", location: "California", status: "Pending", date: "Oct 09 11:30 AM" },
    { title: "Founders Q4 Promo", company: "Multiple", location: "New York", status: "Completed", date: "Oct 05 09:15 AM" },
  ];

  return (
    <div className="max-w-7xl mx-auto flex flex-col gap-8 pb-10">
      
      {/* Top Section */}
      <div className="flex items-end gap-8">
        <div className="w-1/4">
          <h1 className="text-3xl font-bold tracking-tight text-textPrimary mb-2">Quick Stats</h1>
          <p className="text-sm text-textSecondary leading-relaxed">
            Your pipeline statistics for a 1 week period.
          </p>
        </div>
        
        <div className="flex-1 flex gap-4">
          {stats.map((stat, idx) => (
            <div key={idx} className="flex-1 bg-card rounded-[2rem] p-6 flex flex-col items-center justify-center text-center shadow-sm border border-borderLine hover:shadow-md transition-all">
              <div className="w-12 h-12 bg-accentLight rounded-full flex items-center justify-center mb-4">
                <stat.icon className="w-5 h-5 text-accent" />
              </div>
              <h2 className="text-2xl font-bold text-textPrimary">{stat.value}</h2>
              <p className="text-xs font-semibold text-textSecondary mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Middle Section */}
      <div className="flex gap-8">
        
        {/* Pipeline Chart Placeholder */}
        <div className="flex-[2] bg-card rounded-[2rem] p-8 shadow-sm border border-borderLine">
          <div className="flex justify-between items-center mb-8">
            <h3 className="text-xl font-bold text-textPrimary">Pipeline Conversion</h3>
            <div className="flex items-center gap-4 text-xs font-semibold text-textSecondary">
              <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-accent"></div>Leads</div>
              <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-borderLine"></div>Qualified</div>
            </div>
          </div>
          
          <div className="h-48 flex items-end justify-between px-2">
            {/* Dummy Bar Chart */}
            {[40, 70, 45, 90, 65, 80, 50, 75, 40, 85].map((h, i) => (
              <div key={i} className="flex flex-col items-center gap-3">
                <div className="w-3 bg-borderLine rounded-t-full relative" style={{ height: '140px' }}>
                  <div className="absolute bottom-0 w-full bg-accent rounded-full transition-all duration-500" style={{ height: `${h}%` }}></div>
                </div>
                <span className="text-[10px] text-textSecondary font-bold">{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct'][i]}</span>
              </div>
            ))}
          </div>
        </div>

        {/* AI Activity */}
        <div className="flex-1 bg-card rounded-[2rem] p-8 shadow-sm border border-borderLine">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-bold text-textPrimary">AI Activity</h3>
            <button className="text-textSecondary hover:text-accent"><MoreHorizontal className="w-5 h-5"/></button>
          </div>
          <div className="space-y-6">
            {aiActivity.map((act, i) => (
              <div key={i} className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-accentLight rounded-full flex items-center justify-center text-accent font-bold text-sm">
                    {act.title[0]}
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-textPrimary">{act.title}</h4>
                    <p className="text-[10px] text-textSecondary">{act.time} GMT</p>
                  </div>
                </div>
                <span className="text-[10px] font-bold px-3 py-1.5 bg-accentLight text-textSecondary rounded-full">
                  {act.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Section */}
      <div className="bg-card rounded-[2rem] p-8 shadow-sm border border-borderLine">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-xl font-bold text-textPrimary">Active Campaigns</h3>
          <button className="bg-accent text-card px-5 py-2 rounded-full text-xs font-bold hover:opacity-90 transition-opacity">
            Export ⬇
          </button>
        </div>
        
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="text-textSecondary text-xs">
              <th className="pb-4 font-semibold">Campaign Name</th>
              <th className="pb-4 font-semibold">Target Company</th>
              <th className="pb-4 font-semibold">Location</th>
              <th className="pb-4 font-semibold">Status</th>
              <th className="pb-4 font-semibold">Last Active</th>
              <th className="pb-4"></th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((camp, i) => (
              <tr key={i} className="border-t border-borderLine">
                <td className="py-4 font-bold text-textPrimary flex items-center gap-3">
                  <div className="w-4 h-4 border rounded bg-background"></div>
                  {camp.title}
                </td>
                <td className="py-4 font-medium text-textPrimary">{camp.company}</td>
                <td className="py-4 text-textSecondary">{camp.location}</td>
                <td className="py-4">
                  <span className={`text-[10px] font-bold px-3 py-1 rounded-full ${
                    camp.status === 'Active' ? 'bg-success/10 text-success' : 
                    camp.status === 'Completed' ? 'bg-textSecondary/10 text-textSecondary' : 'bg-accentLight text-accent'
                  }`}>
                    {camp.status}
                  </span>
                </td>
                <td className="py-4 font-semibold text-textPrimary text-xs">{camp.date}</td>
                <td className="py-4 text-right">
                  <button className="text-textSecondary hover:text-accent"><MoreHorizontal className="w-4 h-4"/></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  );
}
