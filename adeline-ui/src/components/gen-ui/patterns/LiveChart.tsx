"use client";

/**
 * LiveChart — Real-time mastery progress visualization.
 * Displays student's BKT mastery or priority_score over time with smooth animations.
 * Used in GENUI_ASSEMBLY blocks to provide visual feedback on growth.
 */

import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, Activity } from "lucide-react";

interface DataPoint {
  timestamp: string;
  mastery: number;
  concept: string;
}

interface LiveChartProps {
  state: Record<string, any>;
  onStateChange: (newState: Record<string, any>) => void;
  callbacks?: string[];
  // Component-specific props
  data: DataPoint[];
  chartType?: "line" | "bar";  // Default: line
  showCrossTrack?: boolean;
}

export function LiveChart({
  state,
  onStateChange,
  callbacks = [],
  data,
  chartType = "line",
  showCrossTrack = false,
}: LiveChartProps) {
  const [chartData, setChartData] = useState<DataPoint[]>(data);
  const [hoveredPoint, setHoveredPoint] = useState<DataPoint | null>(null);

  // Auto-update when data changes from callback
  useEffect(() => {
    if (data.length > 0) {
      setChartData(data);
    }
  }, [data]);

  const currentMastery = chartData[chartData.length - 1]?.mastery || 0;
  const previousMastery = chartData[chartData.length - 2]?.mastery || currentMastery;
  const isImproving = currentMastery >= previousMastery;
  const improvementRate = ((currentMastery - previousMastery) * 100).toFixed(1);

  // Calculate chart dimensions
  const chartWidth = 100;
  const chartHeight = 60;
  const padding = 5;
  const maxMastery = 1.0;

  // Generate SVG path for line chart
  const generateLinePath = () => {
    if (chartData.length < 2) return "";

    const points = chartData.map((point, index) => {
      const x = padding + (index / (chartData.length - 1)) * (chartWidth - 2 * padding);
      const y = chartHeight - padding - (point.mastery / maxMastery) * (chartHeight - 2 * padding);
      return `${x},${y}`;
    });

    return `M ${points.join(" L ")}`;
  };

  const linePath = generateLinePath();

  return (
    <div
      className="rounded-xl p-5 space-y-4"
      style={{ background: "#FFFEF7", border: "2px solid #065F4640" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">📊</span>
        <span className="text-xs font-bold px-2 py-0.5 rounded-full uppercase tracking-wider bg-[#065F46] text-white">
          Mastery Progress
        </span>
        {isImproving ? (
          <div className="flex items-center gap-1 text-xs text-green-600 ml-auto">
            <TrendingUp size={14} />
            <span>+{improvementRate}%</span>
          </div>
        ) : (
          <div className="flex items-center gap-1 text-xs text-red-600 ml-auto">
            <TrendingDown size={14} />
            <span>{improvementRate}%</span>
          </div>
        )}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-[#374151]/60">
          <span>Your mastery over time</span>
          <span>Current: {(currentMastery * 100).toFixed(0)}%</span>
        </div>

        {/* Simple SVG Chart */}
        <div className="relative bg-white rounded-lg border border-[#E7DAC3] p-4">
          <svg
            viewBox={`0 0 ${chartWidth} ${chartHeight}`}
            className="w-full h-32"
            preserveAspectRatio="none"
          >
            {/* Grid lines */}
            {[0.25, 0.5, 0.75, 1.0].map((level) => (
              <line
                key={level}
                x1={padding}
                y1={chartHeight - padding - (level / maxMastery) * (chartHeight - 2 * padding)}
                x2={chartWidth - padding}
                y2={chartHeight - padding - (level / maxMastery) * (chartHeight - 2 * padding)}
                stroke="#E7DAC3"
                strokeWidth="0.5"
                strokeDasharray="2,2"
              />
            ))}

            {/* Data line */}
            {linePath && (
              <path
                d={linePath}
                fill="none"
                stroke="#065F46"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}

            {/* Data points */}
            {chartData.map((point, index) => {
              const x = padding + (index / (chartData.length - 1)) * (chartWidth - 2 * padding);
              const y = chartHeight - padding - (point.mastery / maxMastery) * (chartHeight - 2 * padding);
              return (
                <circle
                  key={point.timestamp}
                  cx={x}
                  cy={y}
                  r={hoveredPoint?.timestamp === point.timestamp ? 3 : 2}
                  fill="#065F46"
                  onMouseEnter={() => setHoveredPoint(point)}
                  onMouseLeave={() => setHoveredPoint(null)}
                  className="cursor-pointer"
                />
              );
            })}
          </svg>

          {/* Tooltip */}
          {hoveredPoint && (
            <div
              className="absolute top-2 right-2 bg-[#2F4731] text-white text-xs p-2 rounded shadow-lg"
              style={{ pointerEvents: "none" }}
            >
              <div className="font-semibold">{hoveredPoint.concept}</div>
              <div>Mastery: {(hoveredPoint.mastery * 100).toFixed(0)}%</div>
              <div className="text-[#374151]/70 text-[10px]">{hoveredPoint.timestamp}</div>
            </div>
          )}
        </div>
      </div>

      {/* Cross-track concepts */}
      {showCrossTrack && chartData.length > 1 && (
        <div className="space-y-2">
          <p className="text-xs text-[#374151]/60">Related concepts</p>
          <div className="flex flex-wrap gap-2">
            {chartData.slice(-3).map((point) => (
              <div
                key={point.timestamp}
                className="px-2 py-1 rounded-full bg-[#F3E8FF] border border-[#7C3AED]/20"
              >
                <span className="text-xs text-[#6B21A8]">{point.concept}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Activity indicator */}
      <div className="flex items-center gap-2 text-xs text-[#374151]/60">
        <Activity size={12} className="text-[#065F46]" />
        <span>Updates live as you complete activities</span>
      </div>
    </div>
  );
}
