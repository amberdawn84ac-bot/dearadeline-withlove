"use client";

import Link from "next/link";
import { useState } from "react";
import {
  Beaker,
  BookOpenCheck,
  Check,
  CheckCircle2,
  Download,
  FlaskConical,
  Loader2,
  Scale,
  Sparkles,
  ThermometerSun,
  Upload,
  Users,
} from "lucide-react";
import {
  completeBreadLesson,
  uploadActivityEvidence,
} from "@/lib/brain-client";
import type { BreadLessonCompletionResponse } from "@/lib/brain-client";
import { useStudent } from "@/lib/useStudent";

type AnswerMap = Record<string, string>;

const REVIEW_QUESTIONS = [
  {
    id: "yeast",
    question: "What is baker's yeast?",
    options: [
      ["living_fungus", "A living fungus"],
      ["chemical_powder", "A chemical powder that is not alive"],
      ["grain", "A kind of grain"],
    ],
  },
  {
    id: "gas",
    question: "Which gas makes the dough expand during fermentation?",
    options: [
      ["oxygen", "Oxygen"],
      ["carbon_dioxide", "Carbon dioxide"],
      ["nitrogen", "Nitrogen"],
    ],
  },
  {
    id: "gluten",
    question: "What is the gluten network doing while dough rises?",
    options: [
      ["traps_gas", "Stretching and trapping gas bubbles"],
      ["feeds_yeast", "Serving as the yeast's main food"],
      ["makes_heat", "Producing heat inside the dough"],
    ],
  },
  {
    id: "temperature",
    question: "Why does warm dough usually rise faster than cool dough?",
    options: [
      ["warm_speeds_yeast", "Warmth speeds yeast activity, until it becomes too hot"],
      ["warm_adds_gas", "Warmth adds carbon dioxide from the air"],
      ["warm_makes_flour", "Warmth turns water into flour"],
    ],
  },
  {
    id: "oven",
    question: "What does oven heat do to the dough?",
    options: [
      ["sets_structure_and_browns", "Sets the crumb structure and browns the crust"],
      ["keeps_fermenting", "Keeps the yeast fermenting for the whole bake"],
      ["removes_gluten", "Removes all gluten from the loaf"],
    ],
  },
  {
    id: "ratio",
    question: "How should every ingredient change when a recipe is doubled?",
    options: [
      ["proportional_scaling", "Multiply every ingredient by the same factor"],
      ["flour_only", "Double only the flour"],
      ["guess", "Add ingredients until the bowl looks full"],
    ],
  },
] as const;

const CONCEPTS = [
  {
    icon: FlaskConical,
    title: "Fermentation",
    text: "Yeast consumes available sugars and releases carbon dioxide and a small amount of ethanol.",
  },
  {
    icon: Sparkles,
    title: "Gas + structure",
    text: "Carbon dioxide inflates the dough while the stretchy gluten network holds the bubbles in place.",
  },
  {
    icon: ThermometerSun,
    title: "Temperature",
    text: "Warmth changes reaction rate. Too cool is slow; too hot can damage or kill the yeast.",
  },
  {
    icon: Scale,
    title: "Ratios",
    text: "A recipe is a proportional system. Scaling works only when every ingredient changes by the same factor.",
  },
];

