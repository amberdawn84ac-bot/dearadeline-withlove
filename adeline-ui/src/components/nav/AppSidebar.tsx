"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import React, { useState } from "react";
import { BookOpen, Settings, Menu, X, Trophy, Hammer, Archive, Sparkles } from "lucide-react";
import { DailyBreadWidget } from "@/components/daily-bread/DailyBreadWidget";

const NAV_ITEMS = [
  { label: "Today", href: "/dashboard", icon: Sparkles },
  { label: "Reading Nook", href: "/dashboard/reading-nook", icon: BookOpen },
  { label: "Resource Vault", href: "/dashboard/resource-vault", icon: Archive },
  { label: "Projects", href: "/dashboard/projects", icon: Hammer },
  { label: "My Portfolio", href: "/dashboard/portfolio", icon: Trophy },
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
      <div className="md:hidden flex items-center justify-between px-4 py-3 border-b border-[#E7DAC3] bg-[#FFFEF7]/95 backdrop-blur-xl sticky top-0 z-50">
        <Link href="/dashboard" className="flex items-center gap-3">
          <Image src="/adeline-nav.png" alt="Adeline" width={38} height={38} className="rounded-xl shadow-sm -rotate-2" />
          <span className="font-bold text-xl text-[#2F4731]" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>
            Dear Adeline
          </span>
        </Link>
        <button onClick={() => setIsOpen(!isOpen)} className="p-2 rounded-xl text-[#2F4731] hover:bg-[#2F4731]/5" aria-label="Toggle menu">
          {isOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      <aside className={[
        "fixed inset-y-0 left-0 z-40 w-64 bg-[#FFFDF5] border-r border-[#E7DAC3]",
        "transform transition-transform duration-200 ease-in-out",
        "md:translate-x-0 md:static md:h-screen sticky top-0 overflow-y-auto",
        isOpen ? "translate-x-0" : "-translate-x-full",
      ].join(" ")}>
        <div className="flex flex-col h-full p-5">
          <Link href="/dashboard" className="hidden md:flex items-center gap-3 mb-8 px-2 py-2 group">
            <Image src="/adeline-nav.png" alt="Adeline" width={50} height={50} className="rounded-2xl shadow-md -rotate-2 group-hover:rotate-0 transition-transform" />
            <div className="flex flex-col">
              <span className="font-bold text-[22px] text-[#2F4731] leading-none" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>
                Dear Adeline
              </span>
              <span className="text-[9px] font-black uppercase tracking-[0.22em] text-[#BD6809] mt-1.5">
                Learn · Make · Wonder
              </span>
            </div>
          </Link>

          <div className="px-3 mb-2 text-[9px] font-black uppercase tracking-[0.22em] text-[#2F4731]/35">Explore</div>
          <nav className="space-y-1">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(`${item.href}/`));
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setIsOpen(false)}
                  className={[
                    "flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-200 group",
                    isActive
                      ? "bg-[#2F4731] text-white shadow-md font-bold"
                      : "text-[#2F4731]/70 hover:bg-white hover:shadow-sm hover:text-[#2F4731] font-medium",
                  ].join(" ")}
                >
                  <Icon size={19} className={["transition-transform group-hover:scale-110", isActive ? "text-[#EAB76B]" : "text-[#BD6809]"].join(" ")} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="mt-6 mb-6">
            <div className="px-3 mb-2 text-[9px] font-black uppercase tracking-[0.22em] text-[#2F4731]/35">Daily rhythm</div>
            <DailyBreadWidget onStudy={handleDailyBreadStudy} />
          </div>

          <div className="mt-auto pt-5 border-t border-[#E7DAC3]">
            <Link
              href="/dashboard/settings"
              className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-[#2F4731]/55 hover:text-[#2F4731] hover:bg-white transition-colors"
            >
              <Settings size={17} className="text-[#BD6809]" /> Settings
            </Link>
            <p className="px-4 pt-4 text-[9px] leading-relaxed uppercase tracking-[0.18em] text-[#2F4731]/25 font-bold">
              Education as unique as your child
            </p>
          </div>
        </div>
      </aside>

      {isOpen && <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-30 md:hidden" onClick={() => setIsOpen(false)} />}
      <main className="flex-1 min-w-0 overflow-y-auto h-screen scroll-smooth">{children}</main>
    </div>
  );
}