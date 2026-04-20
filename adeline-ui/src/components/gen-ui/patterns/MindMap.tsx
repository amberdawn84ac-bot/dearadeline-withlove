"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import type { MindMapData, MindMapNode } from "@/lib/brain-client";

// ── Layout constants ──────────────────────────────────────────────────────────
const ROOT_R   = 28;
const L1_R     = 22;
const L2_R     = 16;
const ROOT_RING  = 130;  // px radius from center for depth-1 nodes
const L1_RING    = 90;   // additional px radius from depth-1 for depth-2 nodes

const TRACK_COLORS = {
  root:    { fill: "#2F4731", stroke: "#1A2E1E", text: "#fff" },
  depth1:  { fill: "#8BAE6B", stroke: "#5C7A2F", text: "#fff" },
  depth2:  { fill: "#E7DAC3", stroke: "#C4A882", text: "#374151" },
  edge:    "#C4A882",
};

// ── Math helpers ──────────────────────────────────────────────────────────────
function polarToXY(cx: number, cy: number, radius: number, angleDeg: number) {
  const rad = (angleDeg - 90) * (Math.PI / 180);
  return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) };
}

function wrapText(text: string, maxChars: number): string[] {
  const words = text.split(" ");
  const lines: string[] = [];
  let current = "";
  for (const w of words) {
    if ((current + " " + w).trim().length <= maxChars) {
      current = (current + " " + w).trim();
    } else {
      if (current) lines.push(current);
      current = w;
    }
  }
  if (current) lines.push(current);
  return lines.slice(0, 2); // max 2 lines
}

// ── Node layout ───────────────────────────────────────────────────────────────
interface LayoutNode {
  id:       string;
  label:    string;
  x:        number;
  y:        number;
  depth:    number;
  radius:   number;
  children: LayoutNode[];
  parentX?: number;
  parentY?: number;
  angleStart?: number;
  angleEnd?: number;
}

function buildLayout(
  node: MindMapNode,
  cx: number,
  cy: number,
  depth: number,
  angleStart: number,
  angleEnd: number,
  parentX?: number,
  parentY?: number,
): LayoutNode {
  const angle = (angleStart + angleEnd) / 2;
  const ringRadius = depth === 0 ? 0 : depth === 1 ? ROOT_RING : 0;

  let x = cx, y = cy;
  if (depth === 1) {
    const pos = polarToXY(cx, cy, ROOT_RING, angle);
    x = pos.x; y = pos.y;
  } else if (depth === 2 && parentX !== undefined && parentY !== undefined) {
    const pos = polarToXY(parentX, parentY, L1_RING, angle);
    x = pos.x; y = pos.y;
  }

  const nodeRadius = depth === 0 ? ROOT_R : depth === 1 ? L1_R : L2_R;
  const children = (node.children ?? []);
  const slice = (angleEnd - angleStart) / Math.max(children.length, 1);

  const childLayouts: LayoutNode[] = children.map((c, i) =>
    buildLayout(
      c,
      depth === 1 ? x : cx,
      depth === 1 ? y : cy,
      depth + 1,
      angleStart + i * slice,
      angleStart + (i + 1) * slice,
      x,
      y,
    )
  );

  return {
    id: node.id,
    label: node.label,
    x, y,
    depth,
    radius: nodeRadius,
    children: childLayouts,
    parentX,
    parentY,
    angleStart,
    angleEnd,
  };
}

