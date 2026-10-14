"use client";

import { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

export function AppFrame({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  if (pathname === "/login") {
    return (
      <div className="h-screen overflow-y-auto bg-background">
        {children}
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-sidebar">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-l-[2.5rem] bg-background shadow-[-10px_0_30px_-15px_rgba(0,0,0,0.1)]">
        <TopBar />
        <main className="flex-1 overflow-y-auto px-8 pb-8">
          {children}
        </main>
      </div>
    </div>
  );
}
