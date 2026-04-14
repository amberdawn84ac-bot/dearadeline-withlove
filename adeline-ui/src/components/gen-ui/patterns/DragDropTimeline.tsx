"use client";

/**
 * DragDropTimeline — Interactive timeline with drag-and-drop sorting.
 * Students scramble and reorder timeline events to demonstrate understanding.
 * Used in GENUI_ASSEMBLY blocks for history, literature, science, and justice tracks.
 */

import { useState } from "react";
import { GripVertical, CheckCircle2, XCircle, ArrowUpDown } from "lucide-react";

interface TimelineEvent {
  id: string;
  label: string;
  date: string;
  description: string;
}

interface DragDropTimelineProps {
  state: Record<string, any>;
  onStateChange: (newState: Record<string, any>) => void;
  callbacks?: string[];
  // Component-specific props
  events: TimelineEvent[];
  scrambled?: boolean;  // If true, events are shuffled initially
}

export function DragDropTimeline({
  state,
  onStateChange,
  callbacks = [],
  events,
  scrambled = true,
}: DragDropTimelineProps) {
  const [orderedEvents, setOrderedEvents] = useState<TimelineEvent[]>(
    state.orderedEvents || (scrambled ? [...events].sort(() => Math.random() - 0.5) : events)
  );
  const [wrongAttempts, setWrongAttempts] = useState(state.wrongAttempts || 0);
  const [isComplete, setIsComplete] = useState(state.isComplete || false);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (dropIndex: number) => {
    if (draggedIndex === null || draggedIndex === dropIndex) return;

    const newEvents = [...orderedEvents];
    const [removed] = newEvents.splice(draggedIndex, 1);
    newEvents.splice(dropIndex, 0, removed);

    setOrderedEvents(newEvents);
    setDraggedIndex(null);
    
    onStateChange({
      ...state,
      orderedEvents: newEvents,
      wrongAttempts,
      isComplete,
    });
  };

  const handleCheckOrder = () => {
    // Check if events are in correct chronological order
    const correctOrder = [...events].sort((a, b) => a.date.localeCompare(b.date));
    const isCorrect = orderedEvents.every((event, index) => event.id === correctOrder[index]?.id);

    if (isCorrect) {
      setIsComplete(true);
      onStateChange({
        ...state,
        orderedEvents,
        wrongAttempts,
        isComplete: true,
      });
      if (callbacks.includes("onComplete")) {
        console.log("[DragDropTimeline] Timeline completed successfully");
      }
    } else {
      const newWrongAttempts = wrongAttempts + 1;
      setWrongAttempts(newWrongAttempts);
      onStateChange({
        ...state,
        orderedEvents,
        wrongAttempts: newWrongAttempts,
        isComplete: false,
      });
      
      // Trigger onStruggle after 2+ wrong attempts
      if (newWrongAttempts >= 2 && callbacks.includes("onStruggle")) {
        console.log("[DragDropTimeline] Struggle detected - 2+ wrong attempts");
      }
    }
  };

  const handleReset = () => {
    const shuffled = [...events].sort(() => Math.random() - 0.5);
    setOrderedEvents(shuffled);
    setWrongAttempts(0);
    setIsComplete(false);
    onStateChange({
      ...state,
      orderedEvents: shuffled,
      wrongAttempts: 0,
      isComplete: false,
    });
  };

  const correctOrder = [...events].sort((a, b) => a.date.localeCompare(b.date));

  return (
    <div
      className="rounded-xl p-5 space-y-4"
      style={{ background: "#FFFEF7", border: "2px solid #7C3AED40" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">📅</span>
        <span className="text-xs font-bold px-2 py-0.5 rounded-full uppercase tracking-wider bg-[#7C3AED] text-white">
          Drag & Drop Timeline
        </span>
        {wrongAttempts > 0 && (
          <span className="text-xs text-[#7C3AED]/70 ml-auto">
            Attempts: {wrongAttempts}
          </span>
        )}
      </div>

      <p className="text-sm text-[#2F4731]">
        Drag the events to put them in chronological order from earliest to latest.
      </p>

      <div className="space-y-2">
        {orderedEvents.map((event, index) => (
          <div
            key={event.id}
            draggable
            onDragStart={() => handleDragStart(index)}
            onDragOver={handleDragOver}
            onDrop={() => handleDrop(index)}
            className={`
              flex items-start gap-3 p-4 rounded-lg border-2 transition-all cursor-grab
              ${draggedIndex === index ? "border-[#7C3AED] bg-[#F3E8FF]" : "border-[#E7DAC3] bg-white hover:border-[#7C3AED]/50"}
            `}
          >
            <GripVertical size={16} className="text-[#7C3AED] mt-1" />
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-bold text-[#7C3AED]">{event.date}</span>
                <span className="text-sm font-semibold text-[#2F4731]">{event.label}</span>
              </div>
              <p className="text-xs text-[#374151]">{event.description}</p>
            </div>
            <span className="text-xs text-[#374151]/40">#{index + 1}</span>
          </div>
        ))}
      </div>

      {!isComplete ? (
        <div className="flex gap-2">
          <button
            onClick={handleCheckOrder}
            className="flex-1 px-4 py-2 text-sm font-semibold bg-[#7C3AED] text-white rounded-lg hover:bg-[#6D28D9] transition-colors flex items-center justify-center gap-2"
          >
            <CheckCircle2 size={16} />
            Check Order
          </button>
          <button
            onClick={handleReset}
            className="px-4 py-2 text-sm font-semibold bg-[#E7DAC3] text-[#2F4731] rounded-lg hover:bg-[#D4C4A8] transition-colors flex items-center justify-center gap-2"
          >
            <ArrowUpDown size={16} />
            Reset
          </button>
        </div>
      ) : (
        <div className="p-4 rounded-lg bg-[#D4EDDA] border border-[#28A745] space-y-2">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={20} className="text-green-600" />
            <p className="text-sm font-semibold text-[#155724]">Correct! Well done.</p>
          </div>
          <div className="text-xs text-[#155724]/80">
            You correctly ordered all {events.length} timeline events.
          </div>
        </div>
      )}

      {wrongAttempts >= 2 && !isComplete && (
        <div className="p-3 rounded-lg bg-[#FEF2F2] border border-[#991B1B]">
          <div className="flex items-center gap-2 text-xs">
            <XCircle size={14} className="text-red-600" />
            <span className="text-[#991B1B]">Hint: Look for dates and cause-effect relationships</span>
          </div>
        </div>
      )}
    </div>
  );
}
