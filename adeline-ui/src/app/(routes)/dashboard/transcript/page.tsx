"use client";

import { useState } from "react";
import { OSRHEDashboard } from "@/components/transcript/OSRHEDashboard";
import { downloadOfficialTranscript, downloadMasteryPortfolio } from "@/lib/brain-client";
import { Download } from "lucide-react";
import { useAuth } from "@/lib/useAuth";

type TabType = "osrhe" | "official" | "portfolio";

export default function TranscriptPage() {
  const { user } = useAuth();
  const DEMO_STUDENT_ID = user?.id ?? '';
  const [activeTab, setActiveTab] = useState<TabType>("osrhe");
  const [downloadingOfficial, setDownloadingOfficial] = useState(false);
  const [downloadingPortfolio, setDownloadingPortfolio] = useState(false);

  const handleDownloadOfficial = async () => {
    try {
      setDownloadingOfficial(true);
      const blob = await downloadOfficialTranscript(DEMO_STUDENT_ID);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `official-transcript-${DEMO_STUDENT_ID}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Failed to download official transcript:", error);
      alert("Failed to download official transcript. Please try again.");
    } finally {
      setDownloadingOfficial(false);
    }
  };

  const handleDownloadPortfolio = async () => {
    try {
      setDownloadingPortfolio(true);
      const blob = await downloadMasteryPortfolio(DEMO_STUDENT_ID);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `mastery-portfolio-${DEMO_STUDENT_ID}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Failed to download mastery portfolio:", error);
      alert("Failed to download mastery portfolio. Please try again.");
    } finally {
      setDownloadingPortfolio(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Academic Transcript</h1>
          <p className="text-gray-600 mt-2">
            View your OSRHE progress, official transcript, and mastery portfolio
          </p>
        </div>

        {/* Tabs */}
        <div className="bg-white border-b border-gray-200 mb-6">
          <div className="flex gap-8">
            <button
              onClick={() => setActiveTab("osrhe")}
              className={`px-4 py-4 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "osrhe"
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-600 hover:text-gray-900"
              }`}
            >
              OSRHE Progress
            </button>
            <button
              onClick={() => setActiveTab("official")}
              className={`px-4 py-4 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "official"
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-600 hover:text-gray-900"
              }`}
            >
              Official Transcript
            </button>
            <button
              onClick={() => setActiveTab("portfolio")}
              className={`px-4 py-4 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "portfolio"
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-600 hover:text-gray-900"
              }`}
            >
              Mastery Portfolio
            </button>
          </div>
        </div>

        {/* Tab Content */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          {activeTab === "osrhe" && (
            <div>
              <OSRHEDashboard studentId={DEMO_STUDENT_ID} />
            </div>
          )}

          {activeTab === "official" && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-blue-900 text-sm">
                  Your official academic transcript formatted for college admissions.
                </p>
              </div>
              <button
                onClick={handleDownloadOfficial}
                disabled={downloadingOfficial}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
              >
                <Download className="w-4 h-4" />
                {downloadingOfficial ? "Downloading..." : "Download Official Transcript"}
              </button>
            </div>
          )}

          {activeTab === "portfolio" && (
            <div className="space-y-4">
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                <p className="text-purple-900 text-sm">
                  Your mastery portfolio showcasing accomplishments, projects, and evidence of learning.
                </p>
              </div>
              <button
                onClick={handleDownloadPortfolio}
                disabled={downloadingPortfolio}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 transition-colors"
              >
                <Download className="w-4 h-4" />
                {downloadingPortfolio ? "Downloading..." : "Download Mastery Portfolio"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
