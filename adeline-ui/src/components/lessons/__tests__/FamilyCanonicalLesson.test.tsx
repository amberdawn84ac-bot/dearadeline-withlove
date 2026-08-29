import { render, screen, within } from "@testing-library/react";
import { fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import FamilyCanonicalLesson, { isV11FlowExperience } from "../FamilyCanonicalLesson";
import type { LessonBlockResponse, LessonResponse } from "@/lib/brain-client";

// GenUIRenderer pulls in framer-motion and the entire block-type component
// library — not the thing under test here. Replaced with a minimal stand-in
// that exposes exactly what these tests need to assert on: which blocks were
// passed, in what order, and how they were grouped by the caller.
vi.mock("@/components/GenUIRenderer", () => ({
  default: ({ blocks }: { blocks: LessonBlockResponse[] }) => (
    <div data-testid="genui-call">
      {blocks.map((block) => (
        <div key={block.block_id} data-testid={`block-${block.block_id}`} data-block-type={block.block_type}>
          {block.block_id}
        </div>
      ))}
    </div>
  ),
}));

const sealJournalMock = vi.fn();
vi.mock("@/lib/brain-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/brain-client")>("@/lib/brain-client");
  return {
    ...actual,
    sealJournal: (...args: unknown[]) => sealJournalMock(...args),
    downloadInvestigationPrintable: vi.fn(),
  };
});

function block(id: string, blockType: string, stage: LessonBlockResponse["experience_stage"]): LessonBlockResponse {
  return {
    block_id: id,
    block_type: blockType,
    content: `content for ${id}`,
    experience_stage: stage,
    evidence: [],
    is_silenced: false,
  };
}

const baseLessonFields = {
  lesson_id: "lesson-1",
  track: "CREATION_SCIENCE" as const,
  has_research_missions: false,
  researcher_activated: false,
  agent_name: "Canonical Experience Author",
  xapi_statements: [],
  credits_awarded: [],
  oas_standards: [],
};

describe("isV11FlowExperience", () => {
  it("is true only when format >= 11 AND a non-empty flow exists", () => {
    const withFlow: LessonResponse = {
      ...baseLessonFields,
      title: "Bread",
      blocks: [{ ...block("b1", "TEXT", "INVITATION"), canonical_format_version: 11 }],
      metadata: { experience_design: { layout: "lab_notebook", flow: [{ node_id: "a", label: "a", block_ids: ["b1"] }] } },
    };
    expect(isV11FlowExperience(withFlow)).toBe(true);
  });

  it("is false when format >= 11 but flow is empty", () => {
    const lesson: LessonResponse = {
      ...baseLessonFields,
      title: "Bread",
      blocks: [{ ...block("b1", "TEXT", "INVITATION"), canonical_format_version: 11 }],
      metadata: { experience_design: { layout: "lab_notebook", flow: [] } },
    };
    expect(isV11FlowExperience(lesson)).toBe(false);
  });

  it("is false when flow exists but format is below 11 (pre-flow canonical)", () => {
    const lesson: LessonResponse = {
      ...baseLessonFields,
      title: "Bread",
      blocks: [{ ...block("b1", "TEXT", "INVITATION"), canonical_format_version: 10 }],
      metadata: { experience_design: { layout: "lab_notebook", flow: [{ node_id: "a", label: "a", block_ids: ["b1"] }] } },
    };
    expect(isV11FlowExperience(lesson)).toBe(false);
  });

  it("is false for a plain legacy lesson with no experience_design at all", () => {
    const lesson: LessonResponse = {
      ...baseLessonFields,
      title: "Legacy",
      blocks: [block("b1", "TEXT", "INVITATION")],
      metadata: {},
    };
    expect(isV11FlowExperience(lesson)).toBe(false);
  });
});

