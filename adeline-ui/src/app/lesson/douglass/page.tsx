/**
 * /lesson/douglass — Static showcase lesson: Frederick Douglass
 *
 * Pre-seeded PRIMARY_SOURCE blocks with VERIFIED verdicts so the
 * Verified Seal fires without a live adeline-brain connection.
 * Track: TRUTH_HISTORY — renders with Paradise border + Papaya accents.
 */

import LessonRenderer from "@/components/lessons/LessonRenderer";
import Link from "next/link";
import type { LessonResponse } from "@/lib/brain-client";

const DOUGLASS_LESSON: LessonResponse = {
  lesson_id: "static-douglass-001",
  title: "Frederick Douglass: Witness to Liberty",
  track: "TRUTH_HISTORY",
  has_research_missions: false,
  oas_standards: [
    {
      standard_id: "OK.US.H.5.4",
      text: "Analyze the causes, course, and consequences of the Civil War and Reconstruction.",
      grade: 8,
      lesson_hook:
        "Douglass's autobiography stands as a primary-source account of the institution this war was fought to end.",
    },
    {
      standard_id: "OK.ELA.RI.8.1",
      text: "Cite textual evidence that most strongly supports an analysis of what the text says explicitly.",
      grade: 8,
      lesson_hook:
        "Students cite Douglass's exact words to distinguish historical fact from interpretation.",
    },
  ],
  blocks: [
    {
      block_id: "blk-001",
      block_type: "PRIMARY_SOURCE",
      content:
        "I was born in Tuckahoe, near Hillsborough, and about twelve miles from Easton, in Talbot county, Maryland. I have no accurate knowledge of my age, never having seen any authentic record containing it. By far the larger part of the slaves know as little of their ages as horses know of theirs, and it is the wish of most masters within my knowledge to keep their slaves thus ignorant.",
      homestead_content: undefined,
      is_silenced: false,
      evidence: [
        {
          source_id: "src-narrative-douglass-1845",
          source_title: "Narrative of the Life of Frederick Douglass, an American Slave",
          source_url:
            "https://www.gutenberg.org/files/23/23-h/23-h.htm",
          witness_citation: {
            author: "Frederick Douglass",
            year: 1845,
            archive_name: "Project Gutenberg Public Domain Archive",
          },
          similarity_score: 0.9712,
          verdict: "VERIFIED",
          chunk:
            "I was born in Tuckahoe, near Hillsborough, and about twelve miles from Easton...",
        },
      ],
    },
    {
      block_id: "blk-002",
      block_type: "NARRATIVE",
      content:
        "Douglass was born enslaved in Maryland around 1818. He taught himself to read — an act that was illegal — and used literacy as the tool of his liberation. His 1845 Narrative became one of the most influential abolitionist documents in American history, read across the United States and Europe.",
      homestead_content: undefined,
      is_silenced: false,
      evidence: [],
    },
    {
      block_id: "blk-003",
      block_type: "PRIMARY_SOURCE",
      content:
        "The more I read, the more I was led to abhor and detest my enslavers. I could regard them in no other light than a band of successful robbers, who had left their homes, and gone to Africa, and stolen us from our homes, and in a strange land reduced us to slavery. I loathed them as being the meanest as well as the most wicked of men.",
      homestead_content: undefined,
      is_silenced: false,
      evidence: [
        {
          source_id: "src-narrative-douglass-1845-ch7",
          source_title: "Narrative of the Life of Frederick Douglass, an American Slave — Ch. VII",
          source_url:
            "https://www.gutenberg.org/files/23/23-h/23-h.htm",
          witness_citation: {
            author: "Frederick Douglass",
            year: 1845,
            archive_name: "Project Gutenberg Public Domain Archive",
          },
          similarity_score: 0.9541,
          verdict: "VERIFIED",
          chunk: "The more I read, the more I was led to abhor and detest my enslavers...",
        },
      ],
    },
    {
      block_id: "blk-004",
      block_type: "PRIMARY_SOURCE",
      content:
        "If there is no struggle, there is no progress. Those who profess to favor freedom, and yet deprecate agitation, are men who want crops without plowing up the ground. They want rain without thunder and lightning. They want the ocean without the awful roar of its many waters.",
      homestead_content: undefined,
      is_silenced: false,
      evidence: [
        {
          source_id: "src-douglass-1857-speech",
          source_title: "\"West India Emancipation\" speech, Canandaigua, New York",
          source_url:
            "https://rbscp.lib.rochester.edu/4398",
          witness_citation: {
            author: "Frederick Douglass",
            year: 1857,
            archive_name:
              "University of Rochester Rare Books, Special Collections & Preservation",
          },
          similarity_score: 0.9888,
          verdict: "VERIFIED",
          chunk: "If there is no struggle, there is no progress...",
        },
      ],
    },
  ],
};

export default function DouglassPage() {
  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 font-sketch text-xs text-fuschia/50">
        <Link href="/lesson" className="hover:text-paradise transition-colors">
          ← Back to Journal
        </Link>
        <span>/</span>
        <span className="text-paradise">Frederick Douglass</span>
      </nav>

      {/* Showcase notice */}
      <div
        className="border border-dashed border-papaya bg-parchment-100 px-4 py-2 flex items-center gap-3"
        style={{ borderWidth: "1.5px" }}
      >
        <span className="font-sketch text-xs text-papaya uppercase tracking-widest shrink-0">
          Showcase
        </span>
        <p className="font-body text-xs text-fuschia/60 leading-relaxed">
          This lesson is pre-seeded with verified primary sources. When adeline-brain is live,
          lessons generate dynamically from the Hippocampus archive.
        </p>
      </div>

      <LessonRenderer lesson={DOUGLASS_LESSON} showScores={false} />
    </div>
  );
}
