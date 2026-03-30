import Link from 'next/link';
import Image from 'next/image';
import {
  OpenBook,
  Compass,
  Scroll,
  Pencil,
  MagnifyingGlass,
  Lightbulb,
} from '@/components/illustrations';
import { HomeLessonDemo } from '@/components/HomeLessonDemo';

export default function Home() {
  return (
    <div className="min-h-screen bg-[#FFFEF7] text-[#2F4731] selection:bg-[#BD6809]/20 relative">
      {/* Watermark */}
      <div className="fixed inset-0 pointer-events-none z-0 flex items-center justify-center">
        <Image
          src="/adeline-watermark.png"
          alt=""
          width={800}
          height={800}
          className="opacity-[0.03] select-none"
          priority={false}
        />
      </div>

      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 bg-white/70 backdrop-blur-xl z-50 border-b border-[#E7DAC3]">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <Image
              src="/adeline-nav.png"
              alt="Adeline"
              width={44}
              height={44}
              className="rounded-xl shadow-lg -rotate-3"
            />
            <span className="text-2xl font-bold tracking-tight" style={{ fontFamily: 'var(--font-emilys-candy), "Emilys Candy", cursive' }}>
              Dear Adeline
            </span>
          </Link>
          <div className="hidden md:flex items-center gap-6">
            <Link
              href="/login"
              className="px-6 py-2.5 rounded-full border-2 border-[#2F4731] text-[#2F4731] text-xs font-black uppercase tracking-widest hover:bg-[#2F4731] hover:text-white transition-all"
            >
              Log In
            </Link>
            <Link
              href="/pricing"
              className="px-8 py-3.5 rounded-full bg-[#6B1D2A] text-white text-xs font-black uppercase tracking-[0.2em] shadow-xl hover:scale-105 active:scale-95 transition-all"
            >
              Try Free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-44 pb-32 px-6">
        <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-20 items-center">
          <div className="space-y-10">
            <div className="space-y-6">
              <p className="text-[#BD6809] text-3xl leading-none" style={{ fontFamily: 'var(--font-kalam), Kalam, "Comic Sans MS", system-ui' }}>
                Where Learning Comes Alive
              </p>
              <h1
                className="text-7xl md:text-8xl lg:text-9xl font-normal leading-[0.85] tracking-tighter"
                style={{ fontFamily: 'var(--font-emilys-candy), "Emilys Candy", cursive' }}
              >
                Education as <br />
                <span className="text-[#BD6809] italic">Unique</span> <br />
                as Your Child
              </h1>
            </div>

            <p className="text-xl text-[#2F4731]/80 font-medium max-w-lg leading-relaxed">
              An AI-powered learning companion that adapts to your student&apos;s interests, tracks skills toward graduation, and transforms curiosity into achievement.
            </p>

            <div className="flex flex-wrap gap-6 pt-4">
              <Link
                href="/pricing"
                className="px-12 py-6 rounded-full bg-[#6B1D2A] text-white font-black uppercase tracking-[0.2em] text-xs shadow-2xl hover:brightness-125 active:scale-95 transition-all flex items-center gap-4"
              >
                Join the Academy
                <span className="text-lg">→</span>
              </Link>
              <Link
                href="#philosophy"
                className="px-12 py-6 rounded-full border-2 border-[#2F4731] text-[#2F4731] font-black uppercase tracking-[0.2em] text-xs flex items-center gap-2 hover:bg-[#2F4731]/5 transition-all"
              >
                The Method
              </Link>
            </div>

            <div className="flex items-center gap-4 pt-6 opacity-60">
              <div className="flex -space-x-3">
                {['E', 'M', 'D', 'K'].map((initial, i) => (
                  <div
                    key={i}
                    className="w-10 h-10 rounded-full bg-[#2F4731]/80 border-2 border-[#FFFEF7] flex items-center justify-center text-[10px] font-bold text-white uppercase"
                  >
                    {initial}
                  </div>
                ))}
              </div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-[#2F4731]">
                Trusted by homeschool families <br />
                across Oklahoma
              </p>
            </div>
          </div>

          {/* Chat Preview Card */}
          <div className="relative">
            <div className="relative z-10 bg-white p-2 rounded-[2rem] border-2 border-[#2F4731] shadow-2xl" style={{ transform: 'rotate(1deg)' }}>
              <div className="bg-[#FFFEF7] rounded-[1.8rem] overflow-hidden">
                <div className="p-6 bg-[#2F4731] text-white flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
                      <span role="img" aria-label="AI Mentor">🧠</span>
                    </div>
                    <div>
                      <p className="text-[10px] font-black uppercase tracking-widest opacity-60">AI Mentor</p>
                      <p className="font-bold" style={{ fontFamily: 'var(--font-emilys-candy), "Emilys Candy", cursive' }}>Adeline</p>
                    </div>
                  </div>
                  <div className="w-3 h-3 rounded-full bg-emerald-400 animate-pulse" />
                </div>
                <div className="p-8 space-y-4 min-h-[360px]" style={{ fontFamily: 'var(--font-kalam), Kalam, "Comic Sans MS", system-ui' }}>
                  <div className="flex justify-start">
                    <div className="bg-white p-4 rounded-2xl rounded-tl-none border border-[#2F4731]/10 text-sm max-w-[85%] shadow-sm">
                      Hi Della! What are you excited to learn about today? 🌿
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <div className="bg-[#2F4731]/80 p-4 rounded-2xl rounded-tr-none text-white text-sm max-w-[85%] shadow-lg">
                      I want to grow my crochet business!
                    </div>
                  </div>
                  <div className="flex justify-start">
                    <div className="bg-white p-4 rounded-2xl rounded-tl-none border border-[#2F4731]/10 text-sm max-w-[85%] shadow-sm">
                      That&apos;s amazing! 🧶 Do you have a website to sell your products yet?
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <div className="bg-[#2F4731]/80 p-4 rounded-2xl rounded-tr-none text-white text-sm max-w-[85%] shadow-lg">
                      No, not yet...
                    </div>
                  </div>
                  <div className="flex justify-start">
                    <div className="bg-white p-4 rounded-2xl rounded-tl-none border border-[#2F4731]/10 text-sm max-w-[85%] shadow-sm space-y-3">
                      <p>Perfect! Let&apos;s build one together!</p>
                      <div className="flex flex-wrap gap-2">
                        {['Web Design', 'Marketing', 'Entrepreneurship'].map((tag) => (
                          <span key={tag} className="px-3 py-1 bg-[#BD6809] text-white text-[10px] font-bold rounded-full uppercase">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Live Demo Section */}
      <section className="py-24 px-6 bg-[#F9F6F0]">
        <div className="max-w-7xl mx-auto flex flex-col items-center gap-10">
          <div className="text-center space-y-3">
            <p className="text-[#BD6809] font-black uppercase tracking-[0.4em] text-xs">
              Try It Now — No Account Required
            </p>
            <h2
              className="text-4xl md:text-5xl font-normal leading-tight"
              style={{ fontFamily: 'var(--font-emilys-candy), "Emilys Candy", cursive' }}
            >
              Ask Adeline anything.
            </h2>
            <p className="text-sm text-[#2F4731]/60 max-w-md">
              Choose a track, type a topic, and watch Adeline retrieve a verified primary source and synthesize an age-appropriate lesson — live.
            </p>
          </div>
          <HomeLessonDemo />
        </div>
      </section>

      {/* Features Section */}
      <section className="py-32 px-6 bg-[#2F4731] text-white">
        <div className="max-w-7xl mx-auto flex flex-col items-center text-center space-y-16">
          <div className="space-y-4">
            <p className="text-[#BD6809] font-black uppercase tracking-[0.4em] text-xs">What Adeline Does</p>
            <h2
              className="text-6xl md:text-7xl font-normal leading-none"
              style={{ fontFamily: 'var(--font-emilys-candy), "Emilys Candy", cursive' }}
            >
              Built for Real Learning
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8 w-full">
            {[
              { title: 'Student-Led Learning', desc: 'Adeline follows curiosities and builds plans around passions — not worksheets.', Icon: OpenBook, color: 'bg-emerald-500/20' },
              { title: 'Skills & Credits', desc: 'Every activity maps to credits and competencies automatically. Oklahoma-aligned.', Icon: Compass, color: 'bg-amber-500/20' },
              { title: 'Graduation Tracker', desc: 'See progress toward state-aligned graduation goals in one glance.', Icon: Scroll, color: 'bg-blue-500/20' },
              { title: 'Portfolio Builder', desc: 'Projects, artifacts, and reflections all saved for transcripts.', Icon: Pencil, color: 'bg-rose-500/20' },
              { title: 'Gap Detection', desc: 'Spots missing concepts early and suggests just-right nudges via BKT.', Icon: MagnifyingGlass, color: 'bg-violet-500/20' },
              { title: 'Fun & Games', desc: 'Playful missions, badges, and creative prompts keep learners engaged.', Icon: Lightbulb, color: 'bg-yellow-500/20' },
            ].map((feature, i) => (
              <div
                key={i}
                className="group p-10 bg-white/5 border border-white/10 rounded-[2.5rem] hover:bg-white transition-all duration-500 hover:scale-[1.02] text-left"
              >
                <div className={`w-14 h-14 ${feature.color} rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}>
                  <feature.Icon size={28} color="white" />
                </div>
                <h3
                  className="text-2xl font-bold mb-3 group-hover:text-[#2F4731]"
                  style={{ fontFamily: 'var(--font-emilys-candy), "Emilys Candy", cursive' }}
                >
                  {feature.title}
                </h3>
                <p className="text-white/60 text-sm leading-relaxed group-hover:text-[#2F4731]/70">
                  {feature.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Philosophy Section */}
      <section id="philosophy" className="py-40 px-6">
        <div className="max-w-7xl mx-auto flex flex-col items-center text-center space-y-20">
          <div className="max-w-3xl space-y-6">
            <h2
              className="text-6xl md:text-7xl lg:text-8xl font-normal text-[#2F4731] leading-none italic"
              style={{ fontFamily: 'var(--font-emilys-candy), "Emilys Candy", cursive' }}
            >
              Education should look{' '}
              <span className="text-[#BD6809]">nothing like</span> a factory.
            </h2>
            <p className="text-xl text-[#2F4731]/60 font-medium leading-relaxed">
              We&apos;ve replaced the assembly line with a laboratory. Dear Adeline adapts to each student&apos;s pulse — discovering their strengths and gently revealing their gaps.
            </p>
          </div>

          <div className="grid md:grid-cols-4 gap-4 w-full">
            {[
              { title: 'Hook', desc: 'Narrative-driven discovery', icon: '✨' },
              { title: 'Research', desc: 'Deep-dive investigation', icon: '🔍' },
              { title: 'Build', desc: 'Tangible physical creation', icon: '🛠️' },
              { title: 'Share', desc: 'Teaching for mastery', icon: '📢' },
            ].map((step, i) => (
              <div
                key={i}
                className="p-8 bg-white border-2 border-[#E7DAC3] rounded-[3rem] space-y-4 hover:border-[#BD6809] transition-all group"
              >
                <div className="text-4xl mb-6 grayscale group-hover:grayscale-0 transition-all">{step.icon}</div>
                <h4 className="font-bold text-xl" style={{ fontFamily: 'var(--font-emilys-candy), "Emilys Candy", cursive' }}>
                  {step.title}
                </h4>
                <p className="text-xs font-bold uppercase tracking-widest opacity-40">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 px-6 mb-32">
        <div className="max-w-6xl mx-auto bg-[#BD6809] rounded-[4rem] p-16 md:p-24 text-white text-center space-y-12 shadow-2xl relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-full bg-[#6B1D2A] opacity-0 group-hover:opacity-10 transition-opacity duration-700" />
          <h2
            className="text-6xl md:text-7xl lg:text-8xl font-normal leading-none tracking-tighter relative z-10"
            style={{ fontFamily: 'var(--font-emilys-candy), "Emilys Candy", cursive' }}
          >
            Reclaim <br />
            Their <span className="italic">Wonder</span>
          </h2>
          <p className="text-xl text-white/80 max-w-xl mx-auto font-medium relative z-10">
            Join a community of families proving that education is an adventure, and mastery is its own reward.
          </p>
          <div className="flex flex-col sm:flex-row gap-6 justify-center relative z-10">
            <Link
              href="/pricing"
              className="px-16 py-7 rounded-full bg-white text-[#6B1D2A] font-black uppercase tracking-[0.2em] text-sm shadow-xl hover:scale-105 transition-all"
            >
              Get Started
            </Link>
            <Link
              href="/login"
              className="px-16 py-7 rounded-full border-2 border-white text-white font-black uppercase tracking-[0.2em] text-sm hover:bg-white hover:text-[#BD6809] transition-all"
            >
              Log In
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-24 px-6 border-t border-[#E7DAC3] bg-white/50">
        <div className="max-w-7xl mx-auto grid md:grid-cols-2 justify-between items-center gap-10 opacity-60">
          <div className="flex items-center gap-4">
            <Image src="/adeline-nav.png" alt="Adeline" width={40} height={40} className="rounded-lg" />
            <span className="text-xl font-bold text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), "Emilys Candy", cursive' }}>
              Dear Adeline
            </span>
          </div>
          <div className="md:text-right space-y-2">
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-[#6B1D2A]">Oklahoma Homeschooling Reimagined</p>
            <p className="text-xs font-medium text-[#2F4731]/60">© {new Date().getFullYear()} Dear Adeline Co. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
