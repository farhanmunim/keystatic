---
title: Getting started with Astro content collections
author: sam-lee
cover: /uploads/cover-astro.svg
cover_alt: Stylised rocket icon on a dark background
excerpt: Content collections give your Markdown and YAML files a schema, type-safety and a query API.
date: 2026-09-10T14:30:00.000Z
featured: false
categories:
  - tutorials
tags:
  - astro
  - performance
---
Astro's content collections turn a folder of Markdown or YAML files into a typed data source.

## Define a collection

Each collection lives in `src/content/<name>` and is declared in `src/content.config.ts` with a schema.

```ts
const posts = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/posts' }),
  schema: z.object({ title: z.string(), date: z.coerce.date() }),
});
```

## Query it

Use `getCollection('posts')` in any page or component. Astro validates every file against the schema at build time, so a typo in the front matter fails the build instead of silently producing a broken page.

## Render it

`render(entry)` returns a `Content` component that outputs the Markdown body as HTML.
