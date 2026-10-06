// Provided by the uploadsIndex() integration in astro.config.mjs.
declare module 'virtual:uploads' {
  const files: { path: string; size: number }[];
  export default files;
}
