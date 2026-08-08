import Link from 'next/link'
import Image from 'next/image'
import { BookOpen, GraduationCap, MessageCircle, Sparkles, Target, Trophy } from 'lucide-react'

const FEATURES = [
  {
    icon: MessageCircle,
    title: 'Student-Led Learning',
    text: "Your student tells Adeline what they're interested in. Curiosity becomes curriculum, making education meaningful and engaging.",
    tone: '#7FA36D',
  },
  {
    icon: Target,
    title: 'Skills & Standards Tracking',
    text: 'What they actually do is mapped to the concepts and state standards it demonstrates, so progress grows from real evidence.',
    tone: '#C98778',
  },
  {
    icon: GraduationCap,
    title: 'Graduation Tracker',
    text: 'State standards, graduation requirements, and remaining gaps are mapped clearly. Know where they stand and what still needs attention.',
    tone: '#D49A39',
  },
  {
    icon: BookOpen,
    title: 'Portfolio Builder',
    text: 'Every project, investigation, note, creation, and real-world accomplishment can become part of a beautiful record of what they can actually do.',
    tone: '#D49383',
  },
  {
    icon: Sparkles,
    title: 'Gap Detection',
    text: 'Adeline notices learning gaps and finds natural ways to fill them through the interests, projects, questions, and adventures already happening.',
    tone: '#8A52E8',
  },
  {
    icon: Trophy,
    title: 'Learning That Keeps Moving',
    text: 'A question can become a sketchnote, a project, a story, a real-world experiment, or an adventure in the game world. The next step stays connected to the child.',
    tone: '#E83B79',
  },
]

