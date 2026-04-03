import { render, screen } from "@testing-library/react";
import SourceBadge from "@/components/SourceBadge";

describe("SourceBadge", () => {
  it("renders DECLASSIFIED_GOV badge correctly", () => {
    render(
      <SourceBadge
        sourceType="DECLASSIFIED_GOV"
        sourceTitle="NARA Document"
        sourceUrl="https://catalog.archives.gov/..."
        citationYear={1963}
      />
    );

    expect(screen.getByText("Declassified Document")).toBeInTheDocument();
    // citationYear is rendered as "(1963)" — match by content substring
    expect(screen.getByText("(1963)")).toBeInTheDocument();
  });

  it("renders PRIMARY_SOURCE badge with correct label", () => {
    render(
      <SourceBadge
        sourceType="PRIMARY_SOURCE"
        sourceTitle="Some Primary Document"
      />
    );

    expect(screen.getByText("Primary Source")).toBeInTheDocument();
  });

  it("renders ARCHIVE_ORG badge with view source link when URL provided", () => {
    render(
      <SourceBadge
        sourceType="ARCHIVE_ORG"
        sourceTitle="Archived Page"
        sourceUrl="https://archive.org/details/test"
        citationYear={2001}
      />
    );

    expect(screen.getByText("Archive.org")).toBeInTheDocument();
    expect(screen.getByText("View source")).toBeInTheDocument();
    expect(screen.getByText("(2001)")).toBeInTheDocument();
  });

  it("does not render view source link when sourceUrl is omitted", () => {
    render(
      <SourceBadge
        sourceType="ACADEMIC_JOURNAL"
        sourceTitle="A Journal Article"
      />
    );

    expect(screen.getByText("Academic Journal")).toBeInTheDocument();
    expect(screen.queryByText("View source")).not.toBeInTheDocument();
  });
});
