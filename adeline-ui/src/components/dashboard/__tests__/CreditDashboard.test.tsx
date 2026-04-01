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
      bucketKey: "standard_courses",
      bucketLabel: "Standard Courses",
      threshold: 120,
      earnedHours: 45.5,
    },
    {
      bucketKey: "electives",
      bucketLabel: "Electives",
      threshold: 120,
      earnedHours: 120,
    },
  ],
  pendingProposals: [
    {
      proposalId: "prop-1",
      courseName: "Biology Project",
      track: "CREATION_SCIENCE",
      artifactCount: 3,
    },
  ],
  approvedCourses: [
    {
      courseId: "course-1",
      courseName: "Geometry Mastery",
      track: "APPLIED_MATHEMATICS",
      credits: 1.0,
      gradeLetter: "A",
    },
  ],
};

const mockProfiles = [
  { key: "flexible_homeschool", label: "Flexible Homeschool" },
  { key: "college_prep", label: "College Prep" },
  { key: "public_school_parity", label: "Public School Parity" },
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
    expect(screen.getByText("Credit Accumulation by Bucket")).toBeDefined();
    expect(screen.getByText("Standard Courses")).toBeDefined();
    expect(screen.getByText("Electives")).toBeDefined();
    expect(screen.getByText("45.5 / 120 hours")).toBeDefined();
    expect(screen.getByText("120 / 120 hours")).toBeDefined();

    // Check pending proposals
    expect(screen.getByText("Pending Course Proposals")).toBeDefined();
    expect(screen.getByText("Biology Project")).toBeDefined();
    expect(screen.getByText("CREATION_SCIENCE")).toBeDefined();

    // Check approved courses
    expect(screen.getByText("Official Transcript")).toBeDefined();
    expect(screen.getByText("Geometry Mastery")).toBeDefined();
    expect(screen.getByText("1.0 credit")).toBeDefined();
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
          courseId: "course-2",
          courseName: "Biology Project",
          track: "CREATION_SCIENCE",
          credits: 1.0,
          gradeLetter: "A",
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
