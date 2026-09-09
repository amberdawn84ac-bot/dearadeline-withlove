'use client';

import { useState } from 'react';

function youtubeEmbed(url: string): string | null {
  try {
    const parsed = new URL(url);
    if (parsed.hostname.includes('youtu.be')) {
      const id = parsed.pathname.replace('/', '').trim();
      return id ? `https://www.youtube.com/embed/${id}` : null;
    }
    if (parsed.hostname.includes('youtube.com')) {
      // Only a real watch URL carries ?v=; channel/search links do not embed.
      const id = parsed.searchParams.get('v');
      return id ? `https://www.youtube.com/embed/${id}` : null;
    }
  } catch {
    return null;
  }
  return null;
}

function httpUrl(value: unknown): string {
  const text = typeof value === 'string' ? value.trim() : '';
  return /^https?:\/\//i.test(text) ? text : '';
}

export function OfferedResourceCard({ resource }: { resource: Record<string, unknown> }) {
  const [imageBroken, setImageBroken] = useState(false);

  const url = httpUrl(resource.editor_url) || httpUrl(resource.embed_url) || httpUrl(resource.source_url);
  const title = String(resource.title || 'Resource');
  const kind = String(resource.resource_type || '').replaceAll('_', ' ');
  const thumbnail = httpUrl(resource.thumbnail_url);
  const description = typeof resource.description === 'string' ? resource.description : '';
  const provider = String(resource.provider || '');
  const embed = url ? youtubeEmbed(url) : null;
  const showPhoto = Boolean(thumbnail) && !embed && !imageBroken;
  const label = embed || kind === 'VIDEO'
    ? 'Watch'
    : thumbnail || kind === 'IMAGE'
      ? 'Look closely'
      : 'Open';

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
        <img
          src={thumbnail}
          alt={title}
          className="h-40 w-full object-cover"
          loading="lazy"
          onError={() => setImageBroken(true)}
        />
      ) : null}
      <div className="p-4">
        {(provider || kind) ? (
          <p className="text-xs font-black uppercase tracking-wider text-[#BD6809]">
            {provider}{provider && kind ? ' · ' : ''}{kind}
          </p>
        ) : null}
        <h3 className="mt-2 font-bold text-[#2F4731]">{title}</h3>
        {description ? <p className="mt-1 text-sm leading-6 text-[#2F4731]/65">{description}</p> : null}
        {url ? (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 inline-flex min-h-11 items-center rounded-xl bg-[#2F4731] px-4 py-2 text-sm font-bold text-white no-underline"
          >
            {label}
          </a>
        ) : null}
      </div>
    </article>
  );
}
