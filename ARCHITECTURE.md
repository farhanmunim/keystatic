# Architecture

A static Astro website whose content is edited in a browser with **Keystatic** and stored as
plain files in this GitHub repository. Hosted on a **Cloudflare Worker** (static assets plus a
small server part for the CMS).

Live site: <https://keystatic.farhan.app> · CMS: <https://keystatic.farhan.app/keystatic>

## The big picture

```
                         ┌──────────────────────────────┐
  Editor (browser)       │  GitHub: farhanmunim/keystatic │
  /keystatic  ──────────▶│  main branch                  │
      │  ▲               │   src/content/*  (Markdoc/YAML)│
      │  │ commits       │   public/uploads/* (media)     │
      │  │ via GitHub    └───────────────┬────────────────┘
      │  │ API                           │ push to main
      │  │                               ▼
      │  │               ┌──────────────────────────────┐
      │  │               │ Cloudflare Workers Builds     │
      │  │               │  npm run build                │
      │  │               │  npx wrangler deploy          │
      │  │               └───────────────┬────────────────┘
      ▼  │                               ▼
  ┌────────────────────────────────────────────────────┐
  │ Cloudflare Worker "keystatic"                       │
  │  • static assets (all public pages, /uploads, CSS)  │
  │  • server routes: /keystatic, /api/keystatic/*      │
  └────────────────────────────────────────────────────┘
      ▲
  Visitors ── keystatic.farhan.app (custom domain, zone farhan.app)
```

Content is never stored in a database. The repository is the database, and every edit is a
Git commit.

## Components

| Piece | What it is | Where |
| --- | --- | --- |
| Frontend | Astro 7, `output: 'static'`. Every public page is prerendered at build time | `src/pages`, `src/layouts`, `src/components` |
| Content schema | Astro content collections (Zod). Mirrors the CMS | `src/content.config.ts` |
| CMS | Keystatic (`@keystatic/core`, `@keystatic/astro`, React). Admin UI at `/keystatic` | `keystatic.config.ts` |
| Content files | Markdoc (`.mdoc`) for rich text, YAML (`.yaml`) for data | `src/content/<collection>/` |
| Media | One shared folder, served at `/uploads/...` | `public/uploads/` |
| Hosting adapter | `@astrojs/cloudflare`, builds a Worker with static assets | `astro.config.mjs` |
| Analytics | Self-hosted Umami at `mochi.farhan.app`, script injected from Site Settings | `head_html` in `src/content/settings/site.yaml` |

## Content model

Collections, defined in `keystatic.config.ts` and read by `src/content.config.ts`:

| Collection | Files | URL |
| --- | --- | --- |
| Pages | `src/content/pages/*.mdoc` | `/<slug>` |
| Posts | `src/content/posts/*.mdoc` | `/blog/<slug>` |
| Projects | `src/content/projects/*.mdoc` | `/projects/<slug>` |
| Services | `src/content/services/*.mdoc` | `/services/<slug>` |
| Resources | `src/content/resources/*.mdoc` | `/resources/<slug>` |
| Categories (nestable) | `src/content/categories/*.yaml` | `/category/<slug>` |
| Tags | `src/content/tags/*.yaml` | `/tags/<slug>` |
| Authors | `src/content/authors/*.mdoc` | `/authors/<slug>` |
| Site Settings (singleton) | `src/content/settings/site.yaml` | n/a |

Relations are stored as slugs (an author, tags and categories are file names). The `/docs` page
is the editor guide, and `/analytics` embeds the Umami share dashboard when its URL is set.

## Deployment (Cloudflare)

- **Worker name:** `keystatic`. It must match `name` in `package.json`, because the adapter
  generates the Wrangler config from it.
- **Git integration:** Workers Builds, connected to this repo, production branch `main`.
  - Build command: `npm run build`
  - Deploy command: `npx wrangler deploy`
  - Node version from `.node-version`.
- **What gets built:** `dist/client` (static assets) and `dist/server` (the Worker entry, plus a
  generated `wrangler.json`). The adapter also adds bindings: `ASSETS` (static files),
  `SESSION` (KV) and `IMAGES`.
- **Routing:** static files are served straight from assets. The Worker only runs for the
  non-prerendered routes that Keystatic injects: `/keystatic/*` and `/api/keystatic/*`.
  `/admin` redirects to `/keystatic`.
- **Domains:** custom domain `keystatic.farhan.app` (zone `farhan.app`) and the
  `keystatic.farhanmunim.workers.dev` URL.
- **Redeploy trigger:** any push to `main`. Saving or merging in Keystatic is such a push, so
  publishing content redeploys the site in about a minute or two.

## Authentication: GitHub App

