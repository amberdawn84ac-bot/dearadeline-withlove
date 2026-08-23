import Link from 'next/link';

export default function CoppaPendingPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#F8F2E7] px-5 py-10 text-[#2F4731]">
      <section className="w-full max-w-lg rounded-[28px] border border-[#D6C7AF] bg-[#FFFDF7] p-8 text-center shadow-[0_18px_50px_rgba(62,50,33,.08)]">
        <p className="text-5xl">✉️</p>
        <h1 className="mt-5 text-3xl font-bold" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>Waiting for parent approval</h1>
        <p className="mt-4 text-sm leading-6 text-[#2F4731]/68">The learner profile is reserved, but learning access remains closed. We sent the parent or guardian a review link that expires in 72 hours.</p>
        <p className="mt-3 text-xs leading-5 text-[#2F4731]/55">The parent must read the privacy notice, confirm they are the parent or legal guardian, and actively approve the account.</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link href="/privacy" className="rounded-xl border border-[#CFC1A8] bg-white px-4 py-2.5 text-sm font-bold">Privacy notice</Link>
          <Link href="/login" className="rounded-xl bg-[#2F4731] px-4 py-2.5 text-sm font-bold text-white">Return to sign in</Link>
        </div>
      </section>
    </main>
  );
}
