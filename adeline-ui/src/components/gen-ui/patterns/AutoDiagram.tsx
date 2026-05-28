"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Network, ZoomIn, ZoomOut, Maximize2 } from "lucide-react";

export interface DiagramNode {
  id: string;
  label: string;
  type?: "concept" | "process" | "event" | "entity";
  x: number;
  y: number;
}

export interface DiagramEdge {
  from: string;
  to: string;
  label?: string;
  type?: "causes" | "contains" | "leads-to" | "relates";
}

export interface AutoDiagramProps {
  title: string;
  diagramType: "flowchart" | "concept-map" | "causal-chain" | "hierarchy";
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  description?: string;
  track?: string;
  onNodeClick?: (nodeId: string) => void;
}

export function AutoDiagram({
  title,
  diagramType,
  nodes,
  edges,
  description,
  track,
  onNodeClick,
}: AutoDiagramProps) {
  const [zoom, setZoom] = useState(1);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const themeColor = track === "TRUTH_HISTORY" ? "#6B3A2A" : "#2F4731";
  const accentColor = track === "TRUTH_HISTORY" ? "#C27C4E" : "#8BAE6B";

  const typeColors: Record<string, string> = {
    concept: accentColor,
    process: "#4A90D9",
    event: "#F59E0B",
    entity: "#8B5CF6",
  };

  const edgeStyles: Record<string, { dash?: string; color: string }> = {
    causes: { color: "#EF4444" },
    contains: { dash: "4 2", color: "#9CA3AF" },
    "leads-to": { color: accentColor },
    relates: { dash: "2 2", color: "#6B7280" },
  };

  // Scale to viewBox
  const maxX = Math.max(...nodes.map((n) => n.x), 1);
  const maxY = Math.max(...nodes.map((n) => n.y), 1);
  const getPos = (n: DiagramNode) => ({
    cx: (n.x / maxX) * 380 + 30,
    cy: (n.y / maxY) * 240 + 30,
  });

  const handleNodeClick = (nodeId: string) => {
    setSelectedNode(nodeId === selectedNode ? null : nodeId);
    onNodeClick?.(nodeId);
  };

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
          <Network size={16} style={{ color: accentColor }} />
          <div>
            <h3 className="font-semibold text-sm" style={{ color: themeColor }}>{title}</h3>
            <p className="text-[10px] text-gray-500 capitalize">{diagramType.replace("-", " ")}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}
            className="p-1.5 rounded hover:bg-gray-100 text-gray-500"
            title="Zoom out"
          >
            <ZoomOut size={14} />
          </button>
          <button
            onClick={() => setZoom((z) => Math.min(2, z + 0.25))}
            className="p-1.5 rounded hover:bg-gray-100 text-gray-500"
            title="Zoom in"
          >
            <ZoomIn size={14} />
          </button>
          <button
            onClick={() => setZoom(1)}
            className="p-1.5 rounded hover:bg-gray-100 text-gray-500"
            title="Reset"
          >
            <Maximize2 size={14} />
          </button>
        </div>
      </div>

      {/* Description */}
      {description && (
        <p className="px-5 py-2 text-xs text-gray-500 border-b border-gray-100">{description}</p>
      )}

      {/* Diagram */}
      <div className="px-3 py-4 overflow-auto" style={{ maxHeight: "360px" }}>
        <svg
          viewBox="0 0 440 300"
          className="w-full h-auto"
          style={{ transform: `scale(${zoom})`, transformOrigin: "center", transition: "transform 0.2s" }}
        >
          {/* Edge labels and lines */}
          {edges.map((edge) => {
            const fromNode = nodes.find((n) => n.id === edge.from);
            const toNode = nodes.find((n) => n.id === edge.to);
            if (!fromNode || !toNode) return null;
            const from = getPos(fromNode);
            const to = getPos(toNode);
            const style = edgeStyles[edge.type || "relates"] || edgeStyles.relates;
            const midX = (from.cx + to.cx) / 2;
            const midY = (from.cy + to.cy) / 2;

            return (
              <g key={`${edge.from}-${edge.to}`}>
                <line
                  x1={from.cx}
                  y1={from.cy}
                  x2={to.cx}
                  y2={to.cy}
                  stroke={style.color}
                  strokeWidth={1.5}
                  strokeDasharray={style.dash}
                  markerEnd="url(#arrowhead)"
                />
                {edge.label && (
                  <text
                    x={midX}
                    y={midY - 6}
                    textAnchor="middle"
                    className="text-[7px]"
                    fill="#9CA3AF"
                  >
                    {edge.label}
                  </text>
                )}
              </g>
            );
          })}

          {/* Arrowhead marker */}
          <defs>
            <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill="#9CA3AF" />
            </marker>
          </defs>

          {/* Nodes */}
          {nodes.map((node) => {
            const pos = getPos(node);
            const color = typeColors[node.type || "concept"] || accentColor;
            const isSelected = selectedNode === node.id;

            return (
              <g
                key={node.id}
                onClick={() => handleNodeClick(node.id)}
                className="cursor-pointer"
              >
                <rect
                  x={pos.cx - 40}
                  y={pos.cy - 14}
                  width={80}
                  height={28}
                  rx={6}
                  fill={isSelected ? `${color}20` : "white"}
                  stroke={color}
                  strokeWidth={isSelected ? 2 : 1.5}
                />
                <text
                  x={pos.cx}
                  y={pos.cy + 4}
                  textAnchor="middle"
                  className="text-[9px] font-medium"
                  fill={themeColor}
                >
                  {node.label.length > 12 ? node.label.slice(0, 11) + "…" : node.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Legend */}
      <div className="px-5 pb-3 flex flex-wrap gap-3 text-[10px] border-t border-gray-100 pt-2">
        {Object.entries(typeColors).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1">
            <div className="w-2.5 h-2.5 rounded-sm" style={{ background: color }} />
            <span className="text-gray-500 capitalize">{type}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
