'use client';

import type { SceneVisual as Visual } from '@/lib/classroom-client';

export default function SceneVisual({ visual, activeId }: { visual: Visual; activeId?: string | null }) {
  return <section aria-label="Visual explanation" className="my-6 space-y-4">
    <p className="text-lg leading-8">{visual.reading}</p>
    <div className="grid gap-4">
      {visual.elements.map(element => {
        const marked = activeId === element.id;
        const frame = `rounded-2xl border border-[#d9cfbc] bg-white p-4 ${marked ? 'ring-2 ring-[#bba978] ring-offset-2' : ''}`;
        if (element.type === 'chart' && element.labels && element.values) {
          const max = Math.max(...element.values.map(value => Math.abs(value)), 1);
          return <figure key={element.id} id={`visual-${element.id}`} className={frame}>
            <figcaption className="font-semibold">{element.text || 'Comparison'}</figcaption>
            <svg viewBox={`0 0 320 ${element.labels.length * 36 + 8}`} role="img" aria-label={element.alt || element.text || 'Chart'} className="mt-3 w-full">
              {element.labels.map((label, index) => <g key={label}>
                <text x="0" y={22 + index * 36} fontSize="14" fill="#183d32">{label.slice(0, 18)}</text>
                <rect x="110" y={8 + index * 36} height="18" width={Math.max(4, (Math.abs(element.values![index]) / max) * 200)} fill="#a27e32" />
              </g>)}
            </svg>
          </figure>;
        }
        if (element.type === 'table' && element.headers && element.rows) {
          return <div key={element.id} id={`visual-${element.id}`} className={`${frame} overflow-x-auto`}>
            <table className="w-full text-left text-sm"><caption className="mb-2 text-left font-semibold">{element.text || 'Table'}</caption>
              <thead><tr>{element.headers.map(header => <th key={header} className="border-b p-2">{header}</th>)}</tr></thead>
              <tbody>{element.rows.map((row, index) => <tr key={index}>{row.map((cell, cellIndex) => <td key={cellIndex} className="border-b p-2">{cell}</td>)}</tr>)}</tbody>
            </table>
          </div>;
        }
        if (element.type === 'image') {
          return <figure key={element.id} id={`visual-${element.id}`} className={frame}>
            {element.url?.startsWith('https://') && <img src={element.url} alt={element.alt || ''} className="h-auto max-h-80 w-full rounded-xl object-contain" />}
            <figcaption className="mt-2 leading-7">{element.alt || element.text}</figcaption>
          </figure>;
        }
        return <div key={element.id} id={`visual-${element.id}`} className={frame}>
          {element.type === 'formula' ? <p className="font-mono text-xl">{element.text}</p> : <p className="text-lg leading-8">{element.text}</p>}
        </div>;
      })}
    </div>
  </section>;
}
