// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import markdoc from '@astrojs/markdoc';
import keystatic from '@keystatic/astro';
import cloudflare from '@astrojs/cloudflare';

// https://astro.build/config
export default defineConfig({
  // Update this to the site's production URL (used for canonical links and sitemaps).
  site: 'https://example.com',
  // The site itself is fully static. The adapter only serves Keystatic's /api/keystatic
  // routes (GitHub sign-in) and the /keystatic admin UI; every content page is prerendered.
  output: 'static',
  adapter: cloudflare(),
  integrations: [react(), markdoc(), keystatic()],
  trailingSlash: 'ignore',
  redirects: {
    '/admin': '/keystatic',
  },
});
