import { getCollection, getEntry, type CollectionEntry } from 'astro:content';

/** Site Settings singleton (src/content/settings/site.yml). */
export async function getSettings() {
  const entry = await getEntry('settings', 'site');
  if (!entry) throw new Error('Missing src/content/settings/site.yml (Site Settings).');
  return entry.data;
}

export type Author = CollectionEntry<'authors'>;
export type Tag = CollectionEntry<'tags'>;
export type Category = CollectionEntry<'categories'>;

export const authorName = (author: Author) => `${author.data.first_name} ${author.data.last_name}`;

/** Look up a related entry by id, tolerating dangling references (e.g. a deleted tag). */
export async function getAuthor(id?: string) {
  return id ? ((await getEntry('authors', id)) ?? undefined) : undefined;
}

export async function getTags(ids: string[]) {
  const tags = await Promise.all(ids.map((id) => getEntry('tags', id)));
  return tags.filter((t): t is Tag => Boolean(t));
}

export async function getCategories(ids: string[]) {
  const categories = await Promise.all(ids.map((id) => getEntry('categories', id)));
  return categories.filter((c): c is Category => Boolean(c));
}

/** A category plus every category nested under it, as ids. */
export async function getCategoryTree(id: string): Promise<string[]> {
  const all = await getCollection('categories');
  const ids = [id];
  for (let i = 0; i < ids.length; i++) {
    for (const c of all) if (c.data.parent === ids[i] && !ids.includes(c.id)) ids.push(c.id);
  }
  return ids;
}

/** Breadcrumb trail from the root category down to `category`. */
export async function getCategoryTrail(category: Category): Promise<Category[]> {
  const trail = [category];
  let parent = category.data.parent;
  while (parent && !trail.some((c) => c.id === parent)) {
    const entry = await getEntry('categories', parent);
    if (!entry) break;
    trail.unshift(entry);
    parent = entry.data.parent;
  }
  return trail;
}

/** Posts, newest first, featured posts first. */
export async function getPosts() {
  const posts = await getCollection('posts');
  return posts.sort(
    (a, b) => Number(b.data.featured) - Number(a.data.featured) || b.data.date.valueOf() - a.data.date.valueOf(),
  );
}

/** Projects / services / resources: featured first, then alphabetical. */
export async function getCatalogue<C extends 'projects' | 'services' | 'resources'>(collection: C) {
  const entries = await getCollection(collection);
  return entries.sort(
    (a, b) => Number(b.data.featured) - Number(a.data.featured) || a.data.title.localeCompare(b.data.title),
  );
}

export const formatDate = (date: Date) =>
  date.toLocaleDateString('en-GB', { year: 'numeric', month: 'long', day: 'numeric' });

/** URL prefixes for each routable collection (see src/pages). */
export const paths = {
  pages: '',
  posts: '/blog',
  projects: '/projects',
  services: '/services',
  resources: '/resources',
  categories: '/category',
  tags: '/tags',
  authors: '/authors',
} as const;
