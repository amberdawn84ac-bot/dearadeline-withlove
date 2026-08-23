const RESEND_API_KEY = process.env.RESEND_API_KEY ?? '';
const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? 'https://dearadeline.co';
const FROM_EMAIL = 'Adeline <no-reply@dearadeline.co>';

function escapeHtml(value: string) {
  return value.replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[character] ?? character);
}

export function coppaVerificationUrl(token: string) {
  return `${APP_URL}/coppa-verify?token=${encodeURIComponent(token)}`;
}

export async function sendCoppaVerificationEmail(input: {
  parentEmail: string;
  parentName: string;
  studentName: string;
  verifyUrl: string;
}): Promise<void> {
  if (!RESEND_API_KEY) throw new Error('Parental-consent email service is not configured.');
  const parentName = escapeHtml(input.parentName);
  const studentName = escapeHtml(input.studentName);
  const verifyUrl = escapeHtml(input.verifyUrl);
  const html = `
    <div style="font-family:Georgia,serif;max-width:560px;margin:0 auto;color:#2F4731">
      <h2>Hello, ${parentName}</h2>
      <p>${studentName} requested a Dear Adeline learner account. No learning access will be activated until a parent or legal guardian reviews the privacy notice and gives consent.</p>
      <p><a href="${verifyUrl}" style="background:#BD6809;color:#fff;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block">Review and approve the account</a></p>
      <p style="font-size:13px;color:#666">The link expires in 72 hours. If you did not expect this request, do not approve it.</p>
      <p style="font-size:12px;color:#777">Before approving, read the Children’s Privacy Notice at ${escapeHtml(`${APP_URL}/privacy`)}.</p>
    </div>`;
  const response = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${RESEND_API_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from: FROM_EMAIL,
      to: [input.parentEmail],
      subject: `Review ${input.studentName}'s Dear Adeline account`,
      html,
    }),
  });
  if (!response.ok) throw new Error(`Consent email failed (${response.status}).`);
}
