import { collection, config, fields, singleton } from '@keystatic/core';

// Keystatic CMS configuration (served at /keystatic; /admin redirects there).
// Every collection maps 1:1 to an Astro content collection in src/content.config.ts.
// Entry ids are the file names, which Keystatic generates from the title/name (editable in the CMS).

const REPO = 'farhanmunim/keystatic';

// One shared uploads folder for all images and files. Originals are stored untouched.
const UPLOADS = { directory: 'public/uploads', publicPath: '/uploads/' } as const;

const platforms = ['Website', 'GitHub', 'LinkedIn', 'X', 'Bluesky', 'Mastodon', 'Instagram', 'YouTube', 'Buy Me a Coffee', 'Other'];

const socialLinks = (label = 'Social links') =>
  fields.array(
    fields.object({
      platform: fields.select({
        label: 'Platform',
        options: platforms.map((value) => ({ label: value, value })),
        defaultValue: 'Website',
      }),
      url: fields.url({ label: 'URL', validation: { isRequired: true } }),
      handle: fields.text({ label: 'Handle' }),
    }),
    {
      label,
      itemLabel: (props) => `${props.fields.platform.value}: ${props.fields.url.value ?? ''}`,
    },
  );

const author = () =>
  fields.relationship({
    label: 'Author',
    description: 'Pick yourself from the Authors list.',
    collection: 'authors',
  });

const tags = () =>
  fields.multiRelationship({
    label: 'Tags',
    description: 'Pick from the Tags collection (create new ones there first).',
    collection: 'tags',
  });

const cover = () => ({
  cover: fields.image({ label: 'Cover image', ...UPLOADS }),
  cover_alt: fields.text({
    label: 'Cover image alt text',
    description: 'Describe the cover image for screen readers.',
  }),
});

const content = () =>
  fields.markdoc({
    label: 'Content',
    options: { image: { ...UPLOADS }, table: true },
  });

const title = () => fields.slug({ name: { label: 'Title', validation: { isRequired: true } } });

const featured = (description: string) =>
  fields.checkbox({ label: 'Featured', description, defaultValue: false });

const attachment = (description: string) => fields.file({ label: 'Attachment', description, ...UPLOADS });