describe("v11 flow rendering", () => {
  it("shows the shared family discussion before the learner's progression-based work", () => {
    const lesson: LessonResponse = {
      ...baseLessonFields,
      title: "Operation Public Record",
      blocks: [{ ...block("b1", "PRIMARY_SOURCE", "DISCOVERY"), canonical_format_version: 11 }],
      metadata: {
        family_discussion: {
          launch: "Place the supplied health record and pesticide-use record side by side.",
          questions: ["What is confirmed?", "What evidence is still missing?"],
          synthesis_prompt: "Bring each finding back to one family evidence board.",
        },
        learner_contribution: {
          role: "Graph observed and expected cases using your current statistics target.",
          prompt: "Explain what the graph can and cannot establish.",
          skill_connections: [{
            domain: "math", track: "APPLIED_MATHEMATICS", title: "Compare observed and expected rates",
            suggestion_id: "math-1", working_level: "current", contribution_prompt: "Build and explain the graph.",
            sequence_state: "READY", integration_status: "INTEGRATED",
            integration_rule: "Use only because the supplied records contain comparable quantities.",
            mastery_eligible: true,
          }],
        },
        experience_design: {
          layout: "dossier",
          central_question: "How should a community investigate possible harm?",
          flow: [{ node_id: "records", label: "Read the records", block_ids: ["b1"] }],
        },
      },
    };

    render(<FamilyCanonicalLesson lesson={lesson} studentId="student-1" />);

    const familyLaunch = screen.getByText("First, learn and examine together");
    const learnerWork = screen.getByText("Now, your part of the family investigation");
    expect(familyLaunch.compareDocumentPosition(learnerWork) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText("What is confirmed?")).toBeInTheDocument();
    expect(screen.getByText(/Graph observed and expected cases/)).toBeInTheDocument();
    expect(screen.getByText(/Bring each finding back/)).toBeInTheDocument();
  });

  it("renders in authored flow order, not stage order", () => {
    // Stage-bucket order would be INVITATION, DISCOVERY, ACTION, DEMONSTRATION
    // -> b2 (INVITATION), b1 (DISCOVERY), b3 (ACTION), b4 (DEMONSTRATION).
    // Flow deliberately orders b1 before b2, proving flow — not stage — wins.
    const blocks: LessonBlockResponse[] = [
      { ...block("b1", "TEXT", "DISCOVERY"), canonical_format_version: 11 },
      { ...block("b2", "TEXT", "INVITATION"), canonical_format_version: 11 },
      { ...block("b3", "EXPERIMENT", "ACTION"), canonical_format_version: 11 },
      { ...block("b4", "QUIZ", "DEMONSTRATION"), canonical_format_version: 11 },
    ];
    const lesson: LessonResponse = {
      ...baseLessonFields,
      title: "Kitchen Chemistry: Bread",
      blocks,
      metadata: {
        experience_design: {
          layout: "lab_notebook",
          central_question: "How does yeast turn dough into bread?",
          flow: [
            { node_id: "opening", label: "Two bowls, one question", block_ids: ["b1"] },
            { node_id: "learn", label: "What's happening in the dough", block_ids: ["b2"] },
            { node_id: "experiment", label: "Run the comparison", block_ids: ["b3", "b4"] },
          ],
        },
      },
    };

    render(<FamilyCanonicalLesson lesson={lesson} studentId="student-1" />);

    const ids = screen.getAllByTestId(/^block-/).map((el) => el.textContent);
    expect(ids).toEqual(["b1", "b2", "b3", "b4"]);
  });

  it("renders a multi-block flow node as one grouped step, not independent cards", () => {
    const blocks: LessonBlockResponse[] = [
      { ...block("b3", "EXPERIMENT", "ACTION"), canonical_format_version: 11 },
      { ...block("b4", "DATA_TRACKING", "ACTION"), canonical_format_version: 11 },
    ];
    const lesson: LessonResponse = {
      ...baseLessonFields,
      title: "Bread",
      blocks,
      metadata: {
        experience_design: {
          layout: "lab_notebook",
          flow: [{ node_id: "experiment", label: "Run the comparison", block_ids: ["b3", "b4"] }],
        },
      },
    };

    render(<FamilyCanonicalLesson lesson={lesson} studentId="student-1" />);

    const label = screen.getByText("Run the comparison");
    // Both blocks must live inside the same labeled step container.
    const step = label.closest("section");
    expect(step).not.toBeNull();
    expect(within(step as HTMLElement).getByTestId("block-b3")).toBeInTheDocument();
    expect(within(step as HTMLElement).getByTestId("block-b4")).toBeInTheDocument();
  });

  it("follows flow order even under an unknown/future layout, not stage order", () => {
    const blocks: LessonBlockResponse[] = [
      { ...block("b1", "TEXT", "DEMONSTRATION"), canonical_format_version: 11 }, // would sort last by stage
      { ...block("b2", "TEXT", "INVITATION"), canonical_format_version: 11 },    // would sort first by stage
    ];
    const lesson: LessonResponse = {
      ...baseLessonFields,
      title: "Some future experience",
      blocks,
      metadata: {
        experience_design: {
          layout: "some_future_layout_not_yet_supported",
          flow: [
            { node_id: "a", label: "First", block_ids: ["b1"] },
            { node_id: "b", label: "Second", block_ids: ["b2"] },
          ],
        },
      },
    };

    render(<FamilyCanonicalLesson lesson={lesson} studentId="student-1" />);

    const ids = screen.getAllByTestId(/^block-/).map((el) => el.textContent);
    expect(ids).toEqual(["b1", "b2"]);
  });

  it("does not render the legacy unconditional Your Contribution / What changed in your thinking UI", () => {
    const lesson: LessonResponse = {
      ...baseLessonFields,
      title: "Bread",
      blocks: [{ ...block("b1", "TEXT", "INVITATION"), canonical_format_version: 11 }],
      metadata: {
        experience_design: { layout: "lab_notebook", flow: [{ node_id: "a", label: "a", block_ids: ["b1"] }] },
      },
    };

    render(<FamilyCanonicalLesson lesson={lesson} studentId="student-1" />);

    expect(screen.queryByText("Your contribution")).not.toBeInTheDocument();
    expect(screen.queryByText("What changed in your thinking?")).not.toBeInTheDocument();
  });
});

