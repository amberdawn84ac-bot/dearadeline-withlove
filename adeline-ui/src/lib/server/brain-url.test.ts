import { afterEach, describe, expect, it } from 'vitest';
import { PUBLIC_BRAIN_URL, resolveBrainBaseUrl } from './brain-url';

const ENV_KEYS = ['VERCEL', 'BRAIN_INTERNAL_URL', 'BRAIN_URL', 'NEXT_PUBLIC_BRAIN_URL'] as const;

function setEnv(values: Partial<Record<(typeof ENV_KEYS)[number], string | undefined>>) {
  for (const key of ENV_KEYS) {
    const value = values[key];
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
}

describe('resolveBrainBaseUrl', () => {
  afterEach(() => {
    setEnv({
      VERCEL: undefined,
      BRAIN_INTERNAL_URL: undefined,
      BRAIN_URL: undefined,
      NEXT_PUBLIC_BRAIN_URL: undefined,
    });
  });

  it('uses the Docker hostname when not on Vercel', () => {
    setEnv({ BRAIN_INTERNAL_URL: 'http://adeline-brain:8000/' });
    expect(resolveBrainBaseUrl()).toBe('http://adeline-brain:8000');
  });

  it('ignores the Docker hostname on Vercel and uses the public Railway origin', () => {
    setEnv({
      VERCEL: '1',
      BRAIN_INTERNAL_URL: 'http://adeline-brain:8000',
      NEXT_PUBLIC_BRAIN_URL: 'https://www.dearadeline.co',
    });
    expect(resolveBrainBaseUrl()).toBe(PUBLIC_BRAIN_URL);
  });

  it('keeps a Railway URL even on Vercel', () => {
    setEnv({
      VERCEL: '1',
      BRAIN_INTERNAL_URL: 'https://dearadeline-withlove-production.up.railway.app/brain',
    });
    expect(resolveBrainBaseUrl()).toBe('https://dearadeline-withlove-production.up.railway.app');
  });

  it('does not loop Brain through the public site', () => {
    setEnv({ BRAIN_URL: 'https://www.dearadeline.co/brain' });
    expect(resolveBrainBaseUrl()).toBe(PUBLIC_BRAIN_URL);
  });
});
