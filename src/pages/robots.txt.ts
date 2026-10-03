import type { APIRoute } from 'astro';
import { getSettings } from '../lib/content';

// Mirrors the "Hide this site from search engines" switch in Site Settings.
export const GET: APIRoute = async () => {
  const { noindex } = await getSettings();
  const body = noindex ? 'User-agent: *\nDisallow: /\n' : 'User-agent: *\nAllow: /\n';
  return new Response(body, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};
