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

      <nav className="sticky top-0 z-40 border-b border-[#3a332b]/10 bg-[#eee7d7]/92 backdrop-blur-xl">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link href="/" className="flex items-center gap-3">
            <Image src="/adeline-nav.png" alt="Adeline" width={46} height={46} className="rounded-full border border-[#3a332b]/15 object-cover shadow-sm" />
            <span className="font-serif text-lg">Dear Adeline</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-sm text-[#51483d] hover:text-[#29251f]">Sign in</Link>
            <Link href="/login?mode=signup" className="rounded-full bg-[#315d58] px-5 py-2.5 text-sm font-semibold text-[#fff9ec] shadow-sm hover:bg-[#294f4b]">Start free</Link>
          </div>
        </div>
      </nav>

      <section className="relative overflow-hidden px-5 pb-24 pt-16 sm:px-8 sm:pt-24 lg:pt-28">
        <div className="mx-auto max-w-7xl">
          <div className="max-w-6xl">
            <h1 className="font-serif text-[clamp(4rem,10vw,9.5rem)] leading-[.84] tracking-[-.045em] text-[#2d2a24]">
              Education as <span className="text-[#8e3f69] italic">Unique</span><br />as Your Child
            </h1>
            <p className="mt-8 max-w-3xl text-lg leading-8 text-[#5b5145] sm:text-xl sm:leading-9">
              Adeline listens to what a young person is actually doing, making, wondering about, reading, fixing, building, or dreaming up. She follows their curiosity, helps when they want help, and quietly turns real life into a record that can move them toward graduation.
            </p>
            <div className="mt-8">
              <Link href="/login?mode=signup" className="inline-flex rounded-full bg-[#315d58] px-7 py-3.5 text-sm font-semibold text-[#fff9ec] shadow-md hover:bg-[#294f4b]">Talk to Adeline</Link>
            </div>
          </div>
        </div>
      </section>

      <section className="relative border-y border-[#3a332b]/10 bg-[#e3dac7]/70 px-5 py-24 sm:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="mb-12 max-w-3xl">
            <p className="text-[10px] uppercase tracking-[.3em] text-[#6f4d73]">two children · two different paths</p>
            <h2 className="mt-4 font-serif text-4xl sm:text-5xl">The learning grows out of their life.</h2>
          </div>

          <div className="grid gap-8 lg:grid-cols-2">
            <article className="rounded-[34px_24px_38px_26px] border border-[#392f27]/15 bg-[#f8f0df] p-6 shadow-lg sm:p-8">
              <p className="text-[9px] uppercase tracking-[.22em] text-[#8e3f69]">Della · crochet business</p>
              <div className="mt-6 space-y-4 text-sm leading-6">
                <Bubble side="adeline">Hi Della! What are you excited to learn about today? 🌿</Bubble>
                <Bubble side="student">I want to grow my crochet business!</Bubble>
                <Bubble side="adeline">That&apos;s amazing! 🧶 Do you have a website to sell your products yet?</Bubble>
                <Bubble side="student">No, not yet...</Bubble>
                <Bubble side="adeline">
                  <p>Perfect! Let&apos;s build one together!</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {['Web Design', 'Marketing', 'Entrepreneurship'].map((tag) => (
                      <span key={tag} className="rounded-full bg-[#BD6809] px-3 py-1 text-[10px] font-bold uppercase text-white">{tag}</span>
                    ))}
                  </div>
                </Bubble>
              </div>
              <p className="mt-7 border-l-2 border-[#8e3f69] pl-4 text-xs italic leading-6 text-[#655a4e]">The website becomes the doorway. Writing, design, pricing, business, technology, and marketing become useful because Della wants them.</p>
            </article>

            <article className="rounded-[30px_38px_26px_34px] border border-[#392f27]/15 bg-[#eef1e7] p-6 shadow-lg sm:p-8">
              <p className="text-[9px] uppercase tracking-[.22em] text-[#355b84]">another child · creek investigation</p>
              <div className="mt-6 space-y-4 text-sm leading-6">
                <Bubble side="student">There were dead fish by the creek and we found an old blue bottle.</Bubble>
                <Bubble side="adeline">The bottle is interesting, but it doesn&apos;t prove anything by itself. Want to figure out what the water can actually tell us?</Bubble>
                <Bubble side="student">Yes.</Bubble>
                <Bubble side="adeline">Then we need comparison samples. Upstream, near the drain, and downstream. I can sketch out what to test, or send you into the creek case in the game world.</Bubble>
              </div>
              <p className="mt-7 border-l-2 border-[#355b84] pl-4 text-xs italic leading-6 text-[#596255]">That one conversation can become a sketchnote, a real-world investigation, or a game-world adventure.</p>
            </article>
          </div>
        </div>
      </section>

      <section className="relative px-5 py-24 sm:px-8">
        <div className="mx-auto grid max-w-7xl gap-12 lg:grid-cols-[.95fr_1.05fr]">
          <div>
            <p className="text-[10px] uppercase tracking-[.3em] text-[#315d58]">what happens underneath</p>
            <h2 className="mt-4 font-serif text-4xl sm:text-5xl">They live it. Adeline translates it.</h2>
            <p className="mt-5 max-w-xl text-sm leading-7 text-[#5d5448]">The child should not have to turn every interesting day into school language. Adeline keeps the academic paper trail quietly in the background.</p>
          </div>
          <div className="rounded-[30px_22px_34px_26px] border border-[#392f27]/15 bg-[#f7efdd] p-6 shadow-lg">
            {RECORD.map((item, i) => (
              <div key={item} className="flex items-center gap-4 border-b border-[#3b3229]/10 py-4 last:border-0">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-[#315d58]/25 font-serif text-xs text-[#315d58]">{i + 1}</span>
                <span className="text-sm text-[#4d4439]">{item}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="relative border-t border-[#3a332b]/10 px-5 py-8 text-center text-[10px] tracking-[.18em] text-[#766c5f]">DEAR ADELINE</footer>
    </main>
  )
}

function Bubble({ side, children }: { side: 'student' | 'adeline'; children: React.ReactNode }) {
  return (
    <div className={side === 'student' ? 'flex justify-end' : 'flex justify-start'}>
      <div className={side === 'student' ? 'max-w-[86%] rounded-[20px_20px_5px_20px] bg-[#315d58] px-4 py-3 text-[#fff9ed]' : 'max-w-[90%] rounded-[5px_20px_20px_20px] border border-[#3c342b]/12 bg-white/65 px-4 py-3 text-[#4c4339]'}>
        {children}
      </div>
    </div>
  )
}
