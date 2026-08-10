"use client";

import { FormEvent, useMemo, useState } from "react";

const passes = [
  { id: 0, label: "First telling", note: "The essential story" },
  { id: 1, label: "Return deeper", note: "Words, places, people" },
  { id: 2, label: "Investigate", note: "Evidence, empires, motives" },
  { id: 3, label: "Connect", note: "Power, consequences, today" },
];

const story = [
  { kind: "adeline", text: "Before we race into dates, kings, wars, and inventions, we have to begin where the Hebrew story begins—not with Rome, not with an English translation, but with one Hebrew word: Bereshit." },
  { kind: "text", text: "בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ", sub: "Bereshit bara Elohim et ha-shamayim ve-et ha-aretz · Genesis 1:1" },
  { kind: "adeline", text: "A careful traditional rendering is: “In the beginning, Elohim created the heavens and the earth.” But Hebrew grammar also permits: “When Elohim began to create the heavens and the earth…” with the sentence continuing through the next verses. I will show you genuine translation questions instead of hiding them." },
  { kind: "illustration", text: "The story opens with the unformed deep. Order, distinction, life, and purpose unfold through Elohim’s speech." },
  { kind: "adeline", text: "Notice the name actually present: Elohim. The four-letter name YHWH is not in this verse; YHWH Elohim first appears in Genesis 2:4. We will not silently replace one name with another." },
  { kind: "adeline", text: "Bara—“created”—is a singular verb here. Elohim has a plural-shaped ending, yet it takes that singular verb in this sentence. That is what the Hebrew says. Claims about why belong under interpretation, not translation." },
  { kind: "adeline", text: "“The heavens and the earth” is a Hebrew way of naming the whole ordered world—the totality, not merely two separate objects. History begins with a claim about whose world this is and what kind of world it is." },
];

const answers: Record<string, string> = {
  elohim: "Elohim is the noun used in Genesis 1:1. Its form looks plural, but bara, the verb connected to it, is singular. Hebrew can use Elohim for the Elohim of Israel and, in other contexts, for gods or divine beings. Context and grammar matter.",
  yhwh: "YHWH—יהוה—is not written in Genesis 1:1. Genesis 2:4 is the first place in Genesis where the combined form YHWH Elohim appears. Many English Bibles print LORD in small capitals instead of the four Hebrew letters.",
  beginning: "Bereshit can introduce an absolute statement, “In the beginning,” or a construct-like clause, “When … began.” The vowel pattern and the flow into verses 2–3 are why serious translators discuss both. We should not pretend the question does not exist.",
  bara: "Bara is commonly translated “created.” Genesis 1:1 does not itself contain a Hebrew phrase meaning “out of nothing.” Creation from nothing is a theological conclusion argued from the wider text and tradition; it should be labeled as interpretation rather than smuggled into this one verb.",
  translation: "One reading treats bereshit as the absolute opening: “In the beginning, Elohim created…” Another reads it as introducing a dependent clause: “When Elohim began to create…” The Hebrew consonants are the same. The grammar and relationship between verses 1–3 create the question; responsible translations disclose it.",
  catholic: "We will begin with the Hebrew textual witnesses, not treat a later denominational English Bible as the original. We will compare the Masoretic Text with older witnesses such as the Dead Sea Scrolls, the Samaritan Pentateuch, and the Greek Septuagint when a difference actually affects the passage.",
};