Keystatic signs editors in with a **GitHub App** (not an OAuth App, which does not issue the
expiring and refresh tokens Keystatic needs). Anyone who can sign in with GitHub and has write
access to the repo can edit.

The app:

- Name `Keystatic CMS`, installed on `farhanmunim/keystatic` only.
- Callback URL: `https://keystatic.farhan.app/api/keystatic/github/oauth/callback`
- Permissions: Contents **read and write**, Pull requests **read**, Metadata read.
- "Expire user authorization tokens" and "Request user authorization during installation" on;
  webhooks off.

Sign-in flow:

1. Browser opens `/keystatic`. With no valid cookie, it goes to `/api/keystatic/github/login`.
2. GitHub asks the user to authorise the app and returns to
   `/api/keystatic/github/oauth/callback?code=...`.
3. The **Worker** exchanges the code for tokens, using `KEYSTATIC_GITHUB_CLIENT_ID` and
   `KEYSTATIC_GITHUB_CLIENT_SECRET`.
4. The Worker sets two cookies: the short-lived access token, and the refresh token, which is
   encrypted with `KEYSTATIC_SECRET` and `HttpOnly`.
5. After that, the Keystatic UI talks to the **GitHub API directly from the browser** with the
   access token: reading files, committing, creating branches and pull requests. The Worker
   only handles sign-in and token refresh.

### Configuration values

| Variable | Purpose | Set where |
| --- | --- | --- |
| `KEYSTATIC_GITHUB_CLIENT_ID` | GitHub App client ID | Cloudflare runtime secrets |
| `KEYSTATIC_GITHUB_CLIENT_SECRET` | GitHub App client secret | Cloudflare runtime secrets |
| `KEYSTATIC_SECRET` | Random 32+ character string that encrypts the refresh-token cookie | Cloudflare runtime secrets |
| `PUBLIC_KEYSTATIC_GITHUB_APP_SLUG` | App slug used to build GitHub install links. Inlined at **build time** | Cloudflare **build** variables (and runtime) |

See `.env.example`. Nothing secret is committed to the repo.

## Storage modes

`keystatic.config.ts` picks the mode from `import.meta.env.PROD`:

- **Development** (`npm run dev`): `local` storage. Keystatic reads and writes the files in your
  checkout, with no sign-in.
- **Production:** `github` storage for `farhanmunim/keystatic`.

Keystatic works on the repository's **default branch**, so the default branch on GitHub must be
`main`. Drafts are Git branches: create a branch in the editor, save there, open a pull request
and merge it to publish. Anything not on `main` never reaches the live site.

## Search engines (noindex)

Site Settings has a **Hide this site from search engines** switch (`noindex`), currently on.
It controls both:

- `<meta name="robots" content="noindex, nofollow">` on every page (`src/layouts/Layout.astro`);
- `/robots.txt`, generated from the same setting (`src/pages/robots.txt.ts`): `Disallow: /`
  when on, `Allow: /` when off.

Both are decided at build time, so changing the setting takes effect after the next deploy.

## Analytics

Umami is self-hosted at `mochi.farhan.app`. Its tracking snippet lives in Site Settings → Head
scripts and is injected into every page's `<head>` by the layout. The `/analytics` page embeds
a read-only Umami share URL if one is set in Site Settings.

## Content import from WordPress

`scripts/import-wordpress.py` is a one-off, re-runnable importer. It reads the headless
WordPress REST API at `https://cms.farhan.app/wp-json/wp/v2/` and writes Keystatic-format
files. It replaces the generated content each time it runs.

| WordPress | Keystatic |
| --- | --- |
| posts, categories, tags | posts, categories, tags |
| solutions | services |
| projects (with problem, approach, outcome, KPI fields) | projects (those fields become the body) |
| resources | resources |
| socials | Site Settings social links |
| the single user | the author |
| media library, inline diagrams | `public/uploads` |

Run it with `pip install beautifulsoup4` then `python3 scripts/import-wordpress.py`.

## Request lifecycle summary

- **Visitor:** Cloudflare edge, then the static asset from the Worker's asset store. No
  server code runs.
- **Editor:** `/keystatic` page and `/api/keystatic/*` run in the Worker. Content reads and
  writes go browser to GitHub. A commit to `main` starts a Workers Build, then a new deploy.

## Things to remember

- Rename the Worker, the package name and the Cloudflare project together, or builds break.
- `PUBLIC_KEYSTATIC_GITHUB_APP_SLUG` must be available to the **build**, not just at runtime.
- Rotating `KEYSTATIC_SECRET` signs every editor out (harmless).
- The `workers.dev` URL is also public. It carries the same noindex, but you can disable it in
  the Worker's Domains settings if you only want the custom domain.
- Keystatic has no browsable media library, no roles and no draft flag. See the differences
  table in `README.md`.
