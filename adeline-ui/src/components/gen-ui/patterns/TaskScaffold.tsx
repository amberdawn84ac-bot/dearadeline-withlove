"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, Circle, Clock, ChevronDown, ChevronUp, Sparkles } from "lucide-react";

type Priority = "now" | "today" | "this_week";

export interface ScaffoldTask {
  id: string;
  text: string;
  priority: Priority;
  category?: string;
  estimated_minutes?: number;
}

export interface TaskScaffoldProps {
  title?: string;
  context?: string;
  tasks: ScaffoldTask[];
  onComplete?: () => void;
  onStateChange?: (state: Record<string, unknown>) => void;
  state?: Record<string, unknown>;
  callbacks?: string[];
}

const PRIORITY_CONFIG: Record<Priority, { label: string; color: string; bg: string; border: string }> = {
  now:       { label: "Do Now",    color: "#DC2626", bg: "#FEF2F2", border: "#FECACA" },
  today:     { label: "Today",     color: "#D97706", bg: "#FFFBEB", border: "#FDE68A" },
  this_week: { label: "This Week", color: "#2563EB", bg: "#EFF6FF", border: "#BFDBFE" },
};

export function TaskScaffold({
  title = "Action Plan",
  context,
  tasks,
  onComplete,
  onStateChange,
  state,
}: TaskScaffoldProps) {
  const [completed, setCompleted] = useState<Set<string>>(
    new Set((state?.completed as string[]) ?? [])
  );
  const [collapsed, setCollapsed] = useState<Set<Priority>>(new Set());

  const toggle = (id: string) => {
    setCompleted((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      onStateChange?.({ completed: Array.from(next) });
      if (next.size === tasks.length) onComplete?.();
      return next;
    });
  };

  const toggleCollapse = (p: Priority) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(p)) next.delete(p); else next.add(p);
      return next;
    });
  };

  const groups = (["now", "today", "this_week"] as Priority[])
    .map((p) => ({ priority: p, tasks: tasks.filter((t) => t.priority === p) }))
    .filter((g) => g.tasks.length > 0);

  const doneCount = tasks.filter((t) => completed.has(t.id)).length;
  const pct = tasks.length > 0 ? doneCount / tasks.length : 0;
  const allDone = doneCount === tasks.length && tasks.length > 0;

  return (
    <div className="rounded-2xl overflow-hidden" style={{ border: "1.5px solid #E5E7EB", background: "#FAFBFF" }}>
      {/* Header */}
      <div className="px-4 py-2.5" style={{ borderBottom: "1px solid #F3F4F6", background: "#F9FAFB" }}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5">
            <Sparkles size={12} className="text-[#6B7280]" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-[#374151]">{title}</span>
          </div>
          <span className="text-[10px] text-[#9CA3AF]">{doneCount}/{tasks.length} done</span>
        </div>
        <div className="h-1.5 rounded-full bg-[#E5E7EB] overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-emerald-500"
            animate={{ width: `${pct * 100}%` }}
            transition={{ type: "spring", stiffness: 120, damping: 20 }}
          />
        </div>
      </div>

      {context && (
        <div className="px-4 pt-3">
          <p className="text-[11px] text-[#6B7280] italic leading-relaxed">{context}</p>
        </div>
      )}

      <div className="px-4 py-3 space-y-3">
        {groups.map(({ priority, tasks: groupTasks }) => {
          const cfg = PRIORITY_CONFIG[priority];
          const isCollapsed = collapsed.has(priority);
          const groupDone = groupTasks.filter((t) => completed.has(t.id)).length;

          return (
            <div key={priority}>
              <button
                onClick={() => toggleCollapse(priority)}
                className="flex items-center justify-between w-full mb-1.5"
              >
                <div className="flex items-center gap-1.5">
                  <span
                    className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded"
                    style={{ background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}` }}
                  >
                    {cfg.label}
                  </span>
                  <span className="text-[10px] text-[#9CA3AF]">{groupDone}/{groupTasks.length}</span>
                </div>
                {isCollapsed
                  ? <ChevronDown size={12} className="text-[#9CA3AF]" />
                  : <ChevronUp size={12} className="text-[#9CA3AF]" />
                }
              </button>

              <AnimatePresence>
                {!isCollapsed && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden space-y-1.5"
                  >
                    {groupTasks.map((task) => {
                      const isDone = completed.has(task.id);
                      return (
                        <motion.button
                          key={task.id}
                          onClick={() => toggle(task.id)}
                          layout
                          className="flex items-start gap-2.5 w-full text-left px-3 py-2 rounded-lg transition-colors"
                          style={{
                            background: isDone ? "#F0FDF4" : "#fff",
                            border: `1px solid ${isDone ? "#BBF7D0" : "#F3F4F6"}`,
                          }}
                        >
                          {isDone
                            ? <CheckCircle2 size={15} className="text-emerald-500 shrink-0 mt-0.5" />
                            : <Circle size={15} className="text-[#D1D5DB] shrink-0 mt-0.5" />
                          }
                          <div className="flex-1 min-w-0">
                            <p className={`text-xs leading-snug ${isDone ? "line-through text-[#9CA3AF]" : "text-[#374151]"}`}>
                              {task.text}
                            </p>
                            {task.estimated_minutes && !isDone && (
                              <p className="text-[10px] text-[#9CA3AF] flex items-center gap-0.5 mt-0.5">
                                <Clock size={9} />~{task.estimated_minutes} min
                              </p>
                            )}
                          </div>
                        </motion.button>
                      );
                    })}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>

      {allDone && (
        <div
          className="px-4 py-2.5 flex items-center gap-1.5 text-[11px] font-semibold text-emerald-700"
          style={{ borderTop: "1px solid #BBF7D0", background: "#F0FDF4" }}
        >
          <CheckCircle2 size={12} />
          All tasks complete — great work!
        </div>
      )}
    </div>
  );
}
