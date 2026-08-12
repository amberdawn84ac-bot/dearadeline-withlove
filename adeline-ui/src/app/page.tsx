import Link from 'next/link';
import Image from 'next/image';
import { HomeLessonDemo } from '@/components/HomeLessonDemo';

export default function Home() {
  return (
    <main className="min-h-screen bg-[#dfe4d8] text-[#232820]">
      <section className="relative overflow-hidden px-5 pb-20 pt-8 sm:px-8 lg:px-12 lg:pt-10">
        <div className="pointer-events-none absolute -left-24 top-12 h-[460px] w-[460px] rounded-full bg-white/20 blur-[100px]" />
        <div className="pointer-events-none absolute -bottom-44 right-[-100px] h-[540px] w-[540px] rounded-full bg-[#9aa58f]/25 blur-[110px]" />

        <div className="relative mx-auto grid max-w-[1500px] items-center gap-12 lg:grid-cols-[0.88fr_1.12fr] xl:gap-20">
          <div className="relative z-20 pt-4 lg:pt-0">
            <h1
              className="max-w-[670px] text-[62px] font-normal leading-[0.9] tracking-[-0.045em] text-[#232820] sm:text-[76px] md:text-[90px] lg:text-[96px] xl:text-[108px]"
              style={{ fontFamily: 'var(--font-emilys-candy), "Emilys Candy", cursive' }}
            >
              Education
              <br />
              As Unique As
              <br />
              Your Child
            </h1>

            <p className="mt-8 max-w-[560px] text-[18px] leading-8 text-[#4d574b] sm:text-[19px]">
              A living education that follows your child&apos;s curiosity, turns real interests into real learning, and quietly keeps them moving toward graduation.
            </p>

            <div className="mt-9 flex flex-wrap gap-4">
              <Link
                href="/login"
                className="inline-flex items-center justify-center rounded-full bg-[#c88a18] px-7 py-3.5 text-sm font-bold text-white shadow-[0_14px_30px_rgba(107,72,10,0.2)] transition-transform hover:-translate-y-0.5"
              >
                Meet Adeline
              </Link>
              <Link
                href="#how-it-works"
                className="inline-flex items-center justify-center rounded-full border border-[#8f9989] bg-white/20 px-7 py-3.5 text-sm font-semibold text-[#3e463c] hover:bg-white/45"
              >
                See How It Works
              </Link>
            </div>
          </div>

          <div className="relative z-10 lg:pl-3">
            <div className="overflow-hidden rounded-[30px] border border-[#b5bdae] bg-[#f3f1e8]/88 shadow-[0_24px_70px_rgba(67,77,61,0.18)]">
              <div className="flex items-center gap-4 border-b border-[#c9cec3] bg-[#e8e8de]/92 px-6 py-4">
                <Image src="/adeline-nav.png" alt="Adeline" width={52} height={52} className="rounded-full object-cover" />
                <div>
                  <div
                    className="text-[22px] leading-none text-[#252b23]"
                    style={{ fontFamily: 'var(--font-emilys-candy), "Emilys Candy", cursive' }}
                  >
                    Adeline
                  </div>
                  <div className="mt-1 text-[12px] text-[#6d7568]">Your learning companion</div>
                </div>
              </div>

              <div className="space-y-4 px-6 py-5 sm:px-7 sm:py-6">
                <div className="max-w-[82%] rounded-[18px] rounded-tl-[5px] border border-[#d2d5cd] bg-white/80 px-4 py-3 text-[15px] leading-6 text-[#3e463d] shadow-sm">
                  Hi Della! What are you excited to learn about today?
                </div>

                <div className="ml-auto max-w-[62%] rounded-[18px] rounded-tr-[5px] bg-[#9ba394] px-4 py-3 text-[15px] leading-6 text-white shadow-sm">
                  I want to grow my crochet business!
                </div>

                <div className="max-w-[86%] rounded-[18px] rounded-tl-[5px] border border-[#d2d5cd] bg-white/80 px-4 py-3 text-[15px] leading-6 text-[#3e463d] shadow-sm">
                  That&apos;s exciting. Do you have a website to show your work yet?
                </div>

                <div className="ml-auto max-w-[42%] rounded-[18px] rounded-tr-[5px] bg-[#9ba394] px-4 py-3 text-[15px] leading-6 text-white shadow-sm">
                  No, not yet...
                </div>

                <div className="max-w-[94%] rounded-[18px] rounded-tl-[5px] border border-[#d2d5cd] bg-white/85 px-4 py-3 text-[15px] leading-6 text-[#3e463d] shadow-sm">
                  <p>Perfect. Let&apos;s build one together.</p>
                  <p className="mt-1 text-[#687164]">You&apos;ll learn web design, marketing, pricing, writing, and entrepreneurship while making something your business can actually use.</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {['Web Design', 'Marketing', 'Entrepreneurship'].map((tag) => (
                      <span key={tag} className="rounded-full bg-[#dae0d4] px-3 py-1 text-[11px] font-semibold text-[#566052]">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="border-t border-[#d0d4cb] bg-[#ebece4]/75 px-6 py-3 text-center text-[10px] font-semibold uppercase tracking-[0.14em] text-[#7a8275]">
                Skills quietly tracked toward graduation
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="how-it-works" className="bg-[#f7f5ee] px-5 py-24 sm:px-8 lg:px-12">
        <div className="mx-auto max-w-[1200px] text-center">
          <p className="text-[11px] font-black uppercase tracking-[0.28em] text-[#c27a23]">How it works</p>
          <h2
            className="mt-4 text-5xl text-[#293027] sm:text-6xl"
            style={{ fontFamily: 'var(--font-emilys-candy), "Emilys Candy", cursive' }}
          >
            Start with wonder. Build from there.
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-[17px] leading-7 text-[#687064]">
            Adeline starts with what a child actually wants to know or make, then connects the science, math, history, writing, research, and real-world skills hiding inside it.
          </p>
          <div className="mt-12">
            <HomeLessonDemo />
          </div>
        </div>
      </section>

      <section id="about" className="bg-[#dfe4d8] px-5 py-24 sm:px-8 lg:px-12">
        <div className="mx-auto max-w-[1000px] text-center">
          <h2
            className="text-5xl text-[#293027] sm:text-6xl"
            style={{ fontFamily: 'var(--font-emilys-candy), "Emilys Candy", cursive' }}
          >
            Let them keep their wonder.
          </h2>
          <p className="mx-auto mt-5 max-w-3xl text-[18px] leading-8 text-[#596257]">
            Dear Adeline is designed so the student sees missions, questions, books, projects, games, discoveries, and conversations. The academic machinery stays underneath, where it belongs.
          </p>
        </div>
      </section>
    </main>
  );
}
