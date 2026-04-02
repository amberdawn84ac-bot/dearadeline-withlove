import React from "react";

type SourceType =
  | "PRIMARY_SOURCE"
  | "DECLASSIFIED_GOV"
  | "ARCHIVE_ORG"
  | "ACADEMIC_JOURNAL"
  | "PERSONAL_COLLECTION";

interface SourceBadgeProps {
  sourceType: SourceType;
  sourceTitle: string;
  sourceUrl?: string;
  citationYear?: number;
}

const BADGE_STYLES: Record<SourceType, string> = {
  PRIMARY_SOURCE: "bg-green-100 text-green-800",
  DECLASSIFIED_GOV: "bg-red-100 text-red-800",
  ARCHIVE_ORG: "bg-blue-100 text-blue-800",
  ACADEMIC_JOURNAL: "bg-purple-100 text-purple-800",
  PERSONAL_COLLECTION: "bg-gray-100 text-gray-800",
};

const BADGE_ICONS: Record<SourceType, string> = {
  PRIMARY_SOURCE: "\u{1F4C4}",      // 📄
  DECLASSIFIED_GOV: "\u{1F3DB}",    // 🏛️
  ARCHIVE_ORG: "\u{1F5C2}",         // 🗂️
  ACADEMIC_JOURNAL: "\u{1F4DA}",    // 📚
  PERSONAL_COLLECTION: "\u{1F4DD}", // 📝
};

const BADGE_LABELS: Record<SourceType, string> = {
  PRIMARY_SOURCE: "Primary Source",
  DECLASSIFIED_GOV: "Declassified Document",
  ARCHIVE_ORG: "Archive.org",
  ACADEMIC_JOURNAL: "Academic Journal",
  PERSONAL_COLLECTION: "Personal Collection",
};

export function SourceBadge({
  sourceType,
  sourceTitle,
  sourceUrl,
  citationYear,
}: SourceBadgeProps) {
  const style = BADGE_STYLES[sourceType] ?? BADGE_STYLES.PRIMARY_SOURCE;
  const icon = BADGE_ICONS[sourceType] ?? BADGE_ICONS.PRIMARY_SOURCE;
  const label = BADGE_LABELS[sourceType] ?? "Source";

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${style}`}
    >
      <span>{icon}</span>
      <span>{label}</span>
      {citationYear ? (
        <span className="text-xs opacity-75">({citationYear})</span>
      ) : null}
      {sourceUrl ? (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-1 underline hover:opacity-75"
          title={sourceTitle}
        >
          View source
        </a>
      ) : null}
    </div>
  );
}
