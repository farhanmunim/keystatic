import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// Every collection maps 1:1 to a Keystatic collection in keystatic.config.ts.
// Entry ids are the file names, which Keystatic generates from the title/name (editable in the CMS).
// Keystatic writes empty optional fields as '' or null, so optional strings are normalised to undefined.

const markdown = (dir: string) => glob({ pattern: '**/*.mdoc', base: `./src/content/${dir}` });
const yaml = (dir: string) => glob({ pattern: '**/*.yaml', base: `./src/content/${dir}` });

const optional = z
  .string()
  .nullish()
  .transform((v) => v || undefined);

const socialLink = z.object({
  platform: z.string(),
  url: z.string(),
  handle: optional,
});

// Fields shared by every content type.
const content = {
  title: z.string(),
  author: optional, // id of an `authors` entry
  cover: optional, // path under /uploads
  cover_alt: optional,
};

// Fields shared by Projects, Services and Resources.
const catalogue = {
  ...content,
  featured: z.boolean().default(false),
  tags: z.array(z.string()).default([]), // ids of `tags` entries
};

const pages = defineCollection({
  loader: markdown('pages'),
  schema: z.object({
    ...content,
    description: optional,
  }),
});

const posts = defineCollection({
  loader: markdown('posts'),
  schema: z.object({
    ...content,
    excerpt: optional,
    date: z.coerce.date(),
    featured: z.boolean().default(false),
    categories: z.array(z.string()).default([]), // ids of `categories` entries
    tags: z.array(z.string()).default([]),
  }),
});

const projects = defineCollection({
  loader: markdown('projects'),
  schema: z.object({
    ...catalogue,
    summary: optional,
    url: optional,
    attachment: optional,
  }),
});

const services = defineCollection({
  loader: markdown('services'),
  schema: z.object({
    ...catalogue,
    summary: optional,
  }),
});

const resources = defineCollection({
  loader: markdown('resources'),
  schema: z.object({
    ...catalogue,
    description: optional,
    url: optional,
    attachment: optional,
  }),
});

const categories = defineCollection({
  loader: yaml('categories'),
  schema: z.object({
    name: z.string(),
    parent: optional,
  }),
});

const tags = defineCollection({
  loader: yaml('tags'),
  schema: z.object({
    name: z.string(),
  }),
});

const authors = defineCollection({
  loader: markdown('authors'),
  schema: z.object({
    first_name: z.string(),
    last_name: z.string(),
    avatar: optional,
    social: z.array(socialLink).default([]),
  }),
});

const settings = defineCollection({
  loader: yaml('settings'),
  schema: z.object({
    name: z.string(),
    tagline: optional,
    description: optional,
    logo: optional,
    favicon: optional,
    share_image: optional,
    footer_text: optional,
    social: z.array(socialLink).default([]),
    analytics_url: optional,
    noindex: z.boolean().default(false),
    head_html: optional,
    footer_html: optional,
  }),
});

export const collections = {
  pages,
  posts,
  projects,
  services,
  resources,
  categories,
  tags,
  authors,
  settings,
};
