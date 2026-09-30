// @ts-check
import { defineConfig } from 'astro/config';

// https://astro.build/config
export default defineConfig({
  // Update this to the site's production URL (used for canonical links and sitemaps).
  site: 'https://example.com',
  output: 'static',
  trailingSlash: 'ignore',
});
