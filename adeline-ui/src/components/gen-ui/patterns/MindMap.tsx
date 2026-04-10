"use client";

import { useState } from "react";
import type { MindMapData, MindMapNode } from "@/lib/brain-client";

interface MindMapNodeProps {
  node: MindMapNode;
  depth: number;
}

function MindMapNodeItem({ node, depth }: MindMapNodeProps) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children && node.children.length > 0;
  const indent = depth * 16;

  return (
    <div>
      <div
        className="flex items-center gap-2 py-1 cursor-pointer select-none"
        style={{ paddingLeft: `${indent}px` }}
        onClick={() => hasChildren && setExpanded((e) => !e)}
      >
        {hasChildren ? (
          <span className="text-[#166534] font-bold text-xs w-4 shrink-0">
            {expanded ? "▼" : "▶"}
          </span>
        ) : (
          <span className="w-4 shrink-0 text-[#166534] text-xs">•</span>
        )}
        <span
          className={
            depth === 0
              ? "font-bold text-[#166534] text-sm"
              : "text-[#1F2937] text-sm"
          }
        >
          {node.label}
        </span>
      </div>
      {hasChildren && expanded && (
        <div>
          {node.children.map((child) => (
            <MindMapNodeItem key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

interface MindMapProps {
  data: MindMapData;
}

export function MindMap({ data }: MindMapProps) {
  return (
    <div
      className="rounded-xl p-4"
      style={{ background: "#F0FDF4", border: "1.5px solid #BBF7D0" }}
    >
      <p className="text-xs font-bold text-[#166534] uppercase tracking-widest mb-3">
        Concept Map
      </p>
      <MindMapNodeItem node={data.root} depth={0} />
    </div>
  );
}
