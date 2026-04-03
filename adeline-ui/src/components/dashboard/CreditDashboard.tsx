"use client";

import { useEffect, useState } from "react";
import { getCreditDashboard, approveCourseProposal, listAvailableProfiles } from "@/lib/brain-client";
import type { CreditDashboard, OklahomaProfile } from "@/lib/brain-client";

interface Props {
  studentId: string;
}

export function CreditDashboardComponent({ studentId }: Props) {
  const [dashboard, setDashboard] = useState<CreditDashboard | null>(null);
  const [profiles, setProfiles] = useState<OklahomaProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [approvingProposalId, setApprovingProposalId] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setIsLoading(true);
        const [dashboardData, profilesData] = await Promise.all([
          getCreditDashboard(studentId),
          listAvailableProfiles(),
        ]);
        setDashboard(dashboardData);
        setProfiles(profilesData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load credit data");
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, [studentId]);

  const handleApproveProposal = async (proposalId: string) => {
    try {
      setApprovingProposalId(proposalId);
      await approveCourseProposal(studentId, proposalId);
      const updated = await getCreditDashboard(studentId);
      setDashboard(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve proposal");
    } finally {
      setApprovingProposalId(null);
    }
  };

  if (isLoading) return <div className="p-6 text-center">Loading credit data...</div>;
  if (error) return <div className="p-6 text-red-600">Error: {error}</div>;
  if (!dashboard) return <div className="p-6">No credit data available.</div>;

  const currentProfile = profiles.find((p) => p.key === dashboard.currentProfile);

  return (
    <div className="space-y-6 p-6">
      {/* Header section with portfolio info */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="text-2xl font-bold text-gray-900">Academic Portfolio</h2>
        <p className="mt-2 text-sm text-gray-600">
          Portfolio-first transcript. Credits are awarded for accomplishments: published work, projects completed, skills mastered.
        </p>
        {currentProfile && (
          <div className="mt-4 flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">Compliance Profile:</span>
            <span className="rounded-full bg-blue-100 px-3 py-1 text-sm text-blue-900">{currentProfile.name}</span>
          </div>
        )}
      </div>

      {/* Credit Buckets section with progress bars */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h3 className="text-lg font-semibold text-gray-900">Credit Accumulation by Bucket</h3>
        <div className="mt-4 space-y-4">
          {dashboard.buckets.map((bucket) => {
            return (
              <div key={bucket.bucket} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-900">{bucket.bucket}</span>
                  <span className="text-sm text-gray-600">
                    {bucket.hoursEarned.toFixed(1)} hours
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium">{bucket.masteryGrade}</span>
                  <span className="text-xs text-gray-600">({bucket.evidenceCount} pieces of evidence)</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Pending Proposals section with approve button */}
      {dashboard.pendingProposals.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="text-lg font-semibold text-gray-900">Pending Course Proposals</h3>
          <div className="mt-4 space-y-3">
            {dashboard.pendingProposals.map((proposal) => (
              <div key={proposal.proposalId} className="flex items-center justify-between rounded-lg border border-yellow-200 bg-yellow-50 p-4">
                <div>
                  <p className="font-medium text-gray-900">{proposal.courseName}</p>
                  <p className="text-sm text-gray-600">{proposal.track}</p>
                  <p className="mt-1 text-xs text-gray-500">{proposal.artifactCount} artifacts collected</p>
                </div>
                <button
                  onClick={() => handleApproveProposal(proposal.proposalId)}
                  disabled={approvingProposalId === proposal.proposalId}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {approvingProposalId === proposal.proposalId ? "Approving..." : "Approve"}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Approved Courses section */}
      {dashboard.approvedCourses.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="text-lg font-semibold text-gray-900">Official Transcript</h3>
          <div className="mt-4 space-y-3">
            {dashboard.approvedCourses.map((course) => (
              <div key={course.courseId} className="flex items-center justify-between rounded-lg border border-green-200 bg-green-50 p-4">
                <div>
                  <p className="font-medium text-gray-900">{course.courseName}</p>
                  <p className="text-sm text-gray-600">{course.track}</p>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-green-900">{course.credits.toFixed(1)} credit</p>
                  <p className="text-xs text-gray-500">Grade: {course.gradeLetter}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {dashboard.pendingProposals.length === 0 && dashboard.approvedCourses.length === 0 && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-6 text-center">
          <p className="text-gray-600">No courses yet. Complete learning activities to generate course proposals.</p>
        </div>
      )}
    </div>
  );
}
