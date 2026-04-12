"use client";

/**
 * TextSelectionMenu — Ambient "Highlight & Ask" feature.
 *
 * Listens to browser text selection events and displays a floating menu
 * when text is highlighted within a lesson. Allows students to instantly
 * ask Adeline about the selected text without leaving context.
 *
 * Uses framer-motion for smooth appearance animations.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircleQuestion, Sparkles, X } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

interface SelectionPosition {
  x: number;
  y: number;
  width: number;
}

interface TextSelectionMenuProps {
  /** Container element to listen for selections within (defaults to document) */
  containerRef?: React.RefObject<HTMLElement>;
  /** Callback when user wants to ask about the selected text */
  onAskAboutSelection: (selectedText: string) => void;
  /** Optional: minimum characters to show the menu */
  minChars?: number;
  /** Optional: maximum characters to capture */
  maxChars?: number;
  /** Whether the menu is enabled */
  enabled?: boolean;
}

// ── TextSelectionMenu component ────────────────────────────────────────────────

export function TextSelectionMenu({
  containerRef,
  onAskAboutSelection,
  minChars = 10,
  maxChars = 500,
  enabled = true,
}: TextSelectionMenuProps) {
  const [selectedText, setSelectedText] = useState<string>("");
  const [position, setPosition] = useState<SelectionPosition | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Handle text selection
  const handleSelectionChange = useCallback(() => {
    if (!enabled) return;

    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) {
      // Small delay before hiding to allow click on menu
      setTimeout(() => {
        if (!menuRef.current?.contains(document.activeElement)) {
          setIsVisible(false);
        }
      }, 150);
      return;
    }

    const text = selection.toString().trim();
    
    // Check minimum length
    if (text.length < minChars) {
      setIsVisible(false);
      return;
    }

    // Check if selection is within our container (if specified)
    if (containerRef?.current) {
      const range = selection.getRangeAt(0);
      if (!containerRef.current.contains(range.commonAncestorContainer)) {
        setIsVisible(false);
        return;
      }
    }

    // Get position for the menu
    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    
    // Position menu above the selection, centered
    setPosition({
      x: rect.left + rect.width / 2,
      y: rect.top - 10,
      width: rect.width,
    });

    // Truncate if too long
    const truncatedText = text.length > maxChars 
      ? text.substring(0, maxChars) + "…" 
      : text;
    
    setSelectedText(truncatedText);
    setIsVisible(true);
  }, [enabled, minChars, maxChars, containerRef]);

  // Listen for selection changes
  useEffect(() => {
    document.addEventListener("selectionchange", handleSelectionChange);
    document.addEventListener("mouseup", handleSelectionChange);
    
    return () => {
      document.removeEventListener("selectionchange", handleSelectionChange);
      document.removeEventListener("mouseup", handleSelectionChange);
    };
  }, [handleSelectionChange]);

  // Handle ask button click
  const handleAsk = useCallback(() => {
    if (selectedText) {
      onAskAboutSelection(selectedText);
      setIsVisible(false);
      // Clear the selection
      window.getSelection()?.removeAllRanges();
    }
  }, [selectedText, onAskAboutSelection]);

  // Handle dismiss
  const handleDismiss = useCallback(() => {
    setIsVisible(false);
    window.getSelection()?.removeAllRanges();
  }, []);

  // Don't render if not visible or no position
  if (!isVisible || !position) return null;

  // Render via portal to avoid z-index issues
  return createPortal(
    <AnimatePresence>
      {isVisible && (
        <motion.div
          ref={menuRef}
          initial={{ opacity: 0, y: 10, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 5, scale: 0.95 }}
          transition={{ type: "spring", stiffness: 400, damping: 30 }}
          className="fixed z-[9999] flex items-center gap-1"
          style={{
            left: position.x,
            top: position.y,
            transform: "translate(-50%, -100%)",
          }}
        >
          {/* Main ask button */}
          <motion.button
            onClick={handleAsk}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="flex items-center gap-2 px-3 py-2 rounded-full shadow-lg border-2"
            style={{
              background: "linear-gradient(135deg, #2F4731, #3d5a40)",
              borderColor: "#BD6809",
              color: "#FFFEF7",
            }}
          >
            <MessageCircleQuestion className="w-4 h-4" />
            <span className="text-sm font-semibold whitespace-nowrap">
              Ask Adeline
            </span>
            <Sparkles className="w-3 h-3 text-[#BD6809]" />
          </motion.button>

          {/* Dismiss button */}
          <motion.button
            onClick={handleDismiss}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            className="w-6 h-6 rounded-full flex items-center justify-center shadow-md"
            style={{
              background: "#F3F0EA",
              color: "#2F4731",
            }}
          >
            <X className="w-3 h-3" />
          </motion.button>

          {/* Arrow pointer */}
          <div
            className="absolute left-1/2 -translate-x-1/2 w-3 h-3 rotate-45"
            style={{
              bottom: -6,
              background: "#2F4731",
              borderRight: "2px solid #BD6809",
              borderBottom: "2px solid #BD6809",
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  );
}

// ── Hook for easier integration ────────────────────────────────────────────────

interface UseTextSelectionReturn {
  selectedText: string | null;
  clearSelection: () => void;
}

export function useTextSelection(
  containerRef?: React.RefObject<HTMLElement>
): UseTextSelectionReturn {
  const [selectedText, setSelectedText] = useState<string | null>(null);

  useEffect(() => {
    const handleSelection = () => {
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed) {
        return;
      }

      const text = selection.toString().trim();
      if (text.length < 10) return;

      if (containerRef?.current) {
        const range = selection.getRangeAt(0);
        if (!containerRef.current.contains(range.commonAncestorContainer)) {
          return;
        }
      }

      setSelectedText(text);
    };

    document.addEventListener("mouseup", handleSelection);
    return () => document.removeEventListener("mouseup", handleSelection);
  }, [containerRef]);

  const clearSelection = useCallback(() => {
    setSelectedText(null);
    window.getSelection()?.removeAllRanges();
  }, []);

  return { selectedText, clearSelection };
}
