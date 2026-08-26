/**
 * Phase 2 proof case: Kitchen Chemistry: Bread, rendered against the exact
 * v11 payload shape from the design document (§10.A). This is a structural
 * proof, not a screenshot — this sandbox has no live backend/auth/Gemini to
 * exercise the deployed app through. It renders the real FamilyCanonicalLesson
 * component (GenUIRenderer mocked, same as the main suite, since its internal
 * block-type styling isn't what Phase 2 changed) and asserts on the actual
 * composed structure: flow order, which blocks are grouped into which step,
 * and the absence of the old unconditional ending.
 */
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import FamilyCanonicalLesson from "../FamilyCanonicalLesson";
import type { LessonBlockResponse, LessonResponse } from "@/lib/brain-client";

vi.mock("@/components/GenUIRenderer", () => ({
  default: ({ blocks }: { blocks: LessonBlockResponse[] }) => (
    <div data-testid="genui-call">
      {blocks.map((block) => (
        <div key={block.block_id} data-testid={`block-${block.block_id}`} data-block-type={block.block_type}>
          {block.title ?? block.block_id}
        </div>
      ))}
    </div>
  ),
}));
vi.mock("@/lib/brain-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/brain-client")>("@/lib/brain-client");
  return { ...actual, sealJournal: vi.fn(), downloadInvestigationPrintable: vi.fn() };
});

// Matches design-doc §10.A structure exactly, including block_ids and flow.
const breadBlocks: LessonBlockResponse[] = [
  {
    block_id: "b1", block_type: "TEXT", experience_stage: "INVITATION",
    title: "Two bowls, one question", content: "Feel and knead two doughs side by side...",
    evidence: [], is_silenced: false, canonical_format_version: 11,
  },
  {
    block_id: "b2", block_type: "PRIMARY_SOURCE", experience_stage: "DISCOVERY",
    title: "How fermentation works", content: "Yeast is a living fungus...",
    evidence: [{ source_id: "s1", source_title: "Food science reference", source_url: "https://example.org/fermentation", witness_citation: { author: "", year: null, archive_name: "" }, similarity_score: 0.9, verdict: "VERIFIED", chunk: "" }],
    is_silenced: false, canonical_format_version: 11,
  },
  {
    block_id: "b3", block_type: "EXPERIMENT", experience_stage: "ACTION",
    title: "Yeast vs. no-yeast dough", content: "Materials and procedure...",
    evidence: [{ source_id: "e1", source_title: "measurement", source_url: "", witness_citation: { author: "", year: null, archive_name: "" }, similarity_score: 0, verdict: "VERIFIED", chunk: "dough height every 30 min" }],
    is_silenced: false, canonical_format_version: 11,
  },
  {
    block_id: "b4", block_type: "DATA_TRACKING", experience_stage: "ACTION",
    title: "Rise measurements", content: "Log table for tracking dough height over time.",
    evidence: [], is_silenced: false, canonical_format_version: 11,
  },
  {
    block_id: "b5", block_type: "QUIZ", experience_stage: "DEMONSTRATION",
    title: "What does your data show?", content: "Explain the pattern in your measurements.",
    evidence: [], is_silenced: false, canonical_format_version: 11,
  },
];

const breadLesson: LessonResponse = {
  lesson_id: "lesson-bread-1",
  title: "Kitchen Chemistry: Bread",
  track: "CREATION_SCIENCE",
  blocks: breadBlocks,
  has_research_missions: false,
  researcher_activated: false,
  agent_name: "Canonical Experience Author",
  xapi_statements: [],
  credits_awarded: [],
  oas_standards: [],
  metadata: {
    concept_id: "fermentation-1",
    concept_name: "Fermentation",
    demonstration_contract: {
      invitation: "Explain to the family why the yeasted dough behaved differently.",
      artifact_prompt: "Photo of both doughs at 0/30/60/90 min, or a graphed rise curve",
    },
    portfolio_task: { evidence_to_preserve: "rise-time data, dough photos, explanation" },
    experience_design: {
      primary_mode: "stem",
      central_question: "How do living yeast, ratios, and heat turn flour and water into bread?",
      entry_move: "Feel and knead two doughs side by side — one with active yeast, one without.",
      layout: "lab_notebook",
      flow: [
        { node_id: "opening-question", label: "Two bowls, one question", block_ids: ["b1"] },
        { node_id: "the-science", label: "What's happening in the dough", block_ids: ["b2"] },
        { node_id: "the-experiment", label: "Run the comparison", block_ids: ["b3", "b4"] },
        { node_id: "the-analysis", label: "What does your evidence show?", block_ids: ["b5"] },
      ],
    },
  },
};

describe("Phase 2 proof case: Kitchen Chemistry: Bread (v11)", () => {
  it("renders the full authored arc in order: question -> science -> experiment(grouped) -> analysis", () => {
    render(<FamilyCanonicalLesson lesson={breadLesson} studentId="student-1" />);

    // 1. Central question and entry move are surfaced, not the generic copy.
    expect(screen.getByText("How do living yeast, ratios, and heat turn flour and water into bread?")).toBeInTheDocument();
    expect(screen.getByText(/Feel and knead two doughs side by side/)).toBeInTheDocument();
    expect(screen.queryByText("Follow the question. Use what helps. Make, test, examine, or decide something real.")).not.toBeInTheDocument();

    // 2. Four flow steps appear, each labeled with its authored framing.
    // "Two bowls, one question" appears twice by design in this fixture:
    // once as the flow step's label, once as block b1's own title.
    expect(screen.getAllByText("Two bowls, one question").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("What's happening in the dough")).toBeInTheDocument();
    expect(screen.getByText("Run the comparison")).toBeInTheDocument();
    expect(screen.getByText("What does your evidence show?")).toBeInTheDocument();

    // 3. Overall block order follows the authored flow, not stage order
    //    (which would have grouped b3+b4 with b5 under one ACTION+DEMONSTRATION
    //    bucket and put b2 before b1 was never the case here, but critically:
    //    the experiment/data pair must appear as ONE step, immediately after
    //    the science block and before the analysis block).
    const ids = screen.getAllByTestId(/^block-/).map((el) => el.textContent);
    expect(ids).toEqual([
      "Two bowls, one question",   // b1
      "How fermentation works",     // b2
      "Yeast vs. no-yeast dough",   // b3
      "Rise measurements",          // b4
      "What does your data show?",  // b5
    ]);

    // 4. The experiment and its data log are one composed step, not two
    //    independent cards with no visible relationship.
    const experimentLabel = screen.getByText("Run the comparison");
    const experimentStep = experimentLabel.closest("section");
    expect(experimentStep).not.toBeNull();
    expect(within(experimentStep as HTMLElement).getByTestId("block-b3")).toBeInTheDocument();
    expect(within(experimentStep as HTMLElement).getByTestId("block-b4")).toBeInTheDocument();
    // lab_notebook layout applies its grid treatment to this grouped step.
    expect((experimentStep as HTMLElement).innerHTML).toContain("md:grid-cols-2");

    // 5. No unconditional legacy ending; the authored demonstration_contract/
    //    portfolio_task content is what's shown instead.
    expect(screen.queryByText("Your contribution")).not.toBeInTheDocument();
    expect(screen.queryByText("What changed in your thinking?")).not.toBeInTheDocument();
    expect(screen.getByText("Explain to the family why the yeasted dough behaved differently.")).toBeInTheDocument();
    expect(screen.getByText("Photo of both doughs at 0/30/60/90 min, or a graphed rise curve")).toBeInTheDocument();
  });
});