describe("legacy (pre-v11) rendering is unchanged", () => {
  it("buckets blocks by experience_stage and shows the legacy sections", () => {
    const blocks: LessonBlockResponse[] = [
      block("b1", "TEXT", "INVITATION"),
      block("b2", "PRIMARY_SOURCE", "DISCOVERY"),
      block("b3", "EXPERIMENT", "ACTION"),
      block("b4", "QUIZ", "DEMONSTRATION"),
    ];
    const lesson: LessonResponse = {
      ...baseLessonFields,
      title: "Legacy lesson",
      blocks,
      metadata: {},
    };

    render(<FamilyCanonicalLesson lesson={lesson} studentId="student-1" />);

    // Legacy-only chrome must still be present.
    expect(screen.getByText("Clues and tools")).toBeInTheDocument();
    expect(screen.getByText("Your contribution")).toBeInTheDocument();
    expect(screen.getByText("What changed in your thinking?")).toBeInTheDocument();

    // Stage-bucket order: invitation, discovery, action, demonstration.
    const ids = screen.getAllByTestId(/^block-/).map((el) => el.textContent);
    expect(ids).toEqual(["b1", "b2", "b3", "b4"]);
  });

  it("also renders legacy for a v10-stamped canonical even if flow-shaped metadata is somehow present", () => {
    const lesson: LessonResponse = {
      ...baseLessonFields,
      title: "Stale cached canonical",
      blocks: [{ ...block("b1", "TEXT", "INVITATION"), canonical_format_version: 10 }],
      metadata: {
        experience_design: { layout: "lab_notebook", flow: [{ node_id: "a", label: "a", block_ids: ["b1"] }] },
      },
    };

    render(<FamilyCanonicalLesson lesson={lesson} studentId="student-1" />);

    expect(screen.getByText("Your contribution")).toBeInTheDocument();
  });
});

describe("sealing produces the same evidence payload shape regardless of renderer", () => {
  beforeEach(() => {
    sealJournalMock.mockReset();
    sealJournalMock.mockResolvedValue({
      sealed: true, lesson_id: "lesson-1", track: "CREATION_SCIENCE",
      track_progress: {}, learning_status: "UNDERSTANDING", credit_sealed: true,
    });
  });

  it("v11 seal call carries the same required fields as legacy", async () => {
    const lesson: LessonResponse = {
      ...baseLessonFields,
      title: "Bread",
      blocks: [
        { ...block("b1", "TEXT", "INVITATION"), canonical_format_version: 11 },
        { ...block("b2", "QUIZ", "DEMONSTRATION"), canonical_format_version: 11 },
      ],
      metadata: {
        concept_id: "concept-1",
        concept_name: "Fermentation",
        experience_design: {
          layout: "lab_notebook",
          flow: [
            { node_id: "a", label: "Opening", block_ids: ["b1"] },
            { node_id: "b", label: "Show what you found", block_ids: ["b2"] },
          ],
        },
      },
    };

    render(<FamilyCanonicalLesson lesson={lesson} studentId="student-1" />);

    const reflectionBox = screen.getByPlaceholderText(/I noticed… I tested…/);
    fireEvent.change(reflectionBox, { target: { value: "I noticed the yeasted dough rose much faster than the control." } });
    const saveButton = screen.getByRole("button", { name: /save this evidence/i });
    fireEvent.click(saveButton);

    await waitFor(() => expect(sealJournalMock).toHaveBeenCalledTimes(1));
    const [payload] = sealJournalMock.mock.calls[0];
    expect(payload).toMatchObject({
      lesson_id: "lesson-1",
      track: "CREATION_SCIENCE",
      completed_blocks: 2,
      concept_id: "concept-1",
      concept_name: "Fermentation",
      learner_reflection: "I noticed the yeasted dough rose much faster than the control.",
    });
    expect(payload).toHaveProperty("quiz_results");
    expect(payload).toHaveProperty("artifact_refs");
    expect(payload).toHaveProperty("evidence_sources");
    expect(payload).toHaveProperty("oas_standards");
  });
});
