/**
 * /style-guide — Sketchnote Palette smoke test.
 * Verifies Papaya / Paradise / Fuschia are correctly wired in tailwind.config.ts.
 * Safe to delete once the design system is confirmed.
 */
import VerifiedSeal from "@/components/icons/VerifiedSeal";
import ArchiveSilent from "@/components/lessons/ArchiveSilent";
import { getTruthStatus, TRUTH_STATUS_META } from "@/lib/utils";
import { Wildflower, Butterfly, Bee, Ladybug, MasonJar, Acorn, HeartMagnifier, BotanicalDivider } from "@/components/icons";
import Investigating from "@/components/lessons/Investigating";

export default function StyleGuidePage() {
  return (
    <div className="space-y-10 py-8">

      {/* Header */}
      <div>
        <h1 className="font-sketch text-3xl text-fuschia">Sketchnote Style Guide</h1>
        <p className="font-body text-sm text-fuschia/70 mt-1">
          Dear Adeline 2.0 — visual smoke test
        </p>
      </div>

      {/* ── Color Swatches ─────────────────────────────────── */}
      <section className="space-y-3">
        <h2 className="font-sketch text-xl text-fuschia">Primary Palette</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">

          <div className="sketch-card space-y-2">
            <div className="h-24 bg-papaya rounded-sm" />
            <p className="font-sketch text-fuschia">Papaya</p>
            <p className="font-mono text-xs text-fuschia/60">#BD6809</p>
            <div className="flex gap-2">
              <div className="h-6 w-6 rounded-sm bg-papaya-light" title="papaya-light #D4820F" />
              <div className="h-6 w-6 rounded-sm bg-papaya" title="papaya #BD6809" />
              <div className="h-6 w-6 rounded-sm bg-papaya-dark" title="papaya-dark #9A5507" />
            </div>
          </div>

          <div className="sketch-card space-y-2">
            <div className="h-24 bg-paradise rounded-sm" />
            <p className="font-sketch text-fuschia">Paradise</p>
            <p className="font-mono text-xs text-fuschia/60">#9A3F4A</p>
            <div className="flex gap-2">
              <div className="h-6 w-6 rounded-sm bg-paradise-light" title="paradise-light #B04A57" />
              <div className="h-6 w-6 rounded-sm bg-paradise" title="paradise #9A3F4A" />
              <div className="h-6 w-6 rounded-sm bg-paradise-dark" title="paradise-dark #7D333D" />
            </div>
          </div>

          <div className="sketch-card space-y-2">
            <div className="h-24 bg-fuschia rounded-sm" />
            <p className="font-sketch text-fuschia">Fuschia</p>
            <p className="font-mono text-xs text-fuschia/60">#3D1419</p>
            <div className="flex gap-2">
              <div className="h-6 w-6 rounded-sm bg-fuschia-light" title="fuschia-light #52202A" />
              <div className="h-6 w-6 rounded-sm bg-fuschia" title="fuschia #3D1419" />
              <div className="h-6 w-6 rounded-sm bg-fuschia-dark" title="fuschia-dark #2A0D12" />
            </div>
          </div>

        </div>
      </section>

      {/* ── Muted Jewel Tones ──────────────────────────────── */}
      <section className="space-y-3">
        <h2 className="font-sketch text-xl text-fuschia">Muted Jewel Tones</h2>
        <p className="font-body text-sm text-fuschia/60">Track-aligned companions — dusty, field-pressed, nothing synthetic.</p>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {[
            { cls: "bg-sage",  hex: "#6B7F5E", label: "Sage",  role: "Creation / Homestead" },
            { cls: "bg-slate", hex: "#4A5E72", label: "Slate", role: "Gov / Justice" },
            { cls: "bg-plum",  hex: "#6B4E6B", label: "Plum",  role: "Discipleship" },
            { cls: "bg-ochre", hex: "#8C6D3F", label: "Ochre", role: "Health / Lab" },
            { cls: "bg-ink",   hex: "#2C2318", label: "Ink",   role: "Deep neutral" },
          ].map((s) => (
            <div key={s.label} className="sketch-card space-y-1 text-center">
              <div className={`h-14 rounded-sm ${s.cls}`} />
              <p className="font-sketch text-sm text-fuschia">{s.label}</p>
              <p className="font-mono text-xs text-fuschia/50">{s.hex}</p>
              <p className="font-body text-xs text-fuschia/40 italic">{s.role}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Parchment Tones ────────────────────────────────── */}
      <section className="space-y-3">
        <h2 className="font-sketch text-xl text-fuschia">Parchment Tones</h2>
        <div className="grid grid-cols-4 gap-3">
          {[
            { cls: "bg-parchment-50",  hex: "#FDF8F0", label: "50" },
            { cls: "bg-parchment-100", hex: "#F9EDD8", label: "100" },
            { cls: "bg-parchment-200", hex: "#F0D9B0", label: "200" },
            { cls: "bg-parchment-300", hex: "#E3C07A", label: "300" },
          ].map((s) => (
            <div key={s.label} className="sketch-card space-y-1 text-center">
              <div className={`h-12 rounded-sm border border-fuschia/20 ${s.cls}`} />
              <p className="font-sketch text-xs text-fuschia">parchment-{s.label}</p>
              <p className="font-mono text-xs text-fuschia/50">{s.hex}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Typography ─────────────────────────────────────── */}
      <section className="space-y-3">
        <h2 className="font-sketch text-xl text-fuschia">Typography</h2>
        <div className="sketch-card space-y-4">
          <p className="font-sketch text-3xl text-papaya">Patrick Hand — Sketch (Headings)</p>
          <p className="font-body text-lg text-fuschia">Lora — Body text for reading passages and lesson content.</p>
          <p className="font-mono text-sm text-paradise">JetBrains Mono — code, IDs, scores: 0.91</p>
        </div>
      </section>

      {/* ── Component Tokens ───────────────────────────────── */}
      <section className="space-y-3">
        <h2 className="font-sketch text-xl text-fuschia">Component Classes</h2>
        <div className="space-y-3">
          <div className="sketch-card">
            <p className="font-body text-fuschia"><code>.sketch-card</code> — standard card with sketch border + shadow</p>
          </div>
          <div className="flex gap-3 flex-wrap">
            <span className="track-badge">track-badge</span>
            <button className="btn-primary">btn-primary</button>
          </div>
          <div className="witness-alert">
            <p className="font-sketch">.witness-alert — shown when ARCHIVE_SILENT fires</p>
          </div>
        </div>
      </section>

      {/* ── Verified Seal ──────────────────────────────────── */}
      <section className="space-y-3">
        <h2 className="font-sketch text-xl text-fuschia">Verified Seal</h2>
        <p className="font-body text-sm text-fuschia/60">
          Renders only when <code>similarityScore &ge; 0.85</code>. Passes <code>null</code> below threshold.
        </p>
        <div className="sketch-card flex flex-wrap items-end gap-8">
          {[
            { score: 0.91, label: "0.91 — VERIFIED" },
            { score: 0.85, label: "0.85 — exact gate" },
            { score: 0.84, label: "0.84 — hidden (null)" },
            { score: 0.60, label: "0.60 — hidden (null)" },
          ].map(({ score, label }) => (
            <div key={score} className="flex flex-col items-center gap-2">
              <VerifiedSeal similarityScore={score} size={52} showScore />
              {score < 0.85 && (
                <span className="font-mono text-xs text-fuschia/40">[null]</span>
              )}
              <span className="font-sketch text-xs text-fuschia/60">{label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── Truth Status Utility ───────────────────────────── */}
      <section className="space-y-3">
        <h2 className="font-sketch text-xl text-fuschia">getTruthStatus()</h2>
        <div className="sketch-card">
          <table className="w-full font-mono text-sm">
            <thead>
              <tr className="text-left border-b border-fuschia/20">
                <th className="pb-2 font-sketch font-normal text-fuschia">Score</th>
                <th className="pb-2 font-sketch font-normal text-fuschia">Status</th>
                <th className="pb-2 font-sketch font-normal text-fuschia">Description</th>
              </tr>
            </thead>
            <tbody>
              {[0.93, 0.85, 0.72, 0.64, 0.40].map((score) => {
                const status = getTruthStatus(score);
                const meta = TRUTH_STATUS_META[status];
                return (
                  <tr key={score} className="border-b border-fuschia/10">
                    <td className="py-2 text-fuschia/70">{score}</td>
                    <td className="py-2 font-sketch" style={{ color: meta.color }}>{status}</td>
                    <td className="py-2 font-body text-xs text-fuschia/60">{meta.description}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Nature Icons ───────────────────────────────────── */}
      <section className="space-y-4">
        <h2 className="font-sketch text-xl text-fuschia">Field Note Flora & Fauna</h2>

        {/* Individual creatures */}
        <div className="sketch-card">
          <div className="flex flex-wrap items-end gap-8 justify-around">
            <div className="flex flex-col items-center gap-2">
              <Wildflower size={80} />
              <span className="font-sketch text-xs text-fuschia/60">Wildflower</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Wildflower size={60} rotate={-8} />
              <span className="font-sketch text-xs text-fuschia/60">tilted</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Butterfly size={90} />
              <span className="font-sketch text-xs text-fuschia/60">Butterfly</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Butterfly size={70} tilt={12} />
              <span className="font-sketch text-xs text-fuschia/60">in flight</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Bee size={80} />
              <span className="font-sketch text-xs text-fuschia/60">Bee</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Bee size={56} tilt={0} />
              <span className="font-sketch text-xs text-fuschia/60">hovering</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Ladybug size={72} />
              <span className="font-sketch text-xs text-fuschia/60">Ladybug</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <MasonJar size={80} />
              <span className="font-sketch text-xs text-fuschia/60">Mason Jar</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <MasonJar size={56} />
              <span className="font-sketch text-xs text-fuschia/60">smaller</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Acorn size={80} />
              <span className="font-sketch text-xs text-fuschia/60">Acorn</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Acorn size={52} />
              <span className="font-sketch text-xs text-fuschia/60">smaller</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <HeartMagnifier size={80} />
              <span className="font-sketch text-xs text-fuschia/60">HeartMagnifier</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <HeartMagnifier size={48} />
              <span className="font-sketch text-xs text-fuschia/60">INVESTIGATING</span>
            </div>
          </div>
        </div>

        {/* Full scene divider */}
        <div className="sketch-card py-6">
          <p className="font-sketch text-xs text-fuschia/40 mb-3 text-center">BotanicalDivider — use between lesson sections</p>
          <BotanicalDivider />
        </div>
        <div className="sketch-card py-6">
          <BotanicalDivider />
        </div>
      </section>

      {/* ── Investigating ──────────────────────────────────── */}
      <section className="space-y-3">
        <h2 className="font-sketch text-xl text-fuschia">Investigating</h2>
        <p className="font-body text-sm text-fuschia/60">
          Middle state — score &ge; 0.65 but &lt; 0.85. Sources found, not yet witnessed.
        </p>
        <Investigating
          topic="the 1847 Cherokee land allotment records"
          similarityScore={0.72}
          showScore
        />
        <Investigating topic="naturopathic remedies in frontier homesteads" />
      </section>

      {/* ── Archive Silent ─────────────────────────────────── */}
      <section className="space-y-3">
        <h2 className="font-sketch text-xl text-fuschia">ArchiveSilent</h2>
        <p className="font-body text-sm text-fuschia/60">
          Replaces lesson block content when Witness Protocol returns <code>ARCHIVE_SILENT</code>.
        </p>
        <ArchiveSilent
          topic="the exact census count of 1840"
          similarityScore={0.61}
          showScore
        />
        <ArchiveSilent topic="oral treaties with the Cherokee Nation" />
      </section>

    </div>
  );
}
