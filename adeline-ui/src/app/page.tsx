import Link from 'next/link'
import Image from 'next/image'
import { BookOpen, Brain, GraduationCap, Sparkles, Target, MessageCircle } from 'lucide-react'

const FEATURES = [
  {
    title: 'Student-Led Learning',
    description: 'Your student tells Adeline what they are doing, building, reading, wondering about, or trying. Curiosity becomes the path.',
    Icon: MessageCircle,
    accent: '#7ea06f',
  },
  {
    title: 'Standards Mapping',
    description: 'Real-life work is quietly mapped to state concepts and standards, creating evidence without turning life into a worksheet.',
    Icon: Target,
    accent: '#cc8a7d',
  },
  {
    title: 'Graduation Tracker',
    description: 'See which concepts are covered, which still need evidence, and how the learner is moving toward graduation.',
    Icon: GraduationCap,
    accent: '#d39a36',
  },
  {
    title: 'Portfolio Builder',
    description: 'Projects, activities, notes, explanations, photos, and real work become a living record of what the learner can actually do.',
    Icon: BookOpen,
    accent: '#d08c7a',
  },
  {
    title: 'Gap Detection',
    description: 'Adeline notices what is still missing and looks for a natural way to fill the gap through the learner’s current interests.',
    Icon: Brain,
    accent: '#8b55e9',
  },
  {
    title: 'Stories, Projects & Adventures',
    description: 'A conversation can become a sketchnote, experiment, story, investigation, build, field adventure, or game-world experience.',
    Icon: Sparkles,
    accent: '#e3377b',
  },
]

