"use client";

import { useEffect, useRef, useState, useCallback } from "react";

// ── Event types mirroring adeline-brain/app/api/realtime.py ──────────────────

export type ZPDZone = "FRUSTRATED" | "IN_ZPD" | "BORED";
export type Intervention = "CONTINUE" | "SCAFFOLD" | "ELEVATE" | "BREAK";

export interface CognitiveTwinSnapshot {
  student_id: string;
  zpd_zone: ZPDZone;
  working_memory_load: number;
  engagement_level: number;
  frustration_score: number;
  session_block_count: number;
  consecutive_struggles: number;
  consecutive_successes: number;
  current_track: string | null;
  interaction_velocity: number;
  intervention: Intervention;
  active_monitors?: number;
}

export interface SafetyFlagEvent {
  student_id: string;
  block_type: string;
  flags: string[];
  warnings: string[];
  severity?: "block" | "warning";
}

export interface BlockGeneratedEvent {
  student_id: string;
  block_type: string;
  lesson_id: string;
}

export interface ZPDShiftEvent {
  student_id: string;
  zone: ZPDZone;
  consecutive_struggles?: number;
}

export type MonitorEvent =
  | { event: "twin_snapshot"; payload: CognitiveTwinSnapshot }
  | { event: "cognitive_update"; payload: CognitiveTwinSnapshot }
  | { event: "block_generated"; payload: BlockGeneratedEvent }
  | { event: "safety_flag"; payload: SafetyFlagEvent }
  | { event: "zpd_shift"; payload: ZPDShiftEvent }
  | { event: "agent_thinking"; payload: { student_id: string; message: string; track: string } }
  | { event: "session_start"; payload: { session_id: string; student_id: string } }
  | { event: "session_end"; payload: { session_id: string; student_id: string } }
  | { event: "keepalive" | "pong"; payload?: undefined };

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

export interface UseStudentMonitorOptions {
  studentId: string;
  /** Auto-reconnect on disconnect. Default: true */
  autoReconnect?: boolean;
  /** Max reconnect attempts. Default: 5 */
  maxRetries?: number;
  /** Event handler called on every received event */
  onEvent?: (event: MonitorEvent) => void;
  /** Called when twin state updates */
  onTwinUpdate?: (twin: CognitiveTwinSnapshot) => void;
  /** Called when a safety flag fires */
  onSafetyFlag?: (event: SafetyFlagEvent) => void;
}

export interface UseStudentMonitorReturn {
  status: ConnectionStatus;
  twin: CognitiveTwinSnapshot | null;
  events: MonitorEvent[];
  safetyFlags: SafetyFlagEvent[];
  connect: () => void;
  disconnect: () => void;
}

const BRAIN_URL = process.env.NEXT_PUBLIC_BRAIN_URL ?? "https://dearadeline-withlove-production.up.railway.app";
const WS_URL = BRAIN_URL.replace(/^https?/, (m) => (m === "https" ? "wss" : "ws"));

export function useStudentMonitor({
  studentId,
  autoReconnect = true,
  maxRetries = 5,
  onEvent,
  onTwinUpdate,
  onSafetyFlag,
}: UseStudentMonitorOptions): UseStudentMonitorReturn {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [twin, setTwin] = useState<CognitiveTwinSnapshot | null>(null);
  const [events, setEvents] = useState<MonitorEvent[]>([]);
  const [safetyFlags, setSafetyFlags] = useState<SafetyFlagEvent[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearPing = () => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  };

  const handleMessage = useCallback(
    (raw: string) => {
      let parsed: MonitorEvent;
      try {
        parsed = JSON.parse(raw);
      } catch {
        return;
      }

      setEvents((prev) => [...prev.slice(-99), parsed]);
      onEvent?.(parsed);

      if (parsed.event === "twin_snapshot" || parsed.event === "cognitive_update") {
        setTwin(parsed.payload as CognitiveTwinSnapshot);
        onTwinUpdate?.(parsed.payload as CognitiveTwinSnapshot);
      }

      if (parsed.event === "safety_flag") {
        const flag = parsed.payload as SafetyFlagEvent;
        setSafetyFlags((prev) => [...prev.slice(-49), flag]);
        onSafetyFlag?.(flag);
      }
    },
    [onEvent, onTwinUpdate, onSafetyFlag]
  );

  const openSocket = useCallback(() => {
    if (!studentId) return;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    setStatus("connecting");
    const ws = new WebSocket(`${WS_URL}/ws/monitor/${studentId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      retriesRef.current = 0;

      // Keep-alive ping every 25s
      clearPing();
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
      }, 25_000);
    };

    ws.onmessage = (e) => handleMessage(e.data);

    ws.onerror = () => setStatus("error");

    ws.onclose = () => {
      setStatus("disconnected");
      clearPing();

      if (autoReconnect && retriesRef.current < maxRetries) {
        retriesRef.current += 1;
        const delay = Math.min(1000 * 2 ** retriesRef.current, 30_000);
        setTimeout(openSocket, delay);
      }
    };
  }, [studentId, autoReconnect, maxRetries, handleMessage]);

  const disconnect = useCallback(() => {
    autoReconnect = false;
    clearPing();
    wsRef.current?.close();
    wsRef.current = null;
    setStatus("disconnected");
  }, []);

  useEffect(() => {
    openSocket();
    return () => {
      clearPing();
      wsRef.current?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentId]);

  return {
    status,
    twin,
    events,
    safetyFlags,
    connect: openSocket,
    disconnect,
  };
}
