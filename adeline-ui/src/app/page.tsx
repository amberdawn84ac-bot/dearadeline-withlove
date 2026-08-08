import Link from 'next/link'
import Image from 'next/image'

const RECORD = [
  'What they actually did',
  'Skills and subjects Adeline recognized',
  'Evidence saved in the daily journal and portfolio',
  'Credits accumulating toward graduation',
  'Questions and interests worth following next',
]

export default function Home() {
  return (
    <main className="min-h-screen bg-[#eee7d7] text-[#29251f] selection:bg-[#6f4d73]/20">
      <div className="fixed inset-0 pointer-events-none opacity-[0.13] mix-blend-multiply" style={{ backgroundImage: 'radial-gradient(#332d25 .6px, transparent .7px)', backgroundSize: '6px 6px' }} />

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
            <Link href="/login?mode=signup" className="rounded-full bg-[#5b3769] px-4 py-2 text-[11px] font-semibold text-[#fff8eb] shadow-sm hover:bg-[#4d2f59]">start free</Link>
          </div>
        </div>
      </nav>

      <section className="relative overflow-hidden px-5 pb-20 pt-20 sm:px-8 sm:pt-28">
        <div className="mx-auto grid max-w-7xl items-center gap-14 lg:grid-cols-[1.02fr_.98fr]">
          <div>
            <p className="text-[10px] uppercase tracking-[.34em] text-[#6f4d73]">Dear Adeline</p>
            <h1 className="mt-5 max-w-4xl font-serif text-6xl leading-[.94] sm:text-7xl lg:text-[86px]">Education as <span className="text-[#8e3f69] italic">Unique</span> as Your Child.</h1>
            <p className="mt-7 max-w-2xl text-base leading-8 text-[#595044] sm:text-lg">Adeline listens to what a young person is actually doing, making, wondering about, reading, fixing, building, or dreaming up. She helps when they want help, teaches when curiosity opens the door, and quietly turns real life into a record that can move them toward graduation.</p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link href="/login?mode=signup" className="rounded-full bg-[#315d58] px-6 py-3 text-sm font-semibold text-[#fff9ec] shadow-md">talk to Adeline</Link>
              <a href="#examples" className="rounded-full border border-[#3a332b]/20 bg-[#f5edda]/55 px-6 py-3 text-sm text-[#4c4338]">see what that looks like</a>
            </div>
          </div>

          <div className="relative min-h-[500px]">
            <div className="absolute left-[2%] top-[5%] w-[80%] rotate-[-2deg] rounded-[34px_24px_38px_26px] border border-[#382f27]/15 bg-[#f7efdf] p-7 shadow-2xl">
              <p className="text-[9px] uppercase tracking-[.24em] text-[#7c6e5d]">a conversation, not a course</p>
              <p className="mt-4 font-serif text-2xl">“I want to grow my crochet business.”</p>
              <p className="mt-4 text-sm leading-7 text-[#5e5549]">Adeline notices the missing website, not because “web design” is scheduled, but because Della has somewhere she wants to go.</p>
              <div className="mt-5 flex flex-wrap gap-2 text-[10px]">
                {['web design', 'marketing', 'entrepreneurship'].map((tag) => <span key={tag} className="rounded-full border border-[#8e3f69]/20 bg-[#8e3f69]/10 px-3 py-1 text-[#733858]">{tag}</span>)}
              </div>
            </div>
            <div className="absolute bottom-[2%] right-[1%] w-[70%] rotate-[3deg] rounded-[26px_34px_24px_30px] border border-[#3b3229]/16 bg-[#355b84] p-6 text-[#fff9ed] shadow-2xl">
              <p className="text-[8px] uppercase tracking-[.24em] text-white/55">another child, another door</p>
              <p className="mt-3 font-serif text-2xl">“The creek looks wrong.”</p>
              <p className="mt-3 text-xs leading-6 text-white/72">That can become an investigation, a sketchnote, a game-world adventure, a real water test, or simply a conversation. Adeline follows the child, not a template.</p>
            </div>
          </div>
        </div>
      </section>

      <section id="examples" className="relative border-y border-[#3a332b]/10 bg-[#e3dac7]/70 px-5 py-24 sm:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="mb-12 max-w-3xl">
            <p className="text-[10px] uppercase tracking-[.3em] text-[#6f4d73]">two children · two completely different paths</p>
            <h2 className="mt-4 font-serif text-4xl sm:text-5xl">This is what “unique” actually means.</h2>
          </div>

          <div className="grid gap-8 lg:grid-cols-2">
            <article className="rounded-[34px_24px_38px_26px] border border-[#392f27]/15 bg-[#f8f0df] p-6 shadow-lg sm:p-8">
              <p className="text-[9px] uppercase tracking-[.22em] text-[#8e3f69]">Della · crochet business</p>
              <div className="mt-6 space-y-4 text-sm leading-6">
                <Bubble side="adeline">What have you been thinking about lately?</Bubble>
                <Bubble side="student">I want to grow my crochet business.</Bubble>
                <Bubble side="adeline">Do you have a website where people can see and buy what you make?</Bubble>
                <Bubble side="student">No, not yet.</Bubble>
                <Bubble side="adeline">Then that might be our next build. We can make one together and figure out the design, photos, pricing, writing, and how people will find it.</Bubble>
              </div>
              <p className="mt-7 border-l-2 border-[#8e3f69] pl-4 text-xs italic leading-6 text-[#655a4e]">The learning appears because it serves Della&apos;s goal. Adeline can record the work toward writing, design, business, math, technology, and career evidence as it happens.</p>
            </article>

            <article className="rounded-[30px_38px_26px_34px] border border-[#392f27]/15 bg-[#eef1e7] p-6 shadow-lg sm:p-8">
              <p className="text-[9px] uppercase tracking-[.22em] text-[#355b84]">an investigation · the creek</p>
              <div className="mt-6 space-y-4 text-sm leading-6">
                <Bubble side="student">There were dead fish by the creek and we found an old blue bottle.</Bubble>
                <Bubble side="adeline">The bottle is interesting, but it doesn&apos;t prove anything by itself. Want to figure out what the water can actually tell us?</Bubble>
                <Bubble side="student">Yes.</Bubble>
                <Bubble side="adeline">Then we need comparison samples. Upstream, near the drain, and downstream. I can sketch out what to test, or I can send you into the creek case in the game world.</Bubble>
              </div>
              <p className="mt-7 border-l-2 border-[#355b84] pl-4 text-xs italic leading-6 text-[#596255]">The same conversation can become a sketchnote, a real project, or an adventure. Science, evidence, writing, math, and environmental reasoning are recorded underneath.</p>
            </article>
          </div>
        </div>
      </section>

      <section className="relative px-5 py-24 sm:px-8">
        <div className="mx-auto grid max-w-7xl gap-12 lg:grid-cols-[.95fr_1.05fr]">
          <div>
            <p className="text-[10px] uppercase tracking-[.3em] text-[#315d58]">what Adeline quietly keeps track of</p>
            <h2 className="mt-4 font-serif text-4xl sm:text-5xl">A real life on the front. A graduation record underneath.</h2>
            <p className="mt-5 max-w-xl text-sm leading-7 text-[#5d5448]">The child should not have to translate every interesting day into school language. Adeline does that work backstage.</p>
          </div>
          <div className="rounded-[30px_22px_34px_26px] border border-[#392f27]/15 bg-[#f7efdd] p-6 shadow-lg">
            {RECORD.map((item, i) => <div key={item} className="flex items-center gap-4 border-b border-[#3b3229]/10 py-4 last:border-0"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-[#315d58]/25 font-serif text-xs text-[#315d58]">{i + 1}</span><span className="text-sm text-[#4d4439]">{item}</span></div>)}
          </div>
        </div>
      </section>

      <section className="relative px-5 pb-28 sm:px-8">
        <div className="mx-auto max-w-6xl overflow-hidden rounded-[42px_30px_48px_34px] bg-[#5b3769] px-7 py-14 text-[#fff7e9] shadow-2xl sm:px-14">
          <div className="grid items-end gap-8 md:grid-cols-[1fr_auto]">
            <div>
              <p className="text-[9px] uppercase tracking-[.3em] text-white/55">Dear Adeline</p>
              <h2 className="mt-3 max-w-3xl font-serif text-4xl leading-tight sm:text-6xl">Tell her what you&apos;re doing. Tell her what you&apos;re wondering. See where it goes.</h2>
            </div>
            <Link href="/login?mode=signup" className="rounded-full bg-[#f5ead4] px-6 py-3 text-sm font-semibold text-[#4b3157]">start free</Link>
          </div>
        </div>
      </section>

      <footer className="relative border-t border-[#3a332b]/10 px-5 py-10 text-center text-[10px] tracking-[.18em] text-[#766c5f] sm:px-8">DEAR ADELINE · EDUCATION AS UNIQUE AS YOUR CHILD</footer>
    </main>
  )
}

function Bubble({ side, children }: { side: 'student' | 'adeline'; children: React.ReactNode }) {
  return <div className={side === 'student' ? 'flex justify-end' : 'flex justify-start'}><div className={side === 'student' ? 'max-w-[86%] rounded-[20px_20px_5px_20px] bg-[#315d58] px-4 py-3 text-[#fff9ed]' : 'max-w-[90%] rounded-[5px_20px_20px_20px] border border-[#3c342b]/12 bg-white/65 px-4 py-3 text-[#4c4339]'}>{children}</div></div>
}
