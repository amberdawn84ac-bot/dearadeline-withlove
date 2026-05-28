"use client";

import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus, Zap, Clock } from "lucide-react";

export interface VelocityDataPoint {
  date: string;
  lessonsCompleted: number;
  masteryGain: number;
}

export interface LearningVelocityCardProps {
  studentName?: string;
  currentVelocity: number;
  previousVelocity: number;
  trend: "accelerating" | "steady" | "slowing";
  recentData: VelocityDataPoint[];
  averageSessionMinutes?: number;
  streakDays?: number;
  track?: string;
}

export function LearningVelocityCard({
  studentName,
  currentVelocity,
  previousVelocity,
  trend,
  recentData,
  averageSessionMinutes,
  streakDays,
  track,
}: LearningVelocityCardProps) {
  const themeColor = track === "TRUTH_HISTORY" ? "#6B3A2A" : "#2F4731";
  const accentColor = track === "TRUTH_HISTORY" ? "#C27C4E" : "#8BAE6B";

  const trendIcon = trend === "accelerating" ? TrendingUp : trend === "slowing" ? TrendingDown : Minus;
  const TrendIcon = trendIcon;
  const trendColor = trend === "accelerating" ? "#22C55E" : trend === "slowing" ? "#F59E0B" : "#9CA3AF";
  const trendLabel = trend === "accelerating" ? "Accelerating" : trend === "slowing" ? "Slowing down" : "Steady pace";

  const velocityChange = currentVelocity - previousVelocity;
  const changePercent = previousVelocity > 0 ? Math.round((velocityChange / previousVelocity) * 100) : 0;

  // Simple sparkline from recent data
  const maxMastery = Math.max(...recentData.map((d) => d.masteryGain), 1);
  const sparklinePoints = recentData.map((d, i) => {
    const x = (i / Math.max(recentData.length - 1, 1)) * 100;
    const y = 100 - (d.masteryGain / maxMastery) * 80;
    return `${x},${y}`;
  }).join(" ");

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl overflow-hidden"
      style={{ border: `2px solid ${themeColor}20`, background: "#FFFEF7" }}
    >
      {/* Header */}
      <div className="px-5 py-3 flex items-center justify-between" style={{ background: `${themeColor}08` }}>
        <div className="flex items-center gap-2">
          <Zap size={16} style={{ color: accentColor }} />
          <h3 className="font-semibold text-sm" style={{ color: themeColor }}>
            {studentName ? `${studentName}'s` : "Your"} Learning Velocity
          </h3>
        </div>
        <div className="flex items-center gap-1" style={{ color: trendColor }}>
          <TrendIcon size={14} />
          <span className="text-[10px] font-medium">{trendLabel}</span>
        </div>
      </div>

      {/* Main velocity metric */}
      <div className="px-5 py-4 flex items-end justify-between">
        <div>
          <p className="text-3xl font-bold" style={{ color: themeColor }}>
            {currentVelocity.toFixed(1)}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">mastery points / day</p>
        </div>
        <div className="text-right">
          <p className="text-sm font-medium" style={{ color: trendColor }}>
            {velocityChange >= 0 ? "+" : ""}{changePercent}%
          </p>
          <p className="text-[10px] text-gray-400">vs last week</p>
        </div>
      </div>

      {/* Sparkline chart */}
      {recentData.length > 1 && (
        <div className="px-5 pb-3">
          <svg viewBox="0 0 100 100" className="w-full h-16" preserveAspectRatio="none">
            <polyline
              points={sparklinePoints}
              fill="none"
              stroke={accentColor}
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {/* Area fill */}
            <polygon
              points={`0,100 ${sparklinePoints} 100,100`}
              fill={`${accentColor}15`}
            />
          </svg>
        </div>
      )}

      {/* Stats row */}
      <div className="px-5 pb-4 flex gap-4">
        {averageSessionMinutes !== undefined && (
          <div className="flex items-center gap-1.5">
            <Clock size={12} className="text-gray-400" />
            <span className="text-xs text-gray-600">{averageSessionMinutes}m avg session</span>
          </div>
        )}
        {streakDays !== undefined && streakDays > 0 && (
          <div className="flex items-center gap-1.5">
            <Zap size={12} style={{ color: accentColor }} />
            <span className="text-xs text-gray-600">{streakDays} day streak</span>
          </div>
        )}
      </div>
    </motion.div>
  );
}