export default function Home() {
  return (
    <main className="min-h-screen bg-[#fbf5ea] text-[#2f4731] selection:bg-[#bd6809]/20">
      <nav className="sticky top-0 z-40 border-b border-[#2f4731]/10 bg-[#fffdf8]/92 backdrop-blur-xl">
        <div className="mx-auto flex h-[88px] max-w-6xl items-center justify-between px-5 sm:px-8">
          <Link href="/" className="flex items-center gap-3">
            <Image src="/adeline-nav.png" alt="Dear Adeline" width={44} height={44} className="rounded-xl shadow-sm" />
            <span className="text-2xl text-[#2f4731]" style={{ fontFamily: 'var(--font-emilys-candy)' }}>Dear Adeline</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link href="/login" className="rounded-full border border-[#2f4731] px-5 py-2 text-xs font-bold uppercase tracking-[.16em] text-[#2f4731]">Sign in</Link>
            <Link href="/login?mode=signup" className="rounded-full bg-[#b5164a] px-6 py-2.5 text-xs font-bold uppercase tracking-[.16em] text-white shadow-lg shadow-[#b5164a]/15">Start free</Link>
          </div>
        </div>
      </nav>

      <section className="px-5 pb-20 pt-16 sm:px-8 sm:pt-20 lg:pb-24">
        <div className="mx-auto grid max-w-6xl items-center gap-14 lg:grid-cols-[.94fr_1.06fr]">
          <div>
            <p className="text-2xl text-[#bd6809]" style={{ fontFamily: 'var(--font-emilys-candy)' }}>Where Learning Comes Alive</p>
            <h1 className="mt-1 max-w-[620px] font-serif text-[clamp(4.2rem,7vw,7.2rem)] leading-[.82] tracking-[-.055em] text-[#2f4731]">
              Education<br />as <span className="italic text-[#d48728]">Unique</span><br />as Your<br />Child
            </h1>
            <p className="mt-8 max-w-xl text-lg leading-7 text-[#506a54]">
              An AI-powered learning companion that adapts to your student&apos;s interests, tracks skills toward graduation, and transforms curiosity into achievement.
            </p>
            <div className="mt-9 flex flex-wrap gap-4">
              <Link href="/login?mode=signup" className="inline-flex items-center gap-3 rounded-full bg-[#b5164a] px-8 py-4 text-xs font-bold uppercase tracking-[.15em] text-white shadow-lg shadow-[#b5164a]/15">
                Continue learning <span aria-hidden>→</span>
              </Link>
              <a href="#method" className="inline-flex items-center rounded-full border border-[#2f4731] px-8 py-4 text-xs font-bold uppercase tracking-[.15em] text-[#2f4731]">The method</a>
            </div>
          </div>

          <div className="rounded-[30px] border-2 border-[#2f4731]/70 bg-white p-2 shadow-[0_18px_50px_rgba(47,71,49,.12)]">
            <div className="overflow-hidden rounded-[24px] border border-[#2f4731]/15 bg-[#fbf5ea]">
              <div className="flex items-center justify-between bg-[#2f4731] px-6 py-4 text-white">
                <div>
                  <p className="text-[9px] font-bold uppercase tracking-[.22em] text-white/60">Adeline</p>
                  <p className="mt-1 text-lg" style={{ fontFamily: 'var(--font-emilys-candy)' }}>A conversation that can go somewhere</p>
                </div>
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
              </div>

              <div className="space-y-4 p-6 text-sm leading-6">
                <Bubble side="adeline">Hi Della! What are you excited to learn about today? 🌿</Bubble>
                <Bubble side="student">I want to grow my crochet business!</Bubble>
                <Bubble side="adeline">That&apos;s amazing! 🧶 Do you have a website to sell your products yet?</Bubble>
                <Bubble side="student">No, not yet...</Bubble>
                <div className="rounded-[18px] border border-[#d48728] bg-white px-5 py-4 text-[#2f4731] shadow-sm">
                  <p className="font-bold text-[#d48728]">Perfect! Let&apos;s build one together!</p>
                  <p className="mt-2 text-xs italic text-[#b5164a]">You&apos;ll learn web design, marketing, AND run your business. Here are the skills you&apos;ll earn:</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {['Web Design', 'Marketing', 'Entrepreneurship'].map((tag) => (
                      <span key={tag} className="rounded-full bg-[#e8ece4] px-3 py-1 text-[9px] font-bold uppercase tracking-wide text-[#2f4731]">{tag}</span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="border-t border-[#2f4731]/10 bg-white/70 px-6 py-3 text-center text-[9px] uppercase tracking-[.18em] text-[#6f806f]">
                Skills and standards quietly tracked toward graduation
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="method" className="border-t border-[#2f4731]/10 bg-white px-5 py-20 sm:px-8">
        <div className="mx-auto max-w-6xl text-center">
          <p className="text-2xl text-[#c97867]" style={{ fontFamily: 'var(--font-emilys-candy)' }}>Why Dear Adeline?</p>
          <h2 className="mt-1 text-4xl font-bold tracking-tight text-[#29312d] sm:text-5xl">Learning That <span className="text-[#7fa36d]">Grows With You</span></h2>
          <p className="mx-auto mt-3 max-w-3xl text-lg leading-8 text-[#5d6877]">
            Every student is unique. Adeline understands that, adapting to interests, identifying strengths, and gently filling learning gaps.
          </p>

          <div className="mt-12 grid gap-7 text-left md:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, text, tone }) => (
              <article key={title} className="min-h-[250px] rounded-[26px] border border-black/5 bg-white p-8 shadow-[0_10px_30px_rgba(24,40,30,.07)]">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl text-white" style={{ backgroundColor: tone }}><Icon size={30} strokeWidth={2} /></div>
                <h3 className="mt-6 text-2xl font-bold text-[#29312d]">{title}</h3>
                <p className="mt-2 text-base leading-7 text-[#5d6877]">{text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-[#2f4731]/10 bg-[#fbf5ea] px-5 py-8 text-center text-sm text-[#718071]">
        <span style={{ fontFamily: 'var(--font-emilys-candy)' }} className="text-xl text-[#2f4731]">Dear Adeline</span>
      </footer>
    </main>
  )
}

function Bubble({ side, children }: { side: 'student' | 'adeline'; children: React.ReactNode }) {
  return (
    <div className={side === 'student' ? 'flex justify-end' : 'flex justify-start'}>
      <div className={side === 'student' ? 'max-w-[84%] rounded-[18px_18px_5px_18px] bg-[#63785f] px-4 py-3 text-white shadow-sm' : 'max-w-[88%] rounded-[5px_18px_18px_18px] border border-[#2f4731]/10 bg-white px-4 py-3 text-[#2f4731] shadow-sm'}>
        {children}
      </div>
    </div>
  )
}
