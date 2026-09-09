'use client';

function youtubeEmbed(url: string): string | null {
  try {
    const parsed = new URL(url);
    if (parsed.hostname.includes('youtu.be')) {
      const id = parsed.pathname.replace('/', '').trim();
      return id ? `https://www.youtube.com/embed/${id}` : null;
    }
    if (parsed.hostname.includes('youtube.com')) {
      const id = parsed.searchParams.get('v');
      return id ? `https://www.youtube.com/embed/${id}` : null;
    }
  } catch {
    return null;
  }
  return null;
}

export function OfferedResourceCard({ resource }: { resource: Record<string, unknown> }) {
  const url = String(resource.editor_url || resource.embed_url || resource.source_url || '');
  const title = String(resource.title || 'Resource');
  const kind = String(resource.resource_type || '').replaceAll('_', ' ');
  const thumbnail = typeof resource.thumbnail_url === 'string' ? resource.thumbnail_url : '';
  const description = typeof resource.description === 'string' ? resource.description : '';
  const embed = url ? youtubeEmbed(url) : null;
  const showPhoto = Boolean(thumbnail) && !embed;

  return (
    <article className="overflow-hidden rounded-2xl border border-[#D9CFBC] bg-white">
      {embed ? (
        <div className="aspect-video bg-black">
          <iframe
            src={embed}
            title={title}
            className="h-full w-full border-0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>
      ) : showPhoto ? (
        <img src={thumbnail} alt={title} className="h-40 w-full object-cover" />
      ) : null}
      <div className="p-4">
        <p className="text-xs font-black uppercase tracking-wider text-[#BD6809]">
          {String(resource.provider || '')}{kind ? ` · ${kind}` : ''}
        </p>
        <h3 className="mt-2 font-bold text-[#2F4731]">{title}</h3>
        {description ? <p className="mt-1 text-sm leading-6 text-[#2F4731]/65">{description}</p> : null}
        {url ? (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 inline-flex min-h-11 items-center rounded-xl bg-[#2F4731] px-4 py-2 text-sm font-bold text-white no-underline"
          >
            {embed || kind === 'VIDEO' ? 'Watch' : (thumbnail || kind === 'IMAGE') ? 'Look closely' : 'Open'}
          </a>
        ) : null}
      </div>
    </article>
  );
}
