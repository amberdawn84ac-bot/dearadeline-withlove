import Link from 'next/link';
import styles from './sites-home.module.css';

const LANDING_ART =
  'https://raw.githubusercontent.com/amberdawn84ac-bot/dearadeline-withlove/main/adeline-world/public/landing-illustration.png';
const ADELINE_FACE =
  'https://raw.githubusercontent.com/amberdawn84ac-bot/dearadeline-withlove/main/adeline-world/public/adeline-face.png';

const features = [
  ['♡', 'Student-Led Learning', 'Your student tells Adeline what they’re interested in. Curiosity becomes meaningful curriculum.'],
  ['◎', 'Skills & Credits Tracking', 'Everything learned earns skills and builds clearly toward graduation requirements.'],
  ['⌁', 'Graduation Tracker', 'See what is complete, what is growing, and what still needs attention.'],
  ['▤', 'Portfolio Builder', 'Projects, lessons, and achievements become a beautiful record of real learning.'],
  ['◌', 'Gap Detection', 'Adeline notices missing foundations and gently works them into meaningful projects.'],
  ['✦', 'Learning Missions', 'Real investigations, creations, and challenges make education feel alive.'],
];

export default function Home() {
  return (
    <main className={styles.page}>
      <section className={styles.cover} aria-label="Dear Adeline">
        <div className={styles.coverPage}>
          <img
            src={LANDING_ART}
            alt="Education as unique as your child, with Adeline and a child exploring together"
          />
          <Link href="/dashboard" className={styles.startButton}>
            Start Your Adventure Today!
          </Link>
        </div>
      </section>

      <section className={styles.conversationSection} id="della">
        <div className={styles.conversationIntro}>
          <p>Learning starts with a conversation</p>
          <h2>Adeline listens before she teaches.</h2>
          <span>
            She begins with what your child already loves and turns it into
            projects, skills, and progress toward graduation.
          </span>
        </div>

        <div className={styles.chatExample}>
          <div className={styles.chatHeading}>
            <img src={ADELINE_FACE} alt="Adeline" />
            <div>
              <small>AI LEARNING COMPANION</small>
              <strong>Adeline</strong>
            </div>
            <i aria-label="Online" />
          </div>
          <div className={styles.messages}>
            <p className={styles.adelineMessage}>Hi Della! What are you excited to learn about today? ☀️</p>
            <p className={styles.dellaMessage}>I want to grow my crochet business!</p>
            <p className={styles.adelineMessage}>That’s amazing! 🧶 Do you have a website to sell your products yet?</p>
          </div>
        </div>
      </section>

      <section className={styles.features} id="features">
        <p>Why Dear Adeline?</p>
        <h2>Learning That Grows With You</h2>
        <span>Personal enough to follow their wonder. Structured enough to help them graduate.</span>
        <div className={styles.featureGrid}>
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
