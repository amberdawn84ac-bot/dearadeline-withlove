"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback } from "react";
import { ProjectGuide } from "@/components/projects/ProjectGuide";

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  // TODO: Replace with actual auth context
  const studentId = "demo-student-001";

  const handleSeal = useCallback(
    (_projectId: string) => {
      router.push("/dashboard/projects");
    },
    [router],
  );

  return (
    <div className="min-h-screen bg-[#FFFEF7] pb-12">
      <div className="max-w-2xl mx-auto px-6 py-8">
        {/* Back link */}
        <button
          onClick={() => router.push("/dashboard/projects")}
          className="text-sm text-[#2F4731]/50 hover:text-[#2F4731] mb-6 flex items-center gap-1"
        >
          ← Back to Projects
        </button>

        <ProjectGuide
          projectId={projectId}
          studentId={studentId}
          onSeal={handleSeal}
        />
      </div>
    </div>
  );
}
