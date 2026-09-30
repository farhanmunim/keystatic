# Astro + Sveltia CMS

A static website built with [Astro](https://astro.build) whose content is managed with
[Sveltia CMS](https://sveltiacms.app), a Git-based headless CMS. There is no database and no
content API: every page, post, project, category, tag, author profile and setting is a Markdown
or YAML file in this repository, and Astro's content collections turn those files into pages.

```
Sveltia CMS (/admin) ──commits──▶ GitHub repo ──build──▶ Cloudflare Pages ──▶ live site
```

## Project layout

| Path | What it is |
| --- | --- |
| `public/admin/index.html` | The CMS app (Sveltia CMS loaded from the unpkg CDN) |
| `public/admin/config.yml` | The CMS configuration: collections, fields, workflow, media, auth |
| `public/uploads/` | The shared media library (images, PDFs, attachments), served at `/uploads/...` |
| `src/content.config.ts` | Astro content collections and schemas (mirror of the CMS collections) |
| `src/content/pages/` | Pages (`*.md`) → served at `/<slug>` |
| `src/content/posts/` | Posts (`*.md`) → `/blog/<slug>` |
| `src/content/projects/` | Projects (`*.md`) → `/projects/<slug>` |
| `src/content/services/` | Services (`*.md`) → `/services/<slug>` |
| `src/content/resources/` | Resources (`*.md`) → `/resources/<slug>` |
| `src/content/categories/` | Categories (`*.yml`, optional `parent`) → `/category/<slug>` |
| `src/content/tags/` | Tags (`*.yml`) → `/tags/<slug>` |
| `src/content/authors/` | Author profiles (`*.md`) → `/authors/<slug>` |
| `src/content/settings/site.yml` | Site Settings singleton |
| `src/pages/` | Astro routes (file-based) |
| `src/pages/docs.astro` | Plain-language editor guide, served at `/docs` |
| `src/pages/analytics.astro` | Embeds the Umami share dashboard from Site Settings at `/analytics` |
| `src/layouts/Layout.astro` | Site shell: head metadata, script injection, nav, footer |
| `src/lib/content.ts` | Small helpers around `getCollection`/`getEntry` (lookups, sorting) |

## Local development

```sh
npm install
npm run dev        # http://localhost:4321
npm run build      # production build into dist/
npm run preview    # serve dist/ locally (needed for /admin/ to resolve)
```

To use the CMS locally without GitHub, run `npm run preview`, open
`http://localhost:4322/admin/` in Chrome or Edge and choose **Work with Local Repository**
(Sveltia's built-in local mode; it edits the files in your checkout directly). Note that the
Astro *dev* server only serves the admin at `/admin/index.html`, not `/admin/`.

## Deploying to Cloudflare Pages

1. Push this repository to GitHub.
2. In the Cloudflare dashboard, create a Pages project connected to the repository.
3. Use the **Astro** framework preset (build command `npm run build`, output directory `dist`).
   Node 22 is selected automatically from the `.node-version` file.

Every push to the production branch (`main`) triggers a build. Sveltia CMS commits to that
branch when you publish, so publishing in the CMS deploys the site; no deploy-hook URL is
needed. Cloudflare also builds preview deployments for the editorial-workflow branches
(`sveltia-cms/...`), so unpublished drafts get a preview link inside the CMS.

## Setting up CMS sign-in (one-time)

Sveltia CMS signs editors in with GitHub OAuth. GitHub requires a tiny server-side step to
exchange the OAuth code, so deploy the official
[Sveltia CMS Authenticator](https://github.com/sveltia/sveltia-cms-auth) as a free Cloudflare
Worker:

1. Create a GitHub OAuth App (GitHub → Settings → Developer settings → OAuth Apps → New):
   * Homepage URL: your site URL, e.g. `https://your-site.pages.dev`
   * Authorization callback URL: `https://sveltia-cms-auth.<your-subdomain>.workers.dev/callback`
2. Deploy the worker with the "Deploy to Cloudflare Workers" button in the sveltia-cms-auth
   README, then set these Worker variables/secrets:
   * `GITHUB_CLIENT_ID` – from the OAuth app
   * `GITHUB_CLIENT_SECRET` – from the OAuth app (store as a secret)
   * `ALLOWED_DOMAINS` – your site's domain(s), e.g. `your-site.pages.dev`
3. In `public/admin/config.yml`, set `backend.base_url` to the worker URL and make sure
   `backend.repo` and `backend.branch` match your repository and production branch.

Anyone with **write** access to the GitHub repository can sign in and edit content;
repository **admins** can also change the CMS configuration and settings files.

## Content model

See `public/admin/config.yml` for the full field list. Highlights:

* **Drafts** – Pages, Posts, Projects, Services and Resources use Sveltia's Editorial Workflow
  (Draft → In review → Ready → Published). Unpublished entries live on their own Git branch and
  never reach the live site. Git history is the version history.
* **Slugs** – generated from the title/name (lowercase, ASCII, hyphenated) and editable in the
  entry sidebar.
* **Relations** – posts link to categories and tags; projects/services/resources link to tags;
  every content type links to an author; categories link to a parent category.
* **Media** – one shared library in `public/uploads`; originals are stored untouched.
  Alt text is entered per usage (the *Cover image alt text* field).
* **Settings** – the Site Settings singleton holds site name, tagline, meta description, logo,
  favicon, share image, footer text, social links, analytics dashboard link and raw HTML
  injected into the head and footer of every page.
