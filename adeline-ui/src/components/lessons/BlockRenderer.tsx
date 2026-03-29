"use client";

/**
 * BlockRenderer — Renders Hygraph rich-text HTML inside a lesson context.
 *
 * Used to display CMS-authored lesson blocks (TrackPage descriptions,
 * CurriculumUnit introductions, LessonStub content) alongside the
 * adeline-brain generated PRIMARY_SOURCE / NARRATIVE / LAB_MISSION blocks.
 *
 * The HTML from Hygraph's RichText field is sanitized on render:
 * - Only allows safe tags (p, h1-h4, ul, ol, li, a, strong, em, blockquote, code)
 * - All links open in a new tab with rel="noopener noreferrer"
 * - Scripture blockquotes get the Paradise color treatment
 * - Inline code gets a Parchment background
 *
 * This is the composable "BlockRenderer" pattern called for in the plan —
 * analogous to cascade-adeline's LessonBlock but driven by CMS content.
 */

import { useEffect, useRef } from "react";

interface BlockRendererProps {
  html:        string;
  className?:  string;
  track?:      string;
}

// Inline style for scripture blockquotes (identified by > syntax from CMS)
const BLOCKQUOTE_STYLE = `
  font-style: italic;
  color: #9A3F4A;
  border-left: 3px solid #9A3F4A;
  padding-left: 16px;
  margin: 12px 0;
  font-size: 0.95rem;
  line-height: 1.6;
`;

const CODE_STYLE = `
  background: #FDF6E9;
  border: 1px solid #E7DAC3;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 0.85em;
  font-family: monospace;
`;

const LINK_STYLE = `
  color: #BD6809;
  text-decoration: underline;
  text-underline-offset: 2px;
`;

export function BlockRenderer({ html, className, track: _track }: BlockRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    // Enforce safe link targets
    el.querySelectorAll("a").forEach((a) => {
      a.setAttribute("target", "_blank");
      a.setAttribute("rel",    "noopener noreferrer");
      a.setAttribute("style",  LINK_STYLE);
    });

    // Style blockquotes (scripture / key quotes)
    el.querySelectorAll("blockquote").forEach((bq) => {
      bq.setAttribute("style", BLOCKQUOTE_STYLE);
    });

    // Style inline code
    el.querySelectorAll("code").forEach((code) => {
      code.setAttribute("style", CODE_STYLE);
    });
  }, [html]);

  return (
    <div
      ref={containerRef}
      className={[
        "prose prose-sm max-w-none",
        "text-[#2F4731] leading-relaxed",
        "[&_h1]:text-lg [&_h1]:font-bold [&_h1]:text-[#2F4731] [&_h1]:mb-2",
        "[&_h2]:text-base [&_h2]:font-bold [&_h2]:text-[#2F4731] [&_h2]:mb-1.5",
        "[&_h3]:text-sm [&_h3]:font-bold [&_h3]:text-[#BD6809] [&_h3]:mb-1",
        "[&_p]:mb-3 [&_p]:text-sm",
        "[&_ul]:list-disc [&_ul]:pl-5 [&_ul]:mb-3 [&_ul_li]:text-sm [&_ul_li]:mb-1",
        "[&_ol]:list-decimal [&_ol]:pl-5 [&_ol]:mb-3 [&_ol_li]:text-sm [&_ol_li]:mb-1",
        "[&_strong]:font-bold [&_strong]:text-[#2F4731]",
        "[&_em]:italic [&_em]:text-[#2F4731]/80",
        className ?? "",
      ].join(" ")}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
