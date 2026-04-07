"use client";

import { useRouter } from "next/navigation";
import { Lock, Users, TrendingUp, FileText, GraduationCap } from "lucide-react";

const FEATURES = [
  { icon: Users, label: "Up to 5 student profiles" },
  { icon: TrendingUp, label: "10-Track mastery overview per student" },
  { icon: FileText, label: "PDF transcripts & portfolio builder" },
  { icon: GraduationCap, label: "Standards progress & credit tracking" },
];

export default function TeacherDashboard() {
  const router = useRouter();

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-[#FFFEF7] to-[#F5F0E8] px-6">
      <div className="max-w-md w-full text-center space-y-6">
        {/* Lock icon */}
        <div className="mx-auto w-16 h-16 rounded-full bg-[#2F4731]/10 flex items-center justify-center">
          <Lock className="w-8 h-8 text-[#2F4731]" />
        </div>

        {/* Heading */}
        <div>
          <h1
            className="text-3xl font-bold text-[#2F4731]"
            style={{ fontFamily: "var(--font-emilys-candy), cursive" }}
          >
            Parent Dashboard
          </h1>
          <p className="text-sm text-[#2F4731]/60 mt-2">
            Monitor your children&apos;s mastery across all 10 curriculum tracks,
            generate transcripts, and track credit hours.
          </p>
        </div>

        {/* Feature list */}
        <div className="bg-white border border-[#E7DAC3] rounded-2xl p-6 text-left space-y-4">
          {FEATURES.map(({ icon: Icon, label }) => (
            <div key={label} className="flex items-center gap-3">
              <Icon className="w-5 h-5 text-[#BD6809] shrink-0" />
              <p className="text-sm text-[#2F4731]">{label}</p>
            </div>
          ))}
        </div>

        {/* Pricing callout */}
        <div className="bg-white border-2 border-[#BD6809] rounded-2xl p-5">
          <p className="text-xs font-bold uppercase tracking-widest text-[#BD6809] mb-1">
            Family Plan
          </p>
          <p className="text-3xl font-bold text-[#2F4731]">
            $29.99<span className="text-sm font-normal text-[#2F4731]/60">/month</span>
          </p>
          <p className="text-xs text-[#2F4731]/60 mt-1">
            or $323.89/year (save 10%)
          </p>
        </div>

        {/* CTA */}
        <button
          onClick={() => router.push("/pricing")}
          className="w-full py-3 px-6 rounded-xl bg-[#BD6809] text-white font-bold text-sm hover:bg-[#A55A07] transition-colors"
        >
          Upgrade to Family Plan
        </button>

        <button
          onClick={() => router.push("/dashboard")}
          className="text-sm text-[#2F4731]/50 hover:text-[#2F4731] transition-colors"
        >
          Back to my dashboard
        </button>
      </div>
    </div>
  );
}
