import Link from 'next/link';

export const metadata = {
  title: 'Children’s Privacy Notice | Dear Adeline',
  description: 'How Dear Adeline collects, uses, protects, retains, and deletes children’s information.',
};

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-[#F8F2E7] px-5 py-10 text-[#2F4731] sm:px-8">
      <article className="mx-auto max-w-3xl rounded-[28px] border border-[#D6C7AF] bg-[#FFFDF7] p-6 shadow-[0_18px_50px_rgba(62,50,33,.08)] sm:p-10">
        <Link href="/" className="text-sm font-black text-[#2F6542]">← Dear Adeline</Link>
        <p className="mt-8 text-xs font-black uppercase tracking-[.18em] text-[#9A3F4A]">Effective August 23, 2026</p>
        <h1 className="mt-2 text-4xl font-bold sm:text-5xl" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>Children&rsquo;s Privacy Notice</h1>
        <p className="mt-5 text-base leading-7 text-[#2F4731]/72">Dear Adeline is a family-directed learning service. Parents control accounts for children under 13 and may review, correct, export, or request deletion of their child&rsquo;s personal information.</p>

        <div className="mt-9 space-y-8 text-sm leading-7">
          <section><h2 className="text-2xl font-bold">Information we collect</h2><p className="mt-2">We collect only information needed to provide and secure the learning service: a learner name or display name, username, grade level, interests, parent contact and consent records, learning conversations, investigations, submitted work and evidence, mastery and transcript records, portfolio entries, and limited technical/security logs. We do not require precise location, government identifiers, biometric identifiers, advertising identifiers, or a child&rsquo;s phone number.</p></section>
          <section><h2 className="text-2xl font-bold">How we use it</h2><p className="mt-2">We use this information to authenticate family members, personalize learning, preserve the learner&rsquo;s educational record, show parents their connected family&rsquo;s progress, protect the service, respond to support requests, and meet legal obligations. We do not use children&rsquo;s information for targeted advertising, behavioral advertising, sale, or unrelated profiling.</p></section>
          <section><h2 className="text-2xl font-bold">Service providers</h2><p className="mt-2">We use contracted infrastructure, database, authentication, email, security, and artificial-intelligence service providers only to operate Dear Adeline. These providers may process the minimum information needed for their function. We require appropriate confidentiality, security, and data-processing protections before children&rsquo;s information is released to a provider. We do not permit providers to use children&rsquo;s information for their own advertising.</p></section>
          <section><h2 className="text-2xl font-bold">Parent choices</h2><p className="mt-2">A parent may ask what information we hold about their child, review or correct it, revoke consent, stop future collection, export the educational record, or request deletion. Revoking consent may end features that require the information, but it does not require agreeing to any unrelated data use.</p></section>
          <section><h2 className="text-2xl font-bold">Retention and deletion</h2><p className="mt-2">We retain account and active educational records while the family uses the service so learning, mastery, transcript, and portfolio history remain available. Expired verification tokens are deleted or invalidated promptly. Security logs are kept only for the period reasonably needed to detect abuse and investigate incidents. When a parent requests account deletion, we delete or de-identify children&rsquo;s personal information after resolving legal, security, backup, and record-delivery needs. We do not retain children&rsquo;s information indefinitely or for a new purpose unrelated to the reason it was collected.</p></section>
          <section><h2 className="text-2xl font-bold">Security</h2><p className="mt-2">Dear Adeline uses encrypted connections, hashed learner PINs, verified signed sessions, least-privilege data access, parent–child ownership checks, private evidence storage, rate limits, backups, monitoring, and periodic security review. No system can guarantee perfect security; suspected incidents involving children&rsquo;s information receive priority investigation and response.</p></section>
          <section><h2 className="text-2xl font-bold">Contact</h2><p className="mt-2">Parents can make a privacy request or ask a question at <a href="mailto:privacy@dearadeline.co" className="font-bold text-[#9A3F4A] underline">privacy@dearadeline.co</a>. Please do not send sensitive student work by ordinary email; we will provide a secure method when needed.</p></section>
        </div>
      </article>
    </main>
  );
}
