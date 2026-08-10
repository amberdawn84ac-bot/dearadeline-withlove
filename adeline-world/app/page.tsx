const features = [
  ["♡", "Student-Led Learning", "Your student tells Adeline what they’re interested in. Curiosity becomes meaningful curriculum."],
  ["◎", "Skills & Credits Tracking", "Everything learned earns skills and builds clearly toward graduation requirements."],
  ["⌁", "Graduation Tracker", "See what is complete, what is growing, and what still needs attention."],
  ["▤", "Portfolio Builder", "Projects, lessons, and achievements become a beautiful record of real learning."],
  ["◌", "Gap Detection", "Adeline notices missing foundations and gently works them into meaningful projects."],
  ["✦", "Learning Missions", "Real investigations, creations, and challenges make education feel alive."],
];

export default function Home() {
  return (
    <main>
      <section className="cover" aria-label="Dear Adeline">
        <div className="cover-page">
          <img
            src="/landing-illustration.png"
            alt="Education as unique as your child, with Adeline and a child exploring an open book"
          />
          <a href="/sign-in" className="start-button">
            Start Your Adventure Today!
          </a>
        </div>
      </section>

      <section className="conversation-section" id="della">
        <div className="conversation-intro">
          <p>Learning starts with a conversation</p>
          <h2>Adeline listens before she teaches.</h2>
          <span>
            She begins with what your child already loves and turns it into
            projects, skills, and progress toward graduation.
          </span>
        </div>

        <div className="chat-example">
          <div className="chat-heading">
            <img src="/adeline-face.png" alt="Adeline" />
            <div>
              <small>AI LEARNING COMPANION</small>
              <strong>Adeline</strong>
            </div>
            <i aria-label="Online" />
          </div>
          <div className="messages">
            <p className="adeline-message">Hi Della! What are you excited to learn about today? ☀️</p>
            <p className="della-message">I want to grow my crochet business!</p>
            <p className="adeline-message">That’s amazing! 🧶 Do you have a website to sell your products yet?</p>
          </div>
        </div>
      </section>

      <section className="features" id="features">
        <p>Why Dear Adeline?</p>
        <h2>Learning That Grows With You</h2>
        <span>Personal enough to follow their wonder. Structured enough to help them graduate.</span>
        <div className="feature-grid">
          {features.map(([icon, title, description]) => (
            <article key={title}>
              <b>{icon}</b>
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
