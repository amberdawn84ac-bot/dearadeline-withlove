"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import React, { useState } from "react";
import { BookOpen, Briefcase, Settings, Menu, X, Trophy, Hammer } from "lucide-react";
import { DailyBreadWidget } from "@/components/daily-bread/DailyBreadWidget";

const NAV_ITEMS = [
  { label: "My Learning Plan", href: "/dashboard", icon: BookOpen },
  { label: "Reading Nook",     href: "/dashboard/reading-nook", icon: BookOpen },
  { label: "Projects",         href: "/dashboard/projects", icon: Hammer },
  { label: "My Portfolio",     href: "/dashboard/portfolio", icon: Trophy },
];

export function AppSidebar({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);

  const handleDailyBreadStudy = (prompt: string) => {
    router.push(`/dashboard?study=${encodeURIComponent(prompt)}`);
  };

  return (
    <div className="min-h-screen bg-[#FFFEF7] flex flex-col md:flex-row">
      {/* Mobile header */}
      <div className="md:hidden flex items-center justify-between p-4 border-b border-[#E7DAC3] bg-white/50 backdrop-blur-sm sticky top-0 z-50">
        <Link href="/dashboard" className="flex items-center gap-3">
          <span
            className="font-bold text-[#2F4731]"
            style={{ fontFamily: "var(--font-emilys-candy), cursive" }}
          >
            Dear Adeline
          </span>
        </Link>
        <button onClick={() => setIsOpen(!isOpen)} className="p-2 text-[#2F4731]">
          {isOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Sidebar */}
      <aside
        className={[
          "fixed inset-y-0 left-0 z-40 w-64 bg-[#FFFDF5] border-r border-[#E7DAC3]",
          "transform transition-transform duration-200 ease-in-out",
          "md:translate-x-0 md:static md:h-screen sticky top-0 overflow-y-auto",
          isOpen ? "translate-x-0" : "-translate-x-full",
        ].join(" ")}
      >
        <div className="flex flex-col h-full p-6">
          {/* Logo */}
          <div className="hidden md:flex items-center gap-3 mb-10 px-2">
            <div className="w-12 h-12 rounded-xl bg-[#2F4731] flex items-center justify-center shadow-md border-2 border-white">
              <span className="text-2xl">🌿</span>
            </div>
            <div className="flex flex-col">
              <span
                className="font-bold text-xl text-[#2F4731] leading-none"
                style={{ fontFamily: "var(--font-emilys-candy), cursive" }}
              >
                Dear Adeline
              </span>
              <span className="text-[10px] font-black uppercase tracking-widest text-[#BD6809] mt-1">
                Learning Hub
              </span>
            </div>
          </div>

          {/* Nav */}
          <nav className="space-y-1">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setIsOpen(false)}
                  className={[
                    "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group",
                    isActive
                      ? "bg-[#2F4731] text-white shadow-lg font-bold"
                      : "text-[#2F4731]/70 hover:bg-[#2F4731]/5 hover:text-[#2F4731] font-medium",
                  ].join(" ")}
                >
                  <Icon
                    size={20}
                    className={[
                      "transition-transform group-hover:scale-110",
                      isActive ? "text-[#BD6809]" : "",
                    ].join(" ")}
                  />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Daily Bread */}
          <div className="mt-6 mb-6">
            <DailyBreadWidget onStudy={handleDailyBreadStudy} />
          </div>

          {/* Bottom */}
          <div className="mt-auto pt-6 border-t border-[#E7DAC3]">
            <Link
              href="/dashboard/settings"
              className="flex items-center gap-3 px-4 py-2 text-sm font-medium text-[#2F4731]/60 hover:text-[#2F4731] transition-colors"
            >
              <Settings size={16} />
              Settings
            </Link>
          </div>
        </div>
      </aside>

      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-30 md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Main content */}
      <main className="flex-1 min-w-0 overflow-y-auto h-screen scroll-smooth">
        {children}
      </main>
    </div>
  );
}