export default function HistoryPortal() {
  const [depth, setDepth] = useState(1);
  const [visible, setVisible] = useState(3);
  const [question, setQuestion] = useState("");
  const [asked, setAsked] = useState<{ q: string; a: string }[]>([]);
  const [sourcesOpen, setSourcesOpen] = useState(false);

  const availableStory = useMemo(() => story.slice(0, Math.min(story.length, 3 + depth * 2)), [depth]);

  function ask(text: string) {
    const normalized = text.toLowerCase();
    const key = Object.keys(answers).find((candidate) => normalized.includes(candidate));
    const answer = key ? answers[key] : "That question deserves a sourced answer, not a confident guess. I’ve marked it for investigation. For now, choose one of the source-backed questions below or continue the story.";
    setAsked((current) => [...current, { q: text, a: answer }]);
    setQuestion("");
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (question.trim()) ask(question.trim());
  }

  return (
    <main className="history-page">
      <header className="history-header">
        <a href="/game-portal">← Town map</a>
        <div><span>THE HISTORY PORTAL</span><strong>Truth has a trail.</strong></div>
        <button type="button" onClick={() => setSourcesOpen(!sourcesOpen)}>Sources {sourcesOpen ? "×" : "↗"}</button>
      </header>

      <section className="history-layout">
        <aside className="spiral-panel">
          <div className="spiral-orbit" aria-label="Spiral history learning path">
            <div className="orbit ring-four"><span>Today</span></div>
            <div className="orbit ring-three"><span>Empires</span></div>
            <div className="orbit ring-two"><span>Peoples</span></div>
            <div className="orbit ring-one"><span>Origins</span></div>
            <b>בְּרֵאשִׁית<small>Bereshit</small></b>
          </div>
          <h2>History returns in widening circles.</h2>
          <p>Each pass begins again, adds harder evidence, and carries the story farther toward the present.</p>
          <div className="depth-picker">
            {passes.map((pass) => <button className={depth === pass.id ? "active" : ""} key={pass.id} onClick={() => { setDepth(pass.id); setVisible(3); }} type="button"><b>{pass.label}</b><span>{pass.note}</span></button>)}
          </div>
          <div className="truth-method"><b>THE TRUTH METHOD</b><span>Primary text</span><span>Textual witness</span><span>Material evidence</span><span>Interpretation</span><span>Unknown / disputed</span></div>
        </aside>

        <section className="history-conversation">
          <div className="episode-heading">
            <div><span>ORIGINS · EPISODE 1</span><h1>Before the first kingdom</h1><p>Genesis 1:1 · Hebrew text and translation</p></div>
            <div className="evidence-status"><b>Source discipline on</b><span>No unsupported answer becomes a fact.</span></div>
          </div>

          <div className="history-chat" aria-live="polite">
            {availableStory.slice(0, visible).map((item, index) => (
              <div className={`history-message ${item.kind}`} key={index}>
                {item.kind === "adeline" && <img src="/adeline-face.png" alt="Adeline" />}
                {item.kind === "illustration" ? <figure><img src="/genesis-opening.png" alt="An artistic visualization of darkness, deep waters, and emerging light" /><figcaption>{item.text}<em>Artistic visualization—not evidence.</em></figcaption></figure> : <div><p>{item.text}</p>{item.sub && <small>{item.sub}</small>}{item.kind === "text" && <span>PRIMARY TEXT · MASORETIC HEBREW</span>}</div>}
              </div>
            ))}

            {asked.map((exchange, index) => <div className="question-exchange" key={index}><p>{exchange.q}</p><div><img src="/adeline-face.png" alt="Adeline" /><span>{exchange.a}</span></div></div>)}

            {visible < availableStory.length && <button className="continue-story" type="button" onClick={() => setVisible((count) => count + 1)}>Continue the story ↓</button>}
          </div>

          <div className="quick-questions">
            <span>Interrupt Adeline:</span>
            {["Why does it say Elohim?", "Where is the name YHWH?", "Does bara mean out of nothing?", "Why are there two translations?"].map((prompt) => <button type="button" key={prompt} onClick={() => ask(prompt)}>{prompt}</button>)}
          </div>
          <form className="history-composer" onSubmit={submit}><label htmlFor="history-question">Ask Adeline a question</label><input id="history-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Stop me—what do you want to examine?" /><button>Ask</button></form>
        </section>
      </section>

      {sourcesOpen && <aside className="source-drawer"><button type="button" onClick={() => setSourcesOpen(false)}>×</button><span>SOURCE DESK · EPISODE 1</span><h2>What this telling rests on</h2><article><b>Primary text</b><p>Masoretic Hebrew: Genesis 1:1–3. The displayed Hebrew is the text being translated.</p><a href="https://mechon-mamre.org/p/pt/pt0101.htm" target="_blank" rel="noreferrer">Read the Hebrew text ↗</a></article><article><b>Translation comparison</b><p>Both “In the beginning…” and “When Elohim began…” are disclosed because the Hebrew syntax has been read both ways.</p><a href="https://www.sefaria.org/Genesis.1.1?lang=bi" target="_blank" rel="noreferrer">Compare text and translation ↗</a></article><article><b>Claim labels</b><p>Text says what is present. Translation explains a rendering. Interpretation identifies a conclusion. Art never counts as evidence.</p></article><footer>Later episodes will add manuscripts, inscriptions, archaeology, contemporary records, and named historians—with disagreements shown, not erased.</footer></aside>}
    </main>
  );
}
