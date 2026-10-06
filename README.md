# Astro + Keystatic CMS

A static website built with [Astro](https://astro.build) whose content is managed with
[Keystatic](https://keystatic.com), a Git-based headless CMS. There is no database and no
content API: every page, post, project, category, tag, author profile and setting is a Markdown
or YAML file in this repository, and Astro's content collections turn those files into pages.

```
Keystatic (/keystatic) ──commits──▶ GitHub repo ──build──▶ Cloudflare ──▶ live site
```

## Project layout

| Path | What it is |
| --- | --- |
| `keystatic.config.ts` | The CMS configuration: collections, fields, sidebar groups, storage |
| `public/uploads/` | Uploads, one folder per entry (`<collection>/<entry-slug>/file`), served at `/uploads/...`; listed at `/media` |
| `src/content.config.ts` | Astro content collections and schemas (mirror of the CMS collections) |
| `src/content/pages/` | Pages (`*.mdoc`) → served at `/<slug>` |
| `src/content/posts/` | Posts (`*.mdoc`) → `/blog/<slug>` |
| `src/content/projects/` | Projects (`*.mdoc`) → `/projects/<slug>` |
| `src/content/services/` | Services (`*.mdoc`) → `/services/<slug>` |
| `src/content/resources/` | Resources (`*.mdoc`) → `/resources/<slug>` |
| `src/content/categories/` | Categories (`*.yaml`, optional `parent`) → `/category/<slug>` |
| `src/content/tags/` | Tags (`*.yaml`) → `/tags/<slug>` |
| `src/content/authors/` | Author profiles (`*.mdoc`) → `/authors/<slug>` |
| `src/content/settings/site.yaml` | Site Settings singleton |
| `src/pages/` | Astro routes (file-based) |
| `src/pages/docs.astro` | Plain-language editor guide, served at `/docs` |
| `src/pages/analytics.astro` | Embeds the Umami share dashboard from Site Settings at `/analytics` |
| `src/layouts/Layout.astro` | Site shell: head metadata, script injection, nav, footer |
| `src/lib/content.ts` | Small helpers around `getCollection`/`getEntry` (lookups, sorting) |

See [ARCHITECTURE.md](ARCHITECTURE.md) for how everything fits together (hosting, Workers, GitHub App sign-in).

The site is fully static. The Cloudflare adapter only serves Keystatic's admin UI
(`/keystatic`) and its `/api/keystatic` routes; `/admin` redirects to `/keystatic`.

## Local development

```sh
npm install
npm run dev        # http://localhost:4321, CMS at http://localhost:4321/keystatic
npm run build      # production build into dist/
```

In dev, Keystatic runs in **local mode**: it edits the files in your checkout directly, with no
sign-in. Production uses GitHub storage (`import.meta.env.PROD` in `keystatic.config.ts`).

## Deploying to Cloudflare

The Cloudflare adapter builds a Worker with static assets (`dist/server` + `dist/client`).

1. In the Cloudflare dashboard go to **Workers & Pages → Create → Import a repository** and pick
   this repository. Production branch: `main`.
2. Build command `npm run build`, deploy command `npx wrangler deploy`. Node 22 is picked up from
   `.node-version`.
3. After the first deploy, note the site URL (`https://astro-keystatic-site.<account>.workers.dev`)
   and set `site` in `astro.config.mjs` to it (or your custom domain).

Every push to `main` rebuilds the site, so saving on `main` in the CMS deploys it.

## Setting up CMS sign-in (one-time)

Keystatic signs editors in with a GitHub App you own.

1. GitHub → Settings → Developer settings → GitHub Apps → **New GitHub App**:
   * Homepage URL: your site URL
   * Callback URL: `https://<your-site>/api/keystatic/github/oauth/callback`
   * Check **Request user authorization (OAuth) during installation**
   * Uncheck **Webhook → Active**
   * Repository permissions: **Contents: Read and write**, **Pull requests: Read-only**
     (Metadata: Read-only is added automatically)
   * Where can it be installed: **Only on this account**
2. After creating it, note the **App slug** (from its URL), the **Client ID**, and generate a
   **Client secret**. Then **Install App** on the `keystatic` repository.
3. In Cloudflare → your Worker → **Settings → Variables and Secrets**, add these (and also under
   **Settings → Build → Variables**, because the slug is inlined at build time):
   * `KEYSTATIC_GITHUB_CLIENT_ID`: the Client ID
   * `KEYSTATIC_GITHUB_CLIENT_SECRET`: the Client secret (secret)
   * `KEYSTATIC_SECRET`: any random string of 32+ characters, e.g. `openssl rand -hex 32` (secret)
   * `PUBLIC_KEYSTATIC_GITHUB_APP_SLUG`: the App slug
4. Redeploy, then open `/keystatic` and sign in with GitHub.

Make sure `REPO` in `keystatic.config.ts` matches your repository. Anyone with **write** access to
the GitHub repository can sign in and edit content.

## Content model

See `keystatic.config.ts` for the full field list. Highlights:

* **Drafts** – Keystatic has no draft flag. Drafts are Git branches: create a branch from the
  editor, save there, then open a pull request and merge it to publish. Git history is the
  version history.
* **Slugs** – generated from the title/name (lowercase, hyphenated) and editable in the entry.
* **Relations** – posts link to categories and tags; projects/services/resources link to tags;
  every content type links to an author; categories link to a parent category.
* **Media** – uploads go to `public/uploads/<collection>/<entry-slug>/`, the layout Keystatic
  needs to preview images in the editor. Originals are untouched. Keystatic has no browsable
  media library, so the site's `/media` page lists every file. Alt text is entered per usage
  (the *Cover image alt text* field).
* **Settings** – the Site Settings singleton holds site name, tagline, meta description, logo,
  favicon, share image, footer text, social links, analytics dashboard link and raw HTML
  injected into the head and footer of every page.

## Search engines

Site Settings has a **Hide this site from search engines** switch (on by default for this site).
It adds a `noindex` meta tag to every page and makes `/robots.txt` disallow all crawlers. Turn it
off at launch; the change applies after the next deploy.

## Importing from WordPress

`scripts/import-wordpress.py` seeds all content (posts, projects, services, resources,
categories, tags, author, social links, media) from a headless WordPress REST API. See
ARCHITECTURE.md for the mapping.

```sh
pip install beautifulsoup4
python3 scripts/import-wordpress.py https://cms.farhan.app
```

## Differences from the CMS blueprint

Keystatic is Git-based, so some blueprint behaviours do not apply or are approximated:

| Blueprint | In Keystatic |
| --- | --- |
| Users, roles, passwords, lockout, email resets | Not applicable: GitHub accounts with repo write access sign in |
| Author defaults to current user | Not supported; the editor picks an author |
| Auto publish date on first publish | Defaults to "now" when the post is created |
| Draft / publish | Branches and pull requests |
| Media library with required alt text | Per-field uploads; alt text is a separate field, not enforced |
| Permalinks screen | Prefixes are fixed in `src/pages` and `paths` in `src/lib/content.ts` |
| Deploy hook | Not needed: a commit to the production branch triggers the build |
| CSV/JSON import and export | Not available; content is plain files in Git |
| Inline tag creation | Create tags in the Tags collection first |
