"use client";

import { useEffect, useState } from "react";
import { getOSRHEProgress, OSRHEProgress, OSRHEBucket } from "@/lib/brain-client";

interface Props {
  studentId: string;
}

const BUCKET_COLORS: Record<OSRHEBucket, string> = {
  ENGLISH: "#9A3F4A",
  LAB_SCIENCE: "#2F4731",
  MATH: "#BD6809",
  SOCIAL_STUDIES: "#3D1419",
  ELECTIVE: "#6B7280",
};

const BUCKET_LABELS: Record<OSRHEBucket, string> = {
  ENGLISH: "English",
  LAB_SCIENCE: "Lab Science",
  MATH: "Mathematics",
  SOCIAL_STUDIES: "Social Studies",
  ELECTIVE: "Elective",
};

export function OSRHEDashboard({ studentId }: Props) {
  const [data, setData] = useState<OSRHEProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProgress = async () => {
      try {
        setLoading(true);
        const progress = await getOSRHEProgress(studentId);
        setData(progress);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load OSRHE progress");
        setData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchProgress();
  }, [studentId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading OSRHE progress...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <p className="text-gray-600">No OSRHE data available</p>
      </div>
    );
  }

  const overallPercent = data.totalRequired > 0
    ? Math.round((data.totalEarned / data.totalRequired) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Overall Progress */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Overall Progress</h3>
        <div className="space-y-3">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Credits Earned / Required</span>
            <span className="font-semibold text-gray-900">
              {data.totalEarned} / {data.totalRequired}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
            <div
              className="bg-gradient-to-r from-blue-500 to-blue-600 h-full rounded-full transition-all duration-300"
              style={{ width: `${Math.min(overallPercent, 100)}%` }}
            />
          </div>
          <div className="text-right text-sm font-semibold text-gray-700">
            {overallPercent}% Complete
          </div>
        </div>
      </div>

      {/* Bucket Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.buckets.map((bucket) => {
          const bucketPercent = bucket.required > 0
            ? Math.round((bucket.earned / bucket.required) * 100)
            : 0;
          const bucketColor = BUCKET_COLORS[bucket.bucket];

          return (
            <div
              key={bucket.bucket}
              className="bg-white border border-gray-200 rounded-lg p-5"
            >
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-base font-semibold text-gray-900">
                  {bucket.label}
                </h4>
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: bucketColor }}
                  />
                </div>
              </div>

              <div className="space-y-2 mb-3">
                <div className="flex justify-between text-sm text-gray-600">
                  <span>Credits</span>
                  <span className="font-semibold text-gray-900">
                    {bucket.earned} / {bucket.required}
                  </span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                      width: `${Math.min(bucketPercent, 100)}%`,
                      backgroundColor: bucketColor,
                    }}
                  />
                </div>
                <div className="text-right text-xs font-medium text-gray-600">
                  {bucketPercent}% Complete
                </div>
              </div>

              <div className="pt-3 border-t border-gray-100 flex justify-between text-xs text-gray-500">
                <span>{bucket.hoursEarned} hours earned</span>
                <span>{bucket.evidenceCount} evidence items</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