// ── SVG Node ──────────────────────────────────────────────────────────────────
function SVGNode({
  node,
  selected,
  onSelect,
}: {
  node: LayoutNode;
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const isSelected = selected === node.id;
  const colors =
    node.depth === 0
      ? TRACK_COLORS.root
      : node.depth === 1
        ? TRACK_COLORS.depth1
        : TRACK_COLORS.depth2;

  const lines = wrapText(node.label, node.depth === 0 ? 14 : node.depth === 1 ? 10 : 8);
  const lineHeight = 11;
  const textStartY = -(lines.length - 1) * (lineHeight / 2);

  return (
    <g
      onClick={() => onSelect(node.id)}
      style={{ cursor: "pointer" }}
    >
      {/* Draw edges to children first (behind nodes) */}
      {node.children.map((child) => (
        <line
          key={`edge-${node.id}-${child.id}`}
          x1={node.x}
          y1={node.y}
          x2={child.x}
          y2={child.y}
          stroke={TRACK_COLORS.edge}
          strokeWidth={node.depth === 0 ? 2 : 1.5}
          strokeDasharray={node.depth === 1 ? "none" : "4 3"}
          opacity={0.6}
        />
      ))}

      {/* Node circle */}
      <circle
        cx={node.x}
        cy={node.y}
        r={node.radius + (isSelected ? 3 : 0)}
        fill={colors.fill}
        stroke={isSelected ? "#BD6809" : colors.stroke}
        strokeWidth={isSelected ? 3 : 1.5}
        style={{ transition: "r 0.15s, stroke 0.15s" }}
      />

      {/* Label lines */}
      {lines.map((line, i) => (
        <text
          key={i}
          x={node.x}
          y={node.y + textStartY + i * lineHeight}
          textAnchor="middle"
          dominantBaseline="middle"
          fill={colors.text}
          fontSize={node.depth === 0 ? 9 : node.depth === 1 ? 8 : 7}
          fontWeight={node.depth === 0 ? "bold" : node.depth === 1 ? "600" : "400"}
          style={{ pointerEvents: "none", userSelect: "none" }}
        >
          {line}
        </text>
      ))}

      {/* Recurse to children */}
      {node.children.map((child) => (
        <SVGNode key={child.id} node={child} selected={selected} onSelect={onSelect} />
      ))}
    </g>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
interface MindMapProps {
  data: MindMapData;
}

export function MindMap({ data }: MindMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 400, h: 400 });
  const [selected, setSelected] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);

  // Observe container width, keep square aspect
  useEffect(() => {
    const obs = new ResizeObserver((entries) => {
      const w = entries[0].contentRect.width;
      if (w > 0) setSize({ w, h: Math.max(280, w * 0.75) });
    });
    if (containerRef.current) obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  const cx = size.w / 2;
  const cy = size.h / 2;

  const layout = buildLayout(data.root, cx, cy, 0, 0, 360);

  // Find selected node's label for the detail panel
  function findNode(n: LayoutNode, id: string): LayoutNode | null {
    if (n.id === id) return n;
    for (const c of n.children) {
      const found = findNode(c, id);
      if (found) return found;
    }
    return null;
  }
  const selectedNode = selected ? findNode(layout, selected) : null;

  // Count total nodes
  function countNodes(n: MindMapNode): number {
    return 1 + (n.children ?? []).reduce((s, c) => s + countNodes(c), 0);
  }
  const total = countNodes(data.root);

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ background: "#F9FBF7", border: "1.5px solid #C4E0B0" }}
    >
      {/* Header */}
      <div className="px-4 py-2.5 flex items-center justify-between"
        style={{ borderBottom: "1px solid #E2EDD8" }}>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold uppercase tracking-widest text-[#2F4731]">
            Concept Map
          </span>
          <span className="text-[10px] text-[#9CA3AF]">{total} concepts</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setZoom((z) => Math.max(0.5, z - 0.15))}
            className="w-6 h-6 rounded text-sm font-bold text-[#2F4731] hover:bg-[#E2EDD8] transition-colors"
          >−</button>
          <span className="text-[10px] w-8 text-center text-[#9CA3AF]">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={() => setZoom((z) => Math.min(2, z + 0.15))}
            className="w-6 h-6 rounded text-sm font-bold text-[#2F4731] hover:bg-[#E2EDD8] transition-colors"
          >+</button>
        </div>
      </div>

      {/* SVG canvas */}
      <div ref={containerRef} style={{ width: "100%", overflow: "hidden" }}>
        <svg
          width={size.w}
          height={size.h}
          style={{ display: "block", transition: "height 0.2s" }}
        >
          <g transform={`translate(${(size.w - size.w * zoom) / 2},${(size.h - size.h * zoom) / 2}) scale(${zoom})`}>
            <SVGNode node={layout} selected={selected} onSelect={setSelected} />
          </g>
        </svg>
      </div>

      {/* Selected node detail */}
      {selectedNode && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="px-4 py-3 text-sm"
          style={{ borderTop: "1px solid #E2EDD8", background: "#fff" }}
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="font-semibold text-[#2F4731]">{selectedNode.label}</p>
              <p className="text-[10px] text-[#9CA3AF] mt-0.5">
                Depth {selectedNode.depth} ·{" "}
                {selectedNode.children.length > 0
                  ? `${selectedNode.children.length} sub-concept${selectedNode.children.length !== 1 ? "s" : ""}`
                  : "Leaf concept"}
              </p>
            </div>
            <button
              onClick={() => setSelected(null)}
              className="text-[#9CA3AF] hover:text-[#374151] text-sm shrink-0"
            >✕</button>
          </div>
        </motion.div>
      )}

      {/* Legend */}
      <div className="px-4 py-2 flex items-center gap-4 text-[10px] text-[#9CA3AF]"
        style={{ borderTop: "1px solid #E2EDD8" }}>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full inline-block" style={{ background: TRACK_COLORS.root.fill }} />
          Root
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full inline-block" style={{ background: TRACK_COLORS.depth1.fill }} />
          Main
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full inline-block" style={{ background: TRACK_COLORS.depth2.fill, border: "1px solid #C4A882" }} />
          Detail
        </span>
        <span className="ml-auto">Click node to inspect</span>
      </div>
    </div>
  );
}
