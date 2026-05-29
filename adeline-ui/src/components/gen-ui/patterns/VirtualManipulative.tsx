"use client";

import { useState, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import { Hand, RotateCcw, CheckCircle2 } from "lucide-react";
import { fireGenUICallback } from "@/lib/genui-callback";

export interface ManipulativeItem {
  id: string;
  label: string;
  value: number;
  color?: string;
}

export interface DropZone {
  id: string;
  label: string;
  accepts: string[];
  targetValue?: number;
}

export interface VirtualManipulativeProps {
  title: string;
  instructions: string;
  items: ManipulativeItem[];
  dropZones: DropZone[];
  manipulativeType?: "fraction-bars" | "base-10-blocks" | "balance-scale" | "generic";
  track?: string;
  studentId?: string;
  lessonId?: string;
  blockId?: string;
  onComplete?: (state: { attempts: number; correct: boolean; timeMs: number }) => void;
  onStateChange?: (state: Record<string, unknown>) => void;
}

export function VirtualManipulative({
  title,
  instructions,
  items,
  dropZones,
  manipulativeType = "generic",
  track,
  studentId,
  lessonId,
  blockId,
  onComplete,
  onStateChange,
}: VirtualManipulativeProps) {
  const [placements, setPlacements] = useState<Record<string, string[]>>({});
  const [attempts, setAttempts] = useState(0);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);
  const [draggedItem, setDraggedItem] = useState<string | null>(null);
  const mountedAt = useRef(Date.now());

  const themeColor = track === "CREATION_SCIENCE" ? "#2F4731" : "#6B3A2A";
  const accentColor = track === "CREATION_SCIENCE" ? "#8BAE6B" : "#C27C4E";

  const handleDragStart = (itemId: string) => {
    setDraggedItem(itemId);
  };

  const handleDrop = useCallback(
    (zoneId: string) => {
      if (!draggedItem) return;
      const zone = dropZones.find((z) => z.id === zoneId);
      if (!zone || !zone.accepts.includes(draggedItem)) {
        setFeedback("That piece doesn't fit here. Try another zone.");
        setDraggedItem(null);
        return;
      }

      setPlacements((prev) => ({
        ...prev,
        [zoneId]: [...(prev[zoneId] || []), draggedItem],
      }));
      setDraggedItem(null);
      setFeedback(null);
    },
    [draggedItem, dropZones]
  );

  const checkAnswer = () => {
    setAttempts((a) => a + 1);
    const allCorrect = dropZones.every((zone) => {
      const placed = placements[zone.id] || [];
      if (zone.targetValue !== undefined) {
        const sum = placed.reduce((acc, itemId) => {
          const item = items.find((i) => i.id === itemId);
          return acc + (item?.value || 0);
        }, 0);
        return sum === zone.targetValue;
      }
      return placed.length > 0;
    });

    if (allCorrect) {
      setCompleted(true);
      setFeedback("Excellent! You've placed everything correctly.");
      onComplete?.({ attempts: attempts + 1, correct: true, timeMs: Date.now() - mountedAt.current });
      fireGenUICallback({ studentId, lessonId, componentType: "VirtualManipulative", event: "onAnswer", state: { isCorrect: true, attempts: attempts + 1 }, blockId, track });
      fireGenUICallback({ studentId, lessonId, componentType: "VirtualManipulative", event: "onComplete", state: { attempts: attempts + 1, timeMs: Date.now() - mountedAt.current }, blockId, track });
    } else {
      setFeedback("Not quite right. Try rearranging the pieces.");
    }
    onStateChange?.({ placements, attempts: attempts + 1, completed: allCorrect });
  };

  const reset = () => {
    setPlacements({});
    setFeedback(null);
  };

  const availableItems = items.filter(
    (item) => !Object.values(placements).flat().includes(item.id)
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl overflow-hidden"
      style={{ border: `2px solid ${themeColor}20`, background: "#FFFEF7" }}
    >
      {/* Header */}
      <div className="px-5 py-3" style={{ background: `${themeColor}08` }}>
        <div className="flex items-center gap-2">
          <Hand size={16} style={{ color: accentColor }} />
          <h3 className="font-semibold text-sm" style={{ color: themeColor }}>{title}</h3>
        </div>
        <p className="text-xs text-gray-500 mt-1 capitalize">{manipulativeType.replace(/-/g, " ")}</p>
      </div>

      {/* Instructions */}
      <p className="px-5 py-3 text-sm text-gray-600 border-b border-gray-100">{instructions}</p>

      {/* Available items */}
      <div className="px-5 py-3">
        <p className="text-xs font-medium text-gray-500 mb-2">Drag these pieces:</p>
        <div className="flex flex-wrap gap-2">
          {availableItems.map((item) => (
            <div
              key={item.id}
              draggable
              onDragStart={() => handleDragStart(item.id)}
              className="px-3 py-2 rounded-lg cursor-grab active:cursor-grabbing text-xs font-medium border transition-transform hover:scale-105"
              style={{
                background: item.color || `${accentColor}15`,
                borderColor: item.color || `${accentColor}40`,
                color: themeColor,
              }}
            >
              {item.label} ({item.value})
            </div>
          ))}
          {availableItems.length === 0 && (
            <p className="text-xs text-gray-400 italic">All pieces placed!</p>
          )}
        </div>
      </div>

      {/* Drop zones */}
      <div className="px-5 py-3 grid grid-cols-2 gap-3">
        {dropZones.map((zone) => (
          <div
            key={zone.id}
            onDragOver={(e) => e.preventDefault()}
            onDrop={() => handleDrop(zone.id)}
            className="border-2 border-dashed rounded-xl p-3 min-h-[80px] transition-colors"
            style={{
              borderColor: draggedItem ? `${accentColor}60` : "#E5E7EB",
              background: draggedItem ? `${accentColor}05` : "white",
            }}
          >
            <p className="text-xs font-medium text-gray-500 mb-2">{zone.label}</p>
            <div className="flex flex-wrap gap-1">
              {(placements[zone.id] || []).map((itemId) => {
                const item = items.find((i) => i.id === itemId);
                return (
                  <span
                    key={itemId}
                    className="px-2 py-1 rounded text-[10px] font-medium"
                    style={{ background: `${accentColor}20`, color: accentColor }}
                  >
                    {item?.label}
                  </span>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Feedback */}
      {feedback && (
        <div
          className="mx-5 mb-3 px-4 py-2 rounded-lg text-xs font-medium"
          style={{
            background: completed ? "#F0FDF4" : "#FEF3C7",
            color: completed ? "#166534" : "#92400E",
          }}
        >
          {feedback}
        </div>
      )}

      {/* Actions */}
      <div className="px-5 pb-4 flex items-center gap-2">
        {!completed && (
          <>
            <button
              onClick={checkAnswer}
              className="flex-1 py-2 rounded-lg text-xs font-medium text-white"
              style={{ background: accentColor }}
            >
              Check Answer
            </button>
            <button
              onClick={reset}
              className="p-2 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50"
            >
              <RotateCcw size={14} />
            </button>
          </>
        )}
        {completed && (
          <div className="flex items-center gap-2 text-sm font-medium" style={{ color: accentColor }}>
            <CheckCircle2 size={16} />
            Complete — {attempts} attempt{attempts !== 1 ? "s" : ""}
          </div>
        )}
      </div>
    </motion.div>
  );
}