export default function Home() {
  return (
    <main className="min-h-screen bg-[#fbf5ea] text-[#294b35] selection:bg-[#bd6809]/20">
      <nav className="sticky top-0 z-40 border-b border-[#294b35]/10 bg-[#fffdfa]/92 backdrop-blur-xl">
        <div className="mx-auto flex h-20 max-w-6xl items-center justify-between px-5 sm:px-8">
          <Link href="/" className="flex items-center gap-3">
            <Image
              src="/adeline-nav.png"
              alt="Adeline"
              width={44}
              height={44}
              className="rounded-xl border border-[#294b35]/10 object-cover shadow-sm"
            />
            <span className="font-serif text-xl font-semibold text-[#294b35]">Dear Adeline</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link href="/login" className="rounded-full border border-[#294b35] px-5 py-2 text-xs font-semibold uppercase tracking-[.16em] text-[#294b35]">
              Sign in
            </Link>
            <Link href="/login?mode=signup" className="rounded-full bg-[#b8114d] px-6 py-2.5 text-xs font-semibold uppercase tracking-[.16em] text-white shadow-lg">
              Start free
            </Link>
          </div>
        </div>
      </nav>

      <section className="px-5 pb-24 pt-16 sm:px-8 lg:pt-24">
        <div className="mx-auto grid max-w-6xl items-center gap-14 lg:grid-cols-[.92fr_1.08fr]">
          <div>
            <p className="text-2xl italic text-[#c97825]" style={{ fontFamily: 'var(--font-kalam), cursive' }}>
              Where Learning Comes Alive
            </p>
            <h1 className="mt-1 font-serif text-[clamp(4rem,8.2vw,8.3rem)] leading-[.79] tracking-[-.045em] text-[#294b35]">
              Education<br />
              as<br />
              <span className="italic text-[#d7892e]">Unique</span><br />
              as Your<br />
              Child
            </h1>
            <p className="mt-9 max-w-xl text-lg leading-8 text-[#47604e]">
              Adeline follows your child&apos;s interests, notices what they are already learning in real life, maps that work to state standards, and helps fill the gaps naturally on the way to graduation.
            </p>
            <div className="mt-9 flex flex-wrap gap-4">
              <Link href="/login?mode=signup" className="rounded-full bg-[#b8114d] px-8 py-4 text-xs font-bold uppercase tracking-[.18em] text-white shadow-xl">
                Talk to Adeline →
              </Link>
              <a href="#features" className="rounded-full border border-[#294b35] px-8 py-4 text-xs font-bold uppercase tracking-[.18em] text-[#294b35]">
                See how it works
              </a>
            </div>
          </div>

          <div className="relative">
            <div className="mx-auto max-w-xl overflow-hidden rounded-[32px] border-2 border-[#294b35] bg-[#fffdf8] shadow-[0_25px_70px_rgba(51,57,42,.16)]">
              <div className="flex items-center justify-between bg-[#294b35] px-6 py-5 text-white">
                <div>
                  <p className="text-[9px] uppercase tracking-[.2em] text-white/55">Adeline</p>
                  <p className="font-serif text-lg">Your learning companion</p>
                </div>
                <span className="h-3 w-3 rounded-full bg-emerald-400" />
              </div>

              <div className="space-y-4 px-6 py-7 text-sm leading-6">
                <Bubble side="adeline">Hi Della! What are you excited to learn about today? 🌿</Bubble>
                <Bubble side="student">I want to grow my crochet business!</Bubble>
                <Bubble side="adeline">That&apos;s amazing! 🧶 Do you have a website to sell your products yet?</Bubble>
                <Bubble side="student">No, not yet...</Bubble>
                <div className="rounded-2xl border border-[#d7892e] bg-white px-5 py-4 shadow-sm">
                  <p className="font-semibold text-[#d27a1e]">Perfect! Let&apos;s build one together!</p>
                  <p className="mt-2 text-xs italic text-[#b8114d]">You&apos;ll learn web design, marketing, AND run your business. Here are the skills you&apos;ll earn:</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {['Web Design', 'Marketing', 'Entrepreneurship'].map((tag) => (
                      <span key={tag} className="rounded-full bg-[#eef0e8] px-3 py-1 text-[9px] font-bold uppercase tracking-wide text-[#294b35]">{tag}</span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="border-t border-[#294b35]/10 px-6 py-4 text-center text-[9px] uppercase tracking-[.2em] text-[#748176]">
                Skills and standards are tracked quietly underneath
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="border-t border-[#294b35]/8 bg-white px-5 py-24 sm:px-8">
        <div className="mx-auto max-w-6xl">
          <div className="text-center">
            <p className="text-xl italic text-[#d78364]" style={{ fontFamily: 'var(--font-kalam), cursive' }}>Why Dear Adeline?</p>
            <h2 className="mt-2 font-serif text-4xl font-semibold text-[#2f3f35] sm:text-5xl">
              Learning That <span className="text-[#7ea06f]">Grows With You</span>
            </h2>
            <p className="mx-auto mt-4 max-w-3xl text-lg leading-8 text-[#607066]">
              Every learner is different. Adeline adapts to interests, recognizes strengths, records real-world evidence, and gently fills learning gaps.
            </p>
          </div>

          <div className="mt-12 grid gap-7 md:grid-cols-2 xl:grid-cols-3">
            {FEATURES.map(({ title, description, Icon, accent }) => (
              <article key={title} className="rounded-[28px] border border-black/5 bg-white p-8 shadow-[0_10px_35px_rgba(41,75,53,.07)]">
                <div className="flex h-16 w-16 items-center justify-center rounded-[20px] text-white" style={{ backgroundColor: accent }}>
                  <Icon size={28} />
                </div>
                <h3 className="mt-6 font-serif text-2xl font-semibold text-[#303d34]">{title}</h3>
                <p className="mt-2 text-base leading-7 text-[#617067]">{description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-[#f8f1e5] px-5 py-24 sm:px-8">
        <div className="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[.85fr_1.15fr] lg:items-center">
          <div>
            <p className="text-xl italic text-[#c97825]" style={{ fontFamily: 'var(--font-kalam), cursive' }}>Another child, another path</p>
            <h2 className="mt-2 font-serif text-4xl text-[#294b35] sm:text-5xl">The creek becomes an investigation.</h2>
            <p className="mt-5 text-base leading-8 text-[#5b685e]">
              The same system that can help Della build a business can follow another learner into a water-quality mystery, a sketchnote, a real experiment, or the Dear Adeline game world.
            </p>
          </div>
          <div className="rounded-[30px] border border-[#294b35]/12 bg-[#edf2e9] p-7 shadow-lg">
            <div className="space-y-4 text-sm leading-6">
              <Bubble side="student">There were dead fish by the creek and we found an old blue bottle.</Bubble>
              <Bubble side="adeline">The bottle is interesting, but it doesn&apos;t prove anything by itself. Want to figure out what the water can actually tell us?</Bubble>
              <Bubble side="student">Yes.</Bubble>
              <Bubble side="adeline">Then we need comparison samples. Upstream, near the drain, and downstream. I can sketch out what to test, or send you into the creek case in the game world.</Bubble>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-[#294b35]/10 bg-[#fffdfa] px-5 py-8 text-center text-[10px] uppercase tracking-[.2em] text-[#758078]">
        Dear Adeline · Education as Unique as Your Child
      </footer>
    </main>
  )
}

function Bubble({ side, children }: { side: 'student' | 'adeline'; children: React.ReactNode }) {
  return (
    <div className={side === 'student' ? 'flex justify-end' : 'flex justify-start'}>
      <div className={side === 'student' ? 'max-w-[82%] rounded-[18px_18px_5px_18px] bg-[#5d745d] px-4 py-3 text-white shadow-sm' : 'max-w-[88%] rounded-[5px_18px_18px_18px] border border-[#294b35]/10 bg-white px-4 py-3 text-[#415247] shadow-sm'}>
        {children}
      </div>
    </div>
  )
}
