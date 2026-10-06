// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import markdoc from '@astrojs/markdoc';
import keystatic from '@keystatic/astro';
import cloudflare from '@astrojs/cloudflare';
import { readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

// `virtual:uploads`: a build-time index of public/uploads for the /media page. Pages are
// prerendered by the Cloudflare adapter without Node's fs, so the list is baked in here.
function uploadsIndex() {
  const id = 'virtual:uploads';
  const list = () => {
    const root = 'public/uploads';
    const files = [];
    const walk = (dir) => {
      for (const entry of readdirSync(dir, { withFileTypes: true })) {
        if (entry.name.startsWith('.')) continue;
        const full = join(dir, entry.name);
        if (entry.isDirectory()) walk(full);
        else files.push({ path: '/uploads/' + relative(root, full).split('\\').join('/'), size: statSync(full).size });
      }
    };
    try { walk(root); } catch { /* no uploads yet */ }
    return files;
  };
  return {
    name: 'uploads-index',
    hooks: {
      'astro:config:setup': ({ updateConfig }) =>
        updateConfig({
          vite: {
            plugins: [{
              name: 'uploads-index',
              resolveId: (source) => (source === id ? '\0' + id : undefined),
              load: (source) => (source === '\0' + id ? `export default ${JSON.stringify(list())};` : undefined),
            }],
          },
        }),
    },
  };
}

// https://astro.build/config
export default defineConfig({
  // Update this to the site's production URL (used for canonical links and sitemaps).
  site: 'https://keystatic.farhan.app',
  // The site itself is fully static. The adapter only serves Keystatic's /api/keystatic
  // routes (GitHub sign-in) and the /keystatic admin UI; every content page is prerendered.
  output: 'static',
  adapter: cloudflare(),
  integrations: [react(), markdoc(), keystatic(), uploadsIndex()],
  trailingSlash: 'ignore',
  redirects: {
    '/admin': '/keystatic',
  },
});
