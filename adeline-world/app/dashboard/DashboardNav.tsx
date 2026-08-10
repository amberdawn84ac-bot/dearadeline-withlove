const items = [
  ["today", "☀", "Today", "/dashboard"],
  ["adeline", "♡", "Talk to Adeline", "/dashboard#talk-to-adeline"],
  ["missions", "✦", "My Missions", "/dashboard/missions"],
  ["journal", "▤", "Journal", "/dashboard/journal"],
  ["portfolio", "▧", "Portfolio", "/dashboard/portfolio"],
  ["skills", "◎", "Skills & Credits", "/dashboard/skills"],
  ["graduation", "⌁", "Graduation Path", "/dashboard/graduation"],
  ["game", "◈", "Game Portal", "/game-portal"],
] as const;

export default function DashboardNav({ active }: { active: string }) {
  return (
    <aside className="dashboard-sidebar" aria-label="Dashboard menu">
      <nav className="dashboard-menu">
        {items.map(([id, icon, label, href]) => (
          <a className={active === id ? "active" : ""} href={href} key={id} aria-current={active === id ? "page" : undefined}>
            <b>{icon}</b><span>{label}</span>
          </a>
        ))}
      </nav>
      <article className="daily-bread">
        <div className="bread-heading"><span>DAILY BREAD</span><b>❦</b></div>
        <blockquote>“The beginning of wisdom is this: Get wisdom.”</blockquote>
        <cite>Proverbs 4:7</cite><hr />
        <p>Wisdom begins when you are willing to notice what you do not yet know.</p>
        <strong>Today’s practice</strong><span>Ask one honest question—and follow it.</span>
      </article>
    </aside>
  );
}
