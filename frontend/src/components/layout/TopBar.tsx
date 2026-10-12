"use client";

import React from "react";
import { Search, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

export function TopBar() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => setMounted(true), []);

  return (
    <header className="h-20 bg-transparent flex items-center justify-end px-8 z-10 w-full shrink-0">
      <div className="flex items-center space-x-4">
        {mounted && (
          <button 
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="p-3 text-textSecondary bg-card hover:text-textPrimary rounded-full shadow-sm transition-all"
            title="Toggle theme"
          >
            {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>
        )}
      </div>
    </header>
  );
}
