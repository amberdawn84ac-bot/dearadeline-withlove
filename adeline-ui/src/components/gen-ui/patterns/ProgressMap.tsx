"use client";

import { motion } from "framer-motion";
import { MapPin, CheckCircle2, Circle, Lock } from "lucide-react";

export interface MapNode {
  id: string;
  label: string;
  status: "completed" | "current" | "locked" | "available";
  mastery?: number;
  x: number;
  y: number;
}

export interface MapEdge {
  from: string;
  to: string;
}

export interface ProgressMapProps {
  title: string;
  nodes: MapNode[];
  edges: MapEdge[];
  track?: string;
  onNodeClick?: (nodeId: string) => void;
}

export function ProgressMap({
  title,
  nodes,
  edges,
  track,
  onNodeClick,
}: ProgressMapProps) {
  const themeColor = track === "TRUTH_HISTORY" ? "#6B3A2A" : "#2F4731";
  const accentColor = track === "TRUTH_HISTORY" ? "#C27C4E" : "#8BAE6B";

  const statusColors: Record<string, { bg: string; border: string; text: string }> = {
    completed: { bg: `${accentColor}20`, border: accentColor, text: accentColor },
    current: { bg: "#FEF3C7", border: "#F59E0B", text: "#92400E" },
    available: { bg: "white", border: "#D1D5DB", text: "#6B7280" },
    locked: { bg: "#F3F4F6", border: "#E5E7EB", text: "#9CA3AF" },
  };

  const statusIcons: Record<string, React.ReactNode> = {
    completed: <CheckCircle2 size={12} />,
    current: <MapPin size={12} />,
    available: <Circle size={12} />,
    locked: <Lock size={10} />,
  };

  // Normalize coordinates to SVG viewport
  const maxX = Math.max(...nodes.map((n) => n.x), 1);
  const maxY = Math.max(...nodes.map((n) => n.y), 1);
  const scale = (n: MapNode) => ({
    cx: (n.x / maxX) * 280 + 30,
    cy: (n.y / maxY) * 200 + 30,
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl overflow-hidden"
      style={{ border: `2px solid ${themeColor}20`, background: "#FFFEF7" }}
    >
      {/* Header */}
      <div className="px-5 py-3 flex items-center gap-2" style={{ background: `${themeColor}08` }}>
        <MapPin size={16} style={{ color: accentColor }} />
        <h3 className="font-semibold text-sm" style={{ color: themeColor }}>{title}</h3>
      </div>

      {/* Map visualization */}
      <div className="px-5 py-4">
        <svg viewBox="0 0 340 260" className="w-full h-auto" style={{ maxHeight: "260px" }}>
          {/* Edges */}
          {edges.map((edge) => {
            const fromNode = nodes.find((n) => n.id === edge.from);
            const toNode = nodes.find((n) => n.id === edge.to);
            if (!fromNode || !toNode) return null;
            const from = scale(fromNode);
            const to = scale(toNode);
            const isActive = fromNode.status === "completed" || fromNode.status === "current";
            return (
              <line
                key={`${edge.from}-${edge.to}`}
                x1={from.cx}
                y1={from.cy}
                x2={to.cx}
                y2={to.cy}
                stroke={isActive ? accentColor : "#E5E7EB"}
                strokeWidth={isActive ? 2 : 1.5}
                strokeDasharray={isActive ? undefined : "4 4"}
              />
            );
          })}

          {/* Nodes */}
          {nodes.map((node) => {
            const pos = scale(node);
            const colors = statusColors[node.status];
            return (
              <g
                key={node.id}
                onClick={() => node.status !== "locked" && onNodeClick?.(node.id)}
                className={node.status !== "locked" ? "cursor-pointer" : ""}
              >
                <circle
                  cx={pos.cx}
                  cy={pos.cy}
                  r={node.status === "current" ? 18 : 14}
                  fill={colors.bg}
                  stroke={colors.border}
                  strokeWidth={node.status === "current" ? 2.5 : 1.5}
                />
                {/* Mastery ring for completed nodes */}
                {node.status === "completed" && node.mastery !== undefined && (
                  <circle
                    cx={pos.cx}
                    cy={pos.cy}
                    r={16}
                    fill="none"
                    stroke={accentColor}
                    strokeWidth={2}
                    strokeDasharray={`${node.mastery * 100.5} 100.5`}
                    transform={`rotate(-90 ${pos.cx} ${pos.cy})`}
                    opacity={0.6}
                  />
                )}
                <text
                  x={pos.cx}
                  y={pos.cy + 28}
                  textAnchor="middle"
                  className="text-[8px]"
                  fill={colors.text}
                >
                  {node.label.length > 14 ? node.label.slice(0, 12) + "…" : node.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Legend */}
      <div className="px-5 pb-3 flex items-center gap-4 text-[10px]">
        {Object.entries(statusColors).map(([status, colors]) => (
          <div key={status} className="flex items-center gap-1" style={{ color: colors.text }}>
            {statusIcons[status]}
            <span className="capitalize">{status}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