export default config({
  storage: import.meta.env.PROD
    ? { kind: 'github', repo: REPO }
    : { kind: 'local' },

  ui: {
    brand: { name: 'Site CMS' },
    navigation: {
      Content: ['pages', 'posts', 'projects', 'services', 'resources'],
      Organisation: ['categories', 'tags'],
      Settings: ['authors', 'site'],
    },
  },

  collections: {
    // ---------------------------------------------------------------- Content
    pages: collection({
      label: 'Pages',
      slugField: 'title',
      path: 'src/content/pages/*',
      format: { contentField: 'content' },
      entryLayout: 'content',
      columns: ['title'],
      schema: {
        title: title(),
        author: author(),
        ...cover(),
        description: fields.text({
          label: 'Description',
          description: "Used as the page's meta description.",
          multiline: true,
        }),
        content: content(),
      },
    }),

    posts: collection({
      label: 'Posts',
      slugField: 'title',
      path: 'src/content/posts/*',
      format: { contentField: 'content' },
      entryLayout: 'content',
      columns: ['title', 'date'],
      schema: {
        title: title(),
        author: author(),
        ...cover(),
        excerpt: fields.text({
          label: 'Excerpt',
          description: 'Short summary shown in listings.',
          multiline: true,
        }),
        date: fields.datetime({
          label: 'Publish date',
          description: 'Set when the post is created; change it if needed.',
          defaultValue: { kind: 'now' },
        }),
        featured: featured('Highlight on the homepage and at the top of listings.'),
        categories: fields.multiRelationship({
          label: 'Categories',
          collection: 'categories',
        }),
        tags: tags(),
        content: content(),
      },
    }),

    projects: collection({
      label: 'Projects',
      slugField: 'title',
      path: 'src/content/projects/*',
      format: { contentField: 'content' },
      entryLayout: 'content',
      columns: ['title'],
      schema: {
        title: title(),
        author: author(),
        featured: featured('Show first in listings.'),
        tags: tags(),
        ...cover(),
        summary: fields.text({ label: 'Summary', multiline: true }),
        url: fields.url({ label: 'URL', description: 'Link to the live project.' }),
        attachment: attachment('Optional downloadable file, e.g. a case study PDF.'),
        content: content(),
      },
    }),

    services: collection({
      label: 'Services',
      slugField: 'title',
      path: 'src/content/services/*',
      format: { contentField: 'content' },
      entryLayout: 'content',
      columns: ['title'],
      schema: {
        title: title(),
        author: author(),
        featured: featured('Show first in listings.'),
        tags: tags(),
        ...cover(),
        summary: fields.text({ label: 'Summary', multiline: true }),
        content: content(),
      },
    }),

    resources: collection({
      label: 'Resources',
      slugField: 'title',
      path: 'src/content/resources/*',
      format: { contentField: 'content' },
      entryLayout: 'content',
      columns: ['title'],
      schema: {
        title: title(),
        author: author(),
        featured: featured('Show first in listings.'),
        tags: tags(),
        ...cover(),
        description: fields.text({ label: 'Description', multiline: true }),
        url: fields.url({ label: 'External URL' }),
        attachment: attachment('Optional downloadable file.'),
        content: content(),
      },
    }),

    // ----------------------------------------------------------- Organisation
    categories: collection({
      label: 'Categories',
      slugField: 'name',
      path: 'src/content/categories/*',
      format: 'yaml',
      columns: ['name', 'parent'],
      schema: {
        name: fields.slug({ name: { label: 'Name', validation: { isRequired: true } } }),
        parent: fields.relationship({
          label: 'Parent category',
          description: 'Optional. Enables nesting, e.g. Guides → Tutorials.',
          collection: 'categories',
        }),
      },
    }),

    tags: collection({
      label: 'Tags',
      slugField: 'name',
      path: 'src/content/tags/*',
      format: 'yaml',
      schema: {
        name: fields.slug({ name: { label: 'Name', validation: { isRequired: true } } }),
      },
    }),

    // --------------------------------------------------------------- Settings
    authors: collection({
      label: 'Authors',
      slugField: 'first_name',
      path: 'src/content/authors/*',
      format: { contentField: 'about' },
      entryLayout: 'content',
      columns: ['first_name', 'last_name'],
      schema: {
        first_name: fields.slug({
          name: { label: 'First name', validation: { isRequired: true } },
          slug: {
            label: 'URL slug',
            description: 'Use first-last, e.g. jane-doe. It becomes the author page URL.',
          },
        }),
        last_name: fields.text({ label: 'Last name', validation: { isRequired: true } }),
        avatar: fields.image({ label: 'Avatar', ...UPLOADS }),
        social: socialLinks(),
        about: fields.markdoc({ label: 'About the author', options: { image: { ...UPLOADS }, table: true } }),
      },
    }),
  },

  singletons: {
    site: singleton({
      label: 'Site Settings',
      path: 'src/content/settings/site',
      format: 'yaml',
      schema: {
        name: fields.text({ label: 'Site name', validation: { isRequired: true } }),
        tagline: fields.text({ label: 'Tagline' }),
        description: fields.text({ label: 'Default meta description', multiline: true }),
        logo: fields.image({ label: 'Logo', ...UPLOADS }),
        favicon: fields.image({
          label: 'Favicon',
          description: 'A square SVG, PNG or ICO file.',
          ...UPLOADS,
        }),
        share_image: fields.image({
          label: 'Default social-share image',
          description: 'Used for Open Graph / Twitter cards when a page has no cover image.',
          ...UPLOADS,
        }),
        footer_text: fields.text({ label: 'Footer copyright text' }),
        social: socialLinks(),
        analytics_url: fields.url({
          label: 'Analytics dashboard link',
          description: 'A read-only Umami share URL. When set, it is embedded at /analytics.',
        }),
        noindex: fields.checkbox({
          label: 'Hide this site from search engines',
          description:
            'Adds a noindex meta tag to every page and makes /robots.txt disallow all crawlers. Turn off when you are ready to launch.',
          defaultValue: false,
        }),
        head_html: fields.text({
          label: 'Head scripts',
          description: 'Raw HTML injected into the <head> of every page (analytics/tracking snippets).',
          multiline: true,
        }),
        footer_html: fields.text({
          label: 'Footer scripts',
          description: 'Raw HTML injected before </body> on every page.',
          multiline: true,
        }),
      },
    }),
  },
});
