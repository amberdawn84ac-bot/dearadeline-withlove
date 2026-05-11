"use client";

/**
 * CognitiveDashboard — Real-Time Parent Monitoring Panel
 *
 * Connects to /ws/monitor/{studentId} and displays live:
 *   - Cognitive Twin state (load, engagement, frustration)
 *   - ZPD zone with intervention recommendation
 *   - Session block count
 *   - Safety flag log
 *   - Live event stream
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Activity, AlertTriangle, Brain, Zap, Shield, ChevronDown, ChevronUp, Wifi, WifiOff, type LucideIcon } from "lucide-react";
import {
  useStudentMonitor,
  type CognitiveTwinSnapshot,
  type SafetyFlagEvent,
  type MonitorEvent,
} from "@/hooks/useStudentMonitor";

export interface EventPayload {
  block_type?: string;
  working_memory_load?: number;
  zpd_zone?: string;
  message?: string;
  zone?: string;
}

interface CognitiveDashboardProps {
  studentId: string;
  studentName?: string;
}

const ZPD_CONFIG = {
  FRUSTRATED: { label: "Needs Help", color: "#DC2626", bg: "#FEE2E2", icon: "🧩" },
  IN_ZPD:     { label: "In the Zone", color: "#059669", bg: "#D1FAE5", icon: "✅" },
  BORED:      { label: "Ready for More", color: "#7C3AED", bg: "#EDE9FE", icon: "🚀" },
};

const INTERVENTION_CONFIG = {
  SCAFFOLD: { label: "Scaffolding Suggested", color: "#DC2626", bg: "#FEF2F2" },
  BREAK:    { label: "Break Recommended",     color: "#D97706", bg: "#FFFBEB" },
  ELEVATE:  { label: "Elevate Content",       color: "#7C3AED", bg: "#F5F3FF" },
  CONTINUE: { label: "Continuing",            color: "#059669", bg: "#F0FDF4" },
};

function GaugeMeter({
  value,
  label,
  color,
  icon: Icon,
}: {
  value: number;
  label: string;
  color: string;
  icon: LucideIcon;
}) {
  const pct = Math.round(value * 100);
  const strokeDashoffset = 157 - (157 * value);

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative w-16 h-16">
        <svg className="w-16 h-16 -rotate-90" viewBox="0 0 60 60">
          <circle cx="30" cy="30" r="25" fill="none" stroke="#E5E7EB" strokeWidth="6" />
          <motion.circle
            cx="30" cy="30" r="25"
            fill="none"
            stroke={color}
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray="157"
            animate={{ strokeDashoffset }}
            transition={{ duration: 0.6 }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs font-bold" style={{ color }}>{pct}%</span>
        </div>
      </div>
      <div className="flex items-center gap-1">
        <Icon size={11} style={{ color }} />
        <span className="text-[10px] text-[#6B7280] font-medium">{label}</span>
      </div>
    </div>
  );
}

function ConnectionBadge({ status }: { status: string }) {
  const isConnected = status === "connected";
  return (
    <div
      className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold"
      style={{
        background: isConnected ? "#D1FAE5" : "#FEE2E2",
        color: isConnected ? "#065F46" : "#991B1B",
      }}
    >
      {isConnected ? <Wifi size={10} /> : <WifiOff size={10} />}
      {isConnected ? "Live" : status === "connecting" ? "Connecting…" : "Offline"}
    </div>
  );
}

function SafetyFlagRow({ flag }: { flag: SafetyFlagEvent }) {
  const [open, setOpen] = useState(false);
  const isBlock = flag.severity !== "warning" && flag.flags.some(
    (f) => ["VIOLENCE", "FEAR_CONTENT", "PII_DETECTED"].includes(f)
  );

  return (
    <div
      className="rounded-xl text-xs overflow-hidden"
      style={{
        border: `1px solid ${isBlock ? "#FCA5A5" : "#FCD34D"}`,
        background: isBlock ? "#FFF1F2" : "#FFFBEB",
      }}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2"
      >
        <div className="flex items-center gap-2">
          <AlertTriangle size={12} style={{ color: isBlock ? "#DC2626" : "#D97706" }} />
          <span className="font-semibold" style={{ color: isBlock ? "#991B1B" : "#92400E" }}>
            {isBlock ? "Content Blocked" : "Safety Warning"} — {flag.block_type}
          </span>
        </div>
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-2 space-y-1">
              {flag.flags.map((f, i) => (
                <span
                  key={i}
                  className="inline-block mr-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold"
                  style={{ background: "#E5E7EB", color: "#374151" }}
                >
                  {f}
                </span>
              ))}
              {flag.warnings.map((w, i) => (
                <p key={i} className="text-[#6B7280]">{w}</p>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function EventTicker({ events }: { events: MonitorEvent[] }) {
  const visible = events
    .filter((e) => !["keepalive", "pong"].includes(e.event))
    .slice(-8)
    .reverse();

  return (
    <div className="space-y-1 max-h-40 overflow-y-auto">
      {visible.length === 0 && (
        <p className="text-xs text-[#9CA3AF] italic">Waiting for student activity…</p>
      )}
      {visible.map((e, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -6 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-2 text-[11px] text-[#6B7280]"
        >
          <span
            className="shrink-0 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase"
            style={{
              background:
                e.event === "safety_flag"
                  ? "#FEE2E2"
                  : e.event === "zpd_shift"
                    ? "#EDE9FE"
                    : "#F3F4F6",
              color:
                e.event === "safety_flag"
                  ? "#991B1B"
                  : e.event === "zpd_shift"
                    ? "#5B21B6"
                    : "#6B7280",
            }}
          >
            {e.event.replace("_", " ")}
          </span>
          <span className="truncate">
            {e.event === "block_generated" && `Block: ${(e.payload as EventPayload)?.block_type}`}
            {e.event === "cognitive_update" && `Load: ${Math.round(((e.payload as EventPayload)?.working_memory_load ?? 0) * 100)}% · Zone: ${(e.payload as EventPayload)?.zpd_zone}`}
            {e.event === "agent_thinking" && (e.payload as EventPayload)?.message}
            {e.event === "zpd_shift" && `→ ${(e.payload as EventPayload)?.zone}`}
            {e.event === "session_start" && "Session started"}
            {e.event === "session_end" && "Session ended"}
          </span>
        </motion.div>
      ))}
    </div>
  );
}

export function CognitiveDashboard({ studentId, studentName }: CognitiveDashboardProps) {
  const { status, twin, events, safetyFlags } = useStudentMonitor({ studentId });
  const [showFlags, setShowFlags] = useState(true);
  const [showEvents, setShowEvents] = useState(false);

  const zpd = twin ? ZPD_CONFIG[twin.zpd_zone] ?? ZPD_CONFIG.IN_ZPD : null;
  const intervention = twin ? INTERVENTION_CONFIG[twin.intervention] ?? INTERVENTION_CONFIG.CONTINUE : null;

  return (
    <div
      className="rounded-2xl overflow-hidden text-[#374151]"
      style={{ border: "2px solid #2F473120", background: "#FAFAF7" }}
    >
      {/* Header */}
      <div
        className="px-5 py-3 flex items-center justify-between"
        style={{ background: "#fff", borderBottom: "1px solid #E5E7EB" }}
      >
        <div className="flex items-center gap-2">
          <Brain size={16} style={{ color: "#2F4731" }} />
          <span className="text-sm font-bold text-[#2F4731]">
            {studentName ? `${studentName}'s` : "Student"} Cognitive Monitor
          </span>
        </div>
        <ConnectionBadge status={status} />
      </div>

      <div className="p-5 space-y-5">
        {/* Twin gauges */}
        {twin ? (
          <>
            <div className="flex items-center justify-around">
              <GaugeMeter
                value={twin.working_memory_load}
                label="Memory Load"
                color="#F59E0B"
                icon={Zap}
              />
              <GaugeMeter
                value={twin.engagement_level}
                label="Engagement"
                color="#10B981"
                icon={Activity}
              />
              <GaugeMeter
                value={twin.frustration_score}
                label="Frustration"
                color="#EF4444"
                icon={AlertTriangle}
              />
            </div>

            {/* ZPD zone + intervention */}
            <div className="grid grid-cols-2 gap-3">
              <div
                className="rounded-xl px-3 py-2.5 text-center"
                style={{ background: zpd?.bg }}
              >
                <p className="text-lg">{zpd?.icon}</p>
                <p className="text-[10px] font-bold uppercase tracking-wide" style={{ color: zpd?.color }}>
                  ZPD Zone
                </p>
                <p className="text-xs font-semibold mt-0.5" style={{ color: zpd?.color }}>
                  {zpd?.label}
                </p>
              </div>
              <div
                className="rounded-xl px-3 py-2.5 text-center"
                style={{ background: intervention?.bg }}
              >
                <p className="text-lg">🎯</p>
                <p className="text-[10px] font-bold uppercase tracking-wide" style={{ color: intervention?.color }}>
                  Action
                </p>
                <p className="text-xs font-semibold mt-0.5" style={{ color: intervention?.color }}>
                  {intervention?.label}
                </p>
              </div>
            </div>

            {/* Session stats */}
            <div className="flex gap-3 text-center">
              {[
                { label: "Blocks today", value: twin.session_block_count },
                { label: "Struggles", value: twin.consecutive_struggles },
                { label: "Wins", value: twin.consecutive_successes },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="flex-1 rounded-xl py-2.5"
                  style={{ background: "#fff", border: "1px solid #E5E7EB" }}
                >
                  <p className="text-lg font-bold text-[#2F4731]">{stat.value}</p>
                  <p className="text-[10px] text-[#9CA3AF]">{stat.label}</p>
                </div>
              ))}
            </div>

            {twin.current_track && (
              <div className="flex items-center gap-2 text-xs text-[#6B7280]">
                <Shield size={12} />
                <span>Currently studying: <strong>{twin.current_track.replace(/_/g, " ")}</strong></span>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-8 text-sm text-[#9CA3AF]">
            {status === "connecting" ? "Connecting to live monitor…" : "No session active"}
          </div>
        )}

        {/* Safety flags */}
        {safetyFlags.length > 0 && (
          <div>
            <button
              onClick={() => setShowFlags(!showFlags)}
              className="w-full flex items-center justify-between text-xs font-semibold text-[#DC2626] mb-2"
            >
              <span className="flex items-center gap-1.5">
                <Shield size={12} />
                Safety Flags ({safetyFlags.length})
              </span>
              {showFlags ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
            <AnimatePresence>
              {showFlags && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden space-y-2"
                >
                  {safetyFlags.slice(-5).reverse().map((flag, i) => (
                    <SafetyFlagRow key={i} flag={flag} />
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Live event ticker */}
        <div>
          <button
            onClick={() => setShowEvents(!showEvents)}
            className="w-full flex items-center justify-between text-xs font-semibold text-[#6B7280] mb-2"
          >
            <span className="flex items-center gap-1.5">
              <Activity size={12} />
              Live Events
            </span>
            {showEvents ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          <AnimatePresence>
            {showEvents && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <EventTicker events={events} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