export default function BreadKitchenChemistryLesson() {
  const { student, loading } = useStudent();
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [observations, setObservations] = useState("");
  const [nextTest, setNextTest] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<BreadLessonCompletionResponse | null>(null);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [evidenceUrl, setEvidenceUrl] = useState("");

  const answeredCount = Object.keys(answers).length;
  const ready = answeredCount === REVIEW_QUESTIONS.length
    && observations.trim().length >= 15
    && nextTest.trim().length >= 10;

  async function submitReview() {
    if (!student || !ready) return;
    setSubmitting(true);
    setError("");
    try {
      const completion = await completeBreadLesson({
        grade_level: student.gradeLevel ?? "8",
        answers,
        observations: observations.trim(),
        next_test: nextTest.trim(),
      });
      setResult(completion);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The registrar could not review this lesson yet.");
    } finally {
      setSubmitting(false);
    }
  }

  async function addPhoto(file?: File) {
    if (!file || !result?.sealed) return;
    setUploading(true);
    setError("");
    try {
      const evidence = await uploadActivityEvidence(result.activity_id, file);
      setEvidenceUrl(evidence.file_url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The photo could not be added yet.");
    } finally {
      setUploading(false);
    }
  }

  if (loading) {
    return <div className="p-12 text-center text-[#2F4731]/60">Setting the kitchen table…</div>;
  }
  if (!student) {
    return <div className="p-12 text-center text-[#2F4731]/60">Please sign in to open this family lesson.</div>;
  }

  return (
    <article className="pb-20 text-[#2F4731]">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <Link href="/dashboard" className="text-sm font-bold">← Back to today</Link>
        <a
          href="/workbooks/kitchen-chemistry-bread.pdf"
          download
          className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-[#2F4731] px-4 py-2 text-sm font-bold text-white"
        >
          <Download className="h-4 w-4" /> Printable family workbook
        </a>
      </div>

      <header className="overflow-hidden rounded-[30px] border border-[#D9CFBC] bg-[linear-gradient(135deg,#F5E6C8,#E3ECDD)] shadow-sm">
        <div className="grid gap-8 p-7 md:grid-cols-[1.2fr_.8fr] md:p-11">
          <div>
            <p className="text-xs font-black uppercase tracking-[.2em] text-[#A95322]">One shared family lesson · Kitchen chemistry</p>
            <h1 className="mt-3 text-5xl leading-[.95] text-[#2F4731] md:text-6xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>
              Bread: a living chemistry experiment
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-[#2F4731]/75">
              Mix one dough together, watch a living organism transform it, and explain how gas, protein, ratios, temperature, and heat become a loaf.
            </p>
          </div>
          <div className="rounded-[26px] border border-white/70 bg-white/70 p-6">
            <p className="text-xs font-black uppercase tracking-[.16em] text-[#BD6809]">The family question</p>
            <p className="mt-3 text-2xl leading-snug" style={{ fontFamily: "var(--font-kalam), cursive" }}>
              How can something too small to see fill a bowl with bubbles—and why do those bubbles stay?
            </p>
          </div>
        </div>
      </header>

      <section className="mt-6 grid gap-4 md:grid-cols-3" aria-label="Family learning levels">
        {[
          ["Younger learners", "Notice, touch, draw bubbles, and retell what changed."],
          ["Middle learners", "Measure, compare proofing conditions, and explain cause and effect."],
          ["Older learners", "Use baker's percentages and model anaerobic fermentation, protein structure, and heat transfer."],
        ].map(([title, text], index) => (
          <div key={title} className="rounded-2xl border border-[#E7DAC3] bg-white p-5">
            <div className="flex items-center gap-2 text-[#BD6809]"><Users className="h-4 w-4" /><span className="text-xs font-black uppercase tracking-wider">Layer {index + 1}</span></div>
            <h2 className="mt-3 text-lg font-bold">{title}</h2>
            <p className="mt-1 text-sm leading-6 text-[#2F4731]/65">{text}</p>
          </div>
        ))}
      </section>

      <section className="mt-6 rounded-[26px] border border-[#E7DAC3] bg-[#FFFEF7] p-6 md:p-8">
        <div className="flex items-center gap-3"><Beaker className="h-6 w-6 text-[#BD6809]" /><h2 className="text-3xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>Gather, predict, and stay safe</h2></div>
        <div className="mt-5 grid gap-6 md:grid-cols-2">
          <div>
            <h3 className="font-bold">For one simple loaf</h3>
            <ul className="mt-3 grid gap-2 text-sm leading-6 text-[#2F4731]/75">
              <li>• 500 g flour</li><li>• 350 g lukewarm water</li><li>• 10 g salt</li><li>• 5–7 g yeast</li><li>• Bowl, scale, spoon, towel, loaf pan or baking sheet</li>
            </ul>
          </div>
          <div className="rounded-2xl bg-[#FDF6E9] p-5">
            <h3 className="font-bold text-[#9A3F4A]">Adult checkpoint</h3>
            <p className="mt-2 text-sm leading-6 text-[#2F4731]/70">An adult handles the hot oven, hot pan, and any sharp tools. Check allergies before tasting. Warm water should feel comfortable—not hot—because high heat can kill yeast.</p>
            <p className="mt-4 text-sm font-bold">Predict together: What will the dough look, feel, and smell like after one hour?</p>
          </div>
        </div>
      </section>

      <section className="mt-6 rounded-[26px] border border-[#E7DAC3] bg-white p-6 md:p-8">
        <p className="text-xs font-black uppercase tracking-[.16em] text-[#BD6809]">The shared investigation</p>
        <h2 className="mt-2 text-3xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>Follow the transformation</h2>
        <ol className="mt-6 grid gap-4">
          {[
            ["1", "Measure the system", "Weigh every ingredient. Older learners calculate hydration: 350 g water ÷ 500 g flour = 70%."],
            ["2", "Mix and build structure", "Combine ingredients. Stretch a small piece: the developing gluten network is the dough's gas-holding scaffold."],
            ["3", "Watch fermentation", "Cover the bowl. Mark the starting height. Observe again after 20, 40, and 60 minutes; record bubbles, volume, smell, and texture."],
            ["4", "Change one variable", "If practical, divide the dough. Keep one sample warmer and one cooler. Change only temperature so the comparison means something."],
            ["5", "Shape and bake", "Shape gently, allow a final proof, then have an adult bake. Notice oven spring, crust color, aroma, and the crumb after cooling."],
          ].map(([number, title, text]) => (
            <li key={number} className="grid grid-cols-[44px_1fr] gap-4 rounded-2xl border border-[#E7DAC3] p-5">
              <span className="grid h-11 w-11 place-items-center rounded-full bg-[#2F4731] font-black text-white">{number}</span>
              <div><h3 className="font-bold">{title}</h3><p className="mt-1 text-sm leading-6 text-[#2F4731]/65">{text}</p></div>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-6">
        <h2 className="text-3xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>What the registrar will recognize</h2>
        <p className="mt-2 text-sm text-[#2F4731]/65">The final review checks demonstrated concepts—not how long you stood in the kitchen.</p>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          {CONCEPTS.map(({ icon: Icon, title, text }) => (
            <div key={title} className="rounded-2xl border border-[#D9CFBC] bg-[#F0FDF4] p-5">
              <Icon className="h-5 w-5 text-[#BD6809]" />
              <h3 className="mt-3 font-bold">{title}</h3>
              <p className="mt-1 text-sm leading-6 text-[#2F4731]/65">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-8 rounded-[30px] border-2 border-[#2F4731] bg-[#FFFEF7] p-6 md:p-9" aria-labelledby="bread-review-heading">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-black uppercase tracking-[.18em] text-[#BD6809]">Interactive finish</p>
            <h2 id="bread-review-heading" className="mt-2 text-4xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>Explain the loaf</h2>
            <p className="mt-2 text-sm leading-6 text-[#2F4731]/65">Answer at least five correctly and add your own observations. The server verifies the review before the registrar seals the record.</p>
          </div>
          <span className="rounded-full bg-[#E3ECDD] px-4 py-2 text-sm font-bold">{answeredCount}/{REVIEW_QUESTIONS.length} answered</span>
        </div>

        <div className="mt-7 grid gap-6">
          {REVIEW_QUESTIONS.map((question, index) => (
            <fieldset key={question.id} className="rounded-2xl border border-[#E7DAC3] p-5">
              <legend className="px-2 text-sm font-bold">{index + 1}. {question.question}</legend>
              <div className="mt-3 grid gap-2">
                {question.options.map(([value, label]) => {
                  const selected = answers[question.id] === value;
                  return (
                    <button
                      key={value}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => setAnswers((current) => ({ ...current, [question.id]: value }))}
                      className={`flex min-h-11 items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm transition ${selected ? "border-[#2F4731] bg-[#E3ECDD] font-bold" : "border-[#E7DAC3] bg-white hover:border-[#7C9A61]"}`}
                    >
                      <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full border ${selected ? "border-[#2F4731] bg-[#2F4731] text-white" : "border-[#B7B0A4]"}`}>{selected && <Check className="h-3 w-3" />}</span>
                      {label}
                    </button>
                  );
                })}
              </div>
            </fieldset>
          ))}
        </div>

        <div className="mt-7 grid gap-5 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-bold">
            What did your family actually observe?
            <textarea value={observations} onChange={(event) => setObservations(event.target.value)} rows={5} maxLength={1200} placeholder="Describe bubbles, rise, smell, texture, temperature, crust, or crumb—and connect an observation to a cause." className="rounded-xl border border-[#BFB5A3] bg-white p-4 font-normal leading-6 outline-none focus:border-[#2F4731]" />
          </label>
          <label className="grid gap-2 text-sm font-bold">
            What would you change in the next loaf?
            <textarea value={nextTest} onChange={(event) => setNextTest(event.target.value)} rows={5} maxLength={800} placeholder="Change one variable: temperature, hydration, proofing time, flour, salt, kneading, or shaping. Predict the result." className="rounded-xl border border-[#BFB5A3] bg-white p-4 font-normal leading-6 outline-none focus:border-[#2F4731]" />
          </label>
        </div>

        {error && <p className="mt-5 rounded-xl bg-red-50 p-4 text-sm font-bold text-red-700" role="alert">{error}</p>}

        {!result && (
          <button type="button" onClick={() => void submitReview()} disabled={!ready || submitting} className="mt-6 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#BD6809] px-5 py-3 font-black text-white disabled:cursor-not-allowed disabled:opacity-45 md:w-auto">
            {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <BookOpenCheck className="h-5 w-5" />}
            {submitting ? "Registrar is reviewing…" : "Review concepts & create portfolio entry"}
          </button>
        )}

        {result && (
          <div className={`mt-7 rounded-2xl border p-6 ${result.sealed ? "border-[#166534] bg-[#F0FDF4]" : "border-[#BD6809] bg-[#FFF7ED]"}`}>
            <div className="flex items-start gap-3">
              {result.sealed ? <CheckCircle2 className="mt-0.5 h-6 w-6 shrink-0 text-[#166534]" /> : <Sparkles className="mt-0.5 h-6 w-6 shrink-0 text-[#BD6809]" />}
              <div>
                <h3 className="text-lg font-bold">{result.sealed ? "Portfolio entry created" : "Learning verified; record save pending"}</h3>
                <p className="mt-1 text-sm leading-6 text-[#2F4731]/70">{result.adeline_note}</p>
                <p className="mt-3 text-xs font-black uppercase tracking-wider text-[#2F4731]/55">Review score {result.score_percent}% · Creation Science · Applied Mathematics</p>
              </div>
            </div>
            {result.sealed && (
              <div className="mt-5 flex flex-wrap gap-3">
                <Link href="/dashboard/portfolio" className="inline-flex min-h-11 items-center rounded-xl bg-[#2F4731] px-4 py-2 text-sm font-bold text-white">Open portfolio →</Link>
                {!evidenceUrl ? (
                  <label className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-xl border border-[#2F4731] bg-white px-4 py-2 text-sm font-bold">
                    {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                    {uploading ? "Adding loaf photo…" : "Add a loaf photo"}
                    <input type="file" accept="image/*" className="sr-only" disabled={uploading} onChange={(event) => void addPhoto(event.target.files?.[0])} />
                  </label>
                ) : <span className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-bold text-[#166534]"><CheckCircle2 className="h-4 w-4" /> Photo attached</span>}
              </div>
            )}
          </div>
        )}
      </section>
    </article>
  );
}
