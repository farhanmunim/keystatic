import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// Every collection maps 1:1 to a Sveltia CMS collection in public/admin/config.yml.
// Entry ids are the file names, which Sveltia generates from the title/name (editable in the CMS).

const markdown = (dir: string) => glob({ pattern: '**/*.md', base: `./src/content/${dir}` });
const yaml = (dir: string) => glob({ pattern: '**/*.yml', base: `./src/content/${dir}` });

const socialLink = z.object({
  platform: z.string(),
  url: z.string(),
  handle: z.string().optional(),
});

// Fields shared by every content type.
const content = {
  title: z.string(),
  author: z.string().optional(), // id of an `authors` entry
  cover: z.string().optional(), // path under /uploads
  cover_alt: z.string().optional(),
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
    description: z.string().optional(),
  }),
});

const posts = defineCollection({
  loader: markdown('posts'),
  schema: z.object({
    ...content,
    excerpt: z.string().optional(),
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
    summary: z.string().optional(),
    url: z.string().optional(),
    attachment: z.string().optional(),
  }),
});

const services = defineCollection({
  loader: markdown('services'),
  schema: z.object({
    ...catalogue,
    summary: z.string().optional(),
  }),
});

const resources = defineCollection({
  loader: markdown('resources'),
  schema: z.object({
    ...catalogue,
    description: z.string().optional(),
    url: z.string().optional(),
    attachment: z.string().optional(),
  }),
});

const categories = defineCollection({
  loader: yaml('categories'),
  schema: z.object({
    name: z.string(),
    parent: z.string().optional(),
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
    avatar: z.string().optional(),
    social: z.array(socialLink).default([]),
  }),
});

const settings = defineCollection({
  loader: yaml('settings'),
  schema: z.object({
    name: z.string(),
    tagline: z.string().optional(),
    description: z.string().optional(),
    logo: z.string().optional(),
    favicon: z.string().optional(),
    share_image: z.string().optional(),
    footer_text: z.string().optional(),
    social: z.array(socialLink).default([]),
    analytics_url: z.string().optional(),
    head_html: z.string().optional(),
    footer_html: z.string().optional(),
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
