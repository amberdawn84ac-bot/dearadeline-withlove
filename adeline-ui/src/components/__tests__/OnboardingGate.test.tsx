import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { OnboardingGate } from '../OnboardingGate';

const getSession = vi.fn();
let pathname = '/dashboard';

vi.mock('next/navigation', () => ({
  usePathname: () => pathname,
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: (...args: unknown[]) => getSession(...args),
    },
  },
}));

describe('OnboardingGate', () => {
  beforeEach(() => {
    pathname = '/dashboard';
    getSession.mockReset();
    vi.stubGlobal('fetch', vi.fn());
    // jsdom's location.href is not assignable; stub a writable stand-in.
    Object.defineProperty(window, 'location', {
      value: { href: 'http://localhost/dashboard' },
      writable: true,
    });
  });

  it('sends an unauthenticated visitor on a protected route to login', async () => {
    getSession.mockResolvedValue({ data: { session: null }, error: null });
    render(<OnboardingGate />);
    await waitFor(() => {
      expect(window.location.href).toBe('/login');
    });
  });

  it('sends an authenticated visitor who has not finished onboarding to /onboarding', async () => {
    getSession.mockResolvedValue({
      data: { session: { access_token: 'token' } },
      error: null,
    });
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ user: { onboardingComplete: false } }),
    });
    render(<OnboardingGate />);
    await waitFor(() => {
      expect(window.location.href).toBe('/onboarding');
    });
  });

  it('leaves a finished learner on the dashboard', async () => {
    getSession.mockResolvedValue({
      data: { session: { access_token: 'token' } },
      error: null,
    });
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ user: { onboardingComplete: true } }),
    });
    render(<OnboardingGate />);
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });
    expect(window.location.href).toBe('http://localhost/dashboard');
  });
});
