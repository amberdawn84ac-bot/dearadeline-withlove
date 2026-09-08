import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CreditDashboardComponent } from "../CreditDashboard";
import * as brainClient from "@/lib/brain-client";

vi.mock("@/lib/brain-client");

const mockCreditDashboard = {
  studentId: "student-123",
  currentProfile: "college_prep",
  buckets: [
    {
      bucket: "Standard Courses",
      hoursEarned: 45.5,
      evidenceCount: 4,
      masteryAverage: 0.8,
      masteryGrade: "B",
      creditEarned: null,
    },
    {
      bucket: "Electives",
      hoursEarned: 120,
      evidenceCount: 8,
      masteryAverage: 1,
      masteryGrade: "A",
      creditEarned: 1,
    },
  ],
  pendingProposals: [
    {
      proposalId: "prop-1",
      bucket: "Science",
      externalCourseName: "Biology Project",
      hoursEarned: 30,
      masteryPercentage: 90,
      masteryGrade: "A",
      isApproved: false,
      proposedAt: "2026-01-01T00:00:00Z",
    },
  ],
  approvedCourses: [
    {
      proposalId: "course-1",
      bucket: "Mathematics",
      externalCourseName: "Geometry Mastery",
      hoursEarned: 1,
      masteryPercentage: 95,
      masteryGrade: "A",
      isApproved: true,
      proposedAt: "2026-01-01T00:00:00Z",
    },
  ],
};

const mockProfiles = [
  { key: "flexible_homeschool", name: "Flexible Homeschool", description: "", oasOptional: true },
  { key: "college_prep", name: "College Prep", description: "", oasOptional: false },
  { key: "public_school_parity", name: "Public School Parity", description: "", oasOptional: false },
];

describe("CreditDashboardComponent", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should display loading state initially", () => {
    (brainClient.getCreditDashboard as any).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );
    (brainClient.listAvailableProfiles as any).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<CreditDashboardComponent studentId="student-123" />);

    expect(screen.getByText("Loading credit data...")).toBeDefined();
  });

  it("should render dashboard data after loading", async () => {
    (brainClient.getCreditDashboard as any).mockResolvedValue(mockCreditDashboard);
    (brainClient.listAvailableProfiles as any).mockResolvedValue(mockProfiles);

    render(<CreditDashboardComponent studentId="student-123" />);

    await waitFor(() => {
      expect(screen.getByText("Academic Portfolio")).toBeDefined();
    });

    // Check header section
    expect(screen.getByText("College Prep")).toBeDefined();

    // Check credit buckets
    expect(screen.getByText("Mastery Evidence by Bucket")).toBeDefined();
    expect(screen.getByText("Standard Courses")).toBeDefined();
    expect(screen.getByText("Electives")).toBeDefined();
    expect(screen.getByText("45.5 conventional hours")).toBeDefined();
    expect(screen.getByText("120.0 conventional hours")).toBeDefined();

    // Check pending proposals
    expect(screen.getByText("Pending Course Proposals")).toBeDefined();
    expect(screen.getByText("Biology Project")).toBeDefined();
    expect(screen.getByText("Science")).toBeDefined();

    // Check approved courses
    expect(screen.getByText("Official Transcript")).toBeDefined();
    expect(screen.getByText("Geometry Mastery")).toBeDefined();
    expect(screen.getByText("1 conventional hours")).toBeDefined();
  });

  it("should handle approve proposal button click", async () => {
    (brainClient.getCreditDashboard as any).mockResolvedValue(mockCreditDashboard);
    (brainClient.listAvailableProfiles as any).mockResolvedValue(mockProfiles);
    (brainClient.approveCourseProposal as any).mockResolvedValue(undefined);

    const updatedDashboard = {
      ...mockCreditDashboard,
      pendingProposals: [],
      approvedCourses: [
        ...mockCreditDashboard.approvedCourses,
        {
          proposalId: "course-2",
          bucket: "Science",
          externalCourseName: "Biology Project",
          hoursEarned: 30,
          masteryPercentage: 90,
          masteryGrade: "A",
          isApproved: true,
          proposedAt: "2026-01-01T00:00:00Z",
        },
      ],
    };

    (brainClient.getCreditDashboard as any).mockResolvedValueOnce(mockCreditDashboard);
    (brainClient.getCreditDashboard as any).mockResolvedValueOnce(updatedDashboard);

    const user = userEvent.setup();
    render(<CreditDashboardComponent studentId="student-123" />);

    await waitFor(() => {
      expect(screen.getByText("Biology Project")).toBeDefined();
    });

    const approveButton = screen.getByText("Approve");
    await user.click(approveButton);

    await waitFor(() => {
      expect(brainClient.approveCourseProposal).toHaveBeenCalledWith("student-123", "prop-1");
    });

    await waitFor(() => {
      expect(screen.getByText("Biology Project")).toBeDefined();
      // The component should have refreshed the dashboard
      expect(brainClient.getCreditDashboard).toHaveBeenCalledTimes(2);
    });
  });
});
