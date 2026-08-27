import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EvidenceFooter } from "@/components/GenUIRenderer";
import type { Evidence } from "@/lib/brain-client";

describe("EvidenceFooter evidence contracts", () => {
  it("renders an authored archival citation without a Witness verdict or score", () => {
    const citation: Evidence = {
      source_title: "Pacific Railway Act (1862)",
      creator_or_issuer: "United States Congress",
      date: "July 1, 1862",
      holding_institution: "U.S. National Archives",
      source_url: "https://www.archives.gov/milestone-documents/pacific-railway-act",
      item_identifier: "General Records of the United States Government",
      excerpt_or_observable_feature: "The enacted land-grant and subsidy provisions.",
      claim_supported: "Congress materially supported transcontinental railroad construction.",
    };

    render(<EvidenceFooter evidence={[citation]} />);

    expect(screen.getByRole("link", { name: "Pacific Railway Act (1862)" })).toHaveAttribute(
      "href",
      citation.source_url,
    );
    expect(screen.getByText(/United States Congress/)).toBeInTheDocument();
    expect(screen.getByText(/U\.S\. National Archives/)).toBeInTheDocument();
    expect(screen.getByText(/General Records of the United States Government/)).toBeInTheDocument();
    expect(screen.queryByText(/% match/)).not.toBeInTheDocument();
  });

  it("preserves Witness Protocol verdict and similarity rendering", () => {
    const witness: Evidence = {
      source_id: "evidence-1",
      source_title: "Verified archive passage",
      source_url: "https://example.org/source",
      witness_citation: {
        author: "Archive Author",
        year: 1901,
        archive_name: "Example Archive",
      },
      similarity_score: 0.91,
      verdict: "VERIFIED",
      chunk: "Retrieved passage",
    };

    render(<EvidenceFooter evidence={[witness]} />);

    expect(screen.getByText(/VERIFIED/)).toBeInTheDocument();
    expect(screen.getByText("91% match")).toBeInTheDocument();
  });
});
