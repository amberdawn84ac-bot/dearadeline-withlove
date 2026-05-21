"use client";

/**
 * InteractiveConceptMap — Draggable concept map where students draw connections.
 *
 * Students drag nodes and connect them by clicking source → target.
 * Submits the completed edge list as evidence via onComplete.
 * Uses @xyflow/react for drag, zoom, and edge rendering.
 */

import { useState, useCallback, useRef } from "react";
import {
  ReactFlow,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  BackgroundVariant,
  type Connection,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { CheckCircle, Network, RotateCcw } from "lucide-react";

export interface ConceptNode {
  id: string;
  label: string;
  x?: number;
  y?: number;
}

export interface ConceptEdge {
  source: string;
  target: string;
  label?: string;
}

export interface InteractiveConceptMapProps {
  title: string;
  nodes: ConceptNode[];
  suggestedEdges?: ConceptEdge[];
  onComplete?: (edges: ConceptEdge[]) => void;
  onStateChange?: (state: Record<string, any>) => void;
}

const NODE_W = 140;
const NODE_H = 40;

function buildInitialNodes(nodes: ConceptNode[]): Node[] {
  const cols = Math.ceil(Math.sqrt(nodes.length));
  return nodes.map((n, i) => ({
    id: n.id,
    position: {
      x: n.x ?? 40 + (i % cols) * (NODE_W + 80),
      y: n.y ?? 40 + Math.floor(i / cols) * (NODE_H + 80),
    },
    data: { label: n.label },
    style: {
      background: "#FFFEF7",
      border: "2px solid #2F4731",
      borderRadius: 10,
      padding: "6px 12px",
      fontSize: 12,
      fontWeight: 600,
      color: "#2F4731",
      width: NODE_W,
    },
  }));
}

function buildInitialEdges(suggested: ConceptEdge[]): Edge[] {
  return suggested.map((e, i) => ({
    id: `e-${i}`,
    source: e.source,
    target: e.target,
    label: e.label,
    animated: true,
    style: { stroke: "#BD6809", strokeWidth: 2 },
    labelStyle: { fill: "#2F4731", fontWeight: 600, fontSize: 11 },
  }));
}

export function InteractiveConceptMap({
  title,
  nodes: initialNodes,
  suggestedEdges = [],
  onComplete,
  onStateChange,
}: InteractiveConceptMapProps) {
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState(buildInitialNodes(initialNodes));
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState(buildInitialEdges(suggestedEdges));
  const [completed, setCompleted] = useState(false);
  const mountedAt = useRef(Date.now());

  const onConnect = useCallback(
    (connection: Connection) => {
      const newEdge: Edge = {
        ...connection,
        id: `e-${Date.now()}`,
        animated: true,
        style: { stroke: "#BD6809", strokeWidth: 2 },
      };
      setRfEdges((eds) => addEdge(newEdge, eds));
      onStateChange?.({ edges: [...rfEdges, newEdge].map((e) => ({ source: e.source, target: e.target })) });
    },
    [rfEdges, setRfEdges, onStateChange]
  );

  const handleReset = () => {
    setRfNodes(buildInitialNodes(initialNodes));
    setRfEdges(buildInitialEdges(suggestedEdges));
    setCompleted(false);
    mountedAt.current = Date.now();
  };

  const handleSubmit = () => {
    const responseTimeMs = Date.now() - mountedAt.current;
    const edgeList: ConceptEdge[] = rfEdges.map((e) => ({
      source: e.source,
      target: e.target,
      label: typeof e.label === "string" ? e.label : undefined,
    }));
    setCompleted(true);
    onComplete?.(edgeList);
    onStateChange?.({ edges: edgeList, completed: true, responseTimeMs });
  };

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ border: "2px solid #2F473130", background: "#FFFEF7" }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ background: "#F5F0E8", borderBottom: "1.5px solid #E7DAC3" }}
      >
        <div className="flex items-center gap-2">
          <Network size={15} style={{ color: "#BD6809" }} />
          <span className="text-sm font-bold" style={{ color: "#2F4731" }}>
            {title}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <p className="text-xs" style={{ color: "#2F473180" }}>
            Connect nodes by dragging from handle to handle
          </p>
          <button
            onClick={handleReset}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold"
            style={{ background: "#E7DAC3", color: "#2F4731" }}
            title="Reset map"
          >
            <RotateCcw size={11} />
            Reset
          </button>
        </div>
      </div>

      {/* React Flow canvas */}
      <div style={{ height: 320 }}>
        <ReactFlow
          nodes={rfNodes}
          edges={rfEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView
          attributionPosition="bottom-left"
          style={{ background: "#FFFEF7" }}
        >
          <Controls />
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#2F473115" />
        </ReactFlow>
      </div>

      {/* Footer */}
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ background: "#F5F0E8", borderTop: "1.5px solid #E7DAC3" }}
      >
        <p className="text-xs" style={{ color: "#2F473160" }}>
          {rfEdges.length} connection{rfEdges.length !== 1 ? "s" : ""} drawn
        </p>
        {completed ? (
          <div className="flex items-center gap-1.5 text-sm font-bold" style={{ color: "#2F4731" }}>
            <CheckCircle size={16} />
            Map submitted!
          </div>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={rfEdges.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ background: "#BD6809", color: "#fff" }}
            title={rfEdges.length === 0 ? "Draw at least one connection first" : "Submit your concept map"}
          >
            <CheckCircle size={13} />
            Submit Map
          </button>
        )}
      </div>
    </div>
  );
}
