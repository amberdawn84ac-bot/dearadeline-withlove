"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { BookOpen, ChevronDown, ChevronUp, CheckCircle2 } from "lucide-react";

export interface TextSection {
  heading: string;
  content: string;
  expandable?: boolean;
}

export interface TextExplanationProps {
  title: string;
  sections: TextSection[];
  summary?: string;
  keyTerms?: { term: string; definition: string }[];
  track?: string;
  onComplete?: () => void;
  onStateChange?: (state: Record<string, unknown>) => void;
}

export function TextExplanation({
  title,
  sections,
  summary,
  keyTerms = [],
  track,
  onComplete,
  onStateChange,
}: TextExplanationProps) {
  const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set([0]));
  const [readSections, setReadSections] = useState<Set<number>>(new Set());
  const [completed, setCompleted] = useState(false);

  const themeColor = track === "ENGLISH_LITERATURE" ? "#4A3728" : "#2F4731";
  const accentColor = track === "ENGLISH_LITERATURE" ? "#8B6F47" : "#8BAE6B";

  const toggleSection = (index: number) => {
    const updated = new Set(expandedSections);
    if (updated.has(index)) {
      updated.delete(index);
    } else {
      updated.add(index);
      // Mark as read when expanded
      const readUpdated = new Set(readSections);
      readUpdated.add(index);
      setReadSections(readUpdated);
      onStateChange?.({ expandedSections: [...updated], readSections: [...readUpdated] });

      // Auto-complete when all sections read
      if (readUpdated.size === sections.length && !completed) {
        setCompleted(true);
        onComplete?.();
      }
    }
    setExpandedSections(updated);
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
          <BookOpen size={16} style={{ color: accentColor }} />
          <h3 className="font-semibold text-sm" style={{ color: themeColor }}>{title}</h3>
        </div>
        {completed && (
          <span className="flex items-center gap-1 text-xs font-medium" style={{ color: accentColor }}>
            <CheckCircle2 size={14} /> Read
          </span>
        )}
      </div>

      {/* Summary */}
      {summary && (
        <div className="px-5 py-3 border-b border-gray-100">
          <p className="text-sm text-gray-700 leading-relaxed italic">{summary}</p>
        </div>
      )}

      {/* Sections with progressive disclosure */}
      <div className="divide-y divide-gray-100">
        {sections.map((section, i) => (
          <div key={i} className="px-5">
            <button
              onClick={() => toggleSection(i)}
              className="w-full flex items-center justify-between py-3 text-left"
            >
              <span
                className="text-sm font-medium flex items-center gap-2"
                style={{ color: readSections.has(i) ? accentColor : themeColor }}
              >
                {readSections.has(i) && <CheckCircle2 size={12} />}
                {section.heading}
              </span>
              {section.expandable !== false && (
                expandedSections.has(i) ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />
              )}
            </button>
            {expandedSections.has(i) && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="pb-4"
              >
                <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-line">
                  {section.content}
                </p>
              </motion.div>
            )}
          </div>
        ))}
      </div>

      {/* Key terms */}
      {keyTerms.length > 0 && (
        <div className="px-5 py-3 border-t border-gray-100">
          <p className="text-xs font-medium text-gray-500 mb-2">Key Terms</p>
          <div className="space-y-1.5">
            {keyTerms.map((kt) => (
              <div key={kt.term} className="flex gap-2 text-xs">
                <span className="font-semibold shrink-0" style={{ color: themeColor }}>{kt.term}:</span>
                <span className="text-gray-600">{kt.definition}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}
