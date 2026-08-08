import Link from 'next/link';
import Image from 'next/image';

const PLACES = [
  ['The creek', 'Investigate what changed, gather evidence, test a theory.'],
  ['The workshop', 'Build, repair, measure, prototype, and try again.'],
  ['The courthouse', 'Read records, weigh claims, understand power and law.'],
  ['The market', 'Price things, negotiate, run numbers, understand tradeoffs.'],
  ['The archives', 'Follow primary sources instead of tidy summaries.'],
  ['Adeline’s place', 'Talk, plan, make sense of what happened, decide what comes next.'],
];

const RECORD = [
  'Skills demonstrated',
  'Standards and competencies touched',
  'Projects and evidence saved',
  'Credits accumulating toward graduation',
  'Gaps that still need attention',
  'A transcript a parent can actually understand',
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[#eee7d7] text-[#29251f] selection:bg-[#5d3b70]/20">
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.14] mix-blend-multiply"
        style={{ backgroundImage: 'radial-gradient(#332d25 .6px, transparent .7px)', backgroundSize: '6px 6px' }}
      />

      <nav className="sticky top-0 z-40 border-b border-[#3a332b]/10 bg-[#eee7d7]/90 backdrop-blur-xl">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link href="/" className="flex items-center gap-3">
            <Image src="/adeline-nav.png" alt="Adeline" width={46} height={46} className="rounded-full border border-[#3a332b]/15 object-cover shadow-sm" />
            <div>
              <p className="font-serif text-lg leading-none">Dear Adeline</p>
              <p className="mt-1 text-[9px] uppercase tracking-[.24em] text-[#71675b]">education as unique as your child</p>
            </div>
          </Link>
          <div className="flex items-center gap-2">
            <Link href="/login" className="rounded-full border border-[#3a332b]/20 px-4 py-2 text-[11px] font-semibold text-[#433b32] hover:bg-[#f7f0df]">sign in</Link>
            <Link href="/pricing" className="rounded-full bg-[#5b3769] px-4 py-2 text-[11px] font-semibold text-[#fff8eb] shadow-sm hover:bg-[#4d2f59]">see plans</Link>
          </div>
        </div>
      </nav>

      <section className="relative overflow-hidden px-5 pb-24 pt-20 sm:px-8 sm:pt-28">
        <div className="mx-auto grid max-w-7xl items-center gap-14 lg:grid-cols-[1.05fr_.95fr]">
          <div>
            <p className="text-[10px] uppercase tracking-[.34em] text-[#6f4d73]">not school with prettier buttons</p>
            <h1 className="mt-5 max-w-4xl font-serif text-5xl leading-[.98] sm:text-7xl lg:text-[88px]">Give them a world worth getting curious about.</h1>
            <p className="mt-7 max-w-2xl text-base leading-8 text-[#595044] sm:text-lg">
              Dear Adeline turns learning into places, problems, investigations, conversations, builds, and real decisions. The student experiences an adventure. Underneath it, the system keeps the academic record needed to move toward graduation.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link href="/login" className="rounded-full bg-[#315d58] px-6 py-3 text-sm font-semibold text-[#fff9ec] shadow-md">open Dear Adeline</Link>
              <a href="#how" className="rounded-full border border-[#3a332b]/20 bg-[#f5edda]/55 px-6 py-3 text-sm text-[#4c4338]">see how it works</a>
            </div>
          </div>

          <div className="relative min-h-[480px]">
            <div className="absolute left-[4%] top-[10%] h-[360px] w-[78%] rotate-[-3deg] rounded-[42px_28px_46px_32px] border border-[#382f27]/18 bg-[#f5edda] shadow-2xl">
              <div className="p-7">
                <p className="text-[9px] uppercase tracking-[.25em] text-[#776b5d]">field note · creek road</p>
                <h2 className="mt-3 font-serif text-3xl">The creek is wrong.</h2>
                <p className="mt-4 max-w-sm font-serif text-sm leading-7 text-[#554b3f]">Fish are floating near the bend. There is a cobalt bottle in the roots and an old drain under the road. Nothing tells the learner what subject this is.</p>
                <div className="mt-8 grid grid-cols-3 gap-3">
                  {['water sample', 'delivery slip', 'old drain'].map((item, i) => (
                    <div key={item} className="rounded-2xl border border-[#3d342c]/12 bg-white/35 p-3 text-center">
                      <div className={`mx-auto h-8 w-8 rounded-full ${i === 0 ? 'bg-[#315f70]' : i === 1 ? 'bg-[#6f4d73]' : 'bg-[#9a4e35]'} opacity-80`} />
                      <p className="mt-2 text-[9px] text-[#655b4e]">{item}</p>
                    </div>
                  ))}
                </div>
                <p className="mt-7 border-l-2 border-[#315f70] pl-4 text-xs italic leading-6 text-[#63594c]">Find out what the evidence supports before deciding who or what caused it.</p>
              </div>
            </div>
            <div className="absolute bottom-[4%] right-[2%] w-[54%] rotate-[4deg] rounded-[24px_32px_20px_30px] border border-[#3b3229]/18 bg-[#3e614f] p-5 text-[#fff7e8] shadow-2xl">
              <p className="text-[8px] uppercase tracking-[.25em] text-white/60">what the system quietly records</p>
              <p className="mt-3 font-serif text-xl">Science · math · evidence · writing</p>
              <p className="mt-3 text-[11px] leading-5 text-white/70">The child gets a mystery. The parent gets a defensible learning record.</p>
            </div>
          </div>
        </div>
      </section>

      <section id="how" className="relative border-y border-[#3a332b]/10 bg-[#e3dac7]/70 px-5 py-24 sm:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="grid gap-10 lg:grid-cols-2">
            <div>
              <p className="text-[10px] uppercase tracking-[.3em] text-[#6f4d73]">what the learner sees</p>
              <h2 className="mt-4 font-serif text-4xl sm:text-5xl">A town, not a course catalog.</h2>
              <p className="mt-5 max-w-xl text-sm leading-7 text-[#5d5448]">The ten Dear Adeline tracks run underneath believable places and problems. A single adventure can cross science, writing, math, history, economics, government, health, stewardship, justice, and discipleship without announcing each transition.</p>
              <div className="mt-8 grid gap-3 sm:grid-cols-2">
                {PLACES.map(([title, desc]) => (
                  <div key={title} className="rounded-[22px_17px_24px_19px] border border-[#392f27]/12 bg-[#f4eddd]/70 p-5">
                    <h3 className="font-serif text-lg">{title}</h3>
                    <p className="mt-2 text-xs leading-6 text-[#665c4f]">{desc}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="lg:pl-12">
              <p className="text-[10px] uppercase tracking-[.3em] text-[#315d58]">what the parent sees</p>
              <h2 className="mt-4 font-serif text-4xl sm:text-5xl">The paper trail behind the wonder.</h2>
              <p className="mt-5 max-w-xl text-sm leading-7 text-[#5d5448]">Fun is not enough if nobody can show what the learner actually mastered. Dear Adeline keeps evidence underneath the experience so curiosity can still lead somewhere concrete.</p>
              <div className="mt-8 rounded-[30px_22px_34px_26px] border border-[#392f27]/15 bg-[#f7efdd] p-6 shadow-lg">
                {RECORD.map((item, i) => (
                  <div key={item} className="flex items-center gap-4 border-b border-[#3b3229]/10 py-4 last:border-0">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-[#315d58]/25 font-serif text-xs text-[#315d58]">{i + 1}</span>
                    <span className="text-sm text-[#4d4439]">{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="relative px-5 py-24 sm:px-8">
        <div className="mx-auto max-w-5xl text-center">
          <p className="text-[10px] uppercase tracking-[.32em] text-[#6f4d73]">where the Brain belongs</p>
          <h2 className="mx-auto mt-4 max-w-4xl font-serif text-4xl leading-tight sm:text-6xl">AI should run backstage, not stand in the middle of the room waving its arms.</h2>
          <p className="mx-auto mt-7 max-w-2xl text-sm leading-7 text-[#5e5549]">The Brain can adapt difficulty, suggest the next useful challenge, help an NPC respond, evaluate evidence, and connect work to academic goals. The interface should still feel like Dear Adeline, not a chatbot product.</p>
        </div>
      </section>

      <section className="relative px-5 pb-28 sm:px-8">
        <div className="mx-auto max-w-6xl overflow-hidden rounded-[42px_30px_48px_34px] bg-[#5b3769] px-7 py-14 text-[#fff7e9] shadow-2xl sm:px-14">
          <div className="grid items-end gap-8 md:grid-cols-[1fr_auto]">
            <div>
              <p className="text-[9px] uppercase tracking-[.3em] text-white/55">Dear Adeline</p>
              <h2 className="mt-3 max-w-3xl font-serif text-4xl leading-tight sm:text-6xl">Keep the wonder. Keep the receipts.</h2>
              <p className="mt-5 max-w-2xl text-sm leading-7 text-white/70">A learner can spend the afternoon solving a problem in town. Their family can still see exactly what that afternoon accomplished.</p>
            </div>
            <Link href="/login" className="rounded-full bg-[#f5ead4] px-6 py-3 text-sm font-semibold text-[#4b3157]">sign in</Link>
          </div>
        </div>
      </section>

      <footer className="relative border-t border-[#3a332b]/10 px-5 py-10 text-center text-[10px] tracking-[.18em] text-[#766c5f] sm:px-8">DEAR ADELINE · BUILT AROUND THE LEARNER</footer>
    </main>
  );
}
