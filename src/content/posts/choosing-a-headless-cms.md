---
title: Choosing a headless CMS for a static site
author: jane-doe
excerpt: Git-based, API-based or self-hosted? A short guide to picking the right kind of CMS for a static site.
date: 2026-09-20T08:15:00.000Z
featured: false
categories:
  - guides
tags:
  - cms
  - design
---
There are three broad families of headless CMS.

### Git-based

Content is stored as files in your repository. The CMS is a thin editing UI on top of Git. Examples: Sveltia CMS, Decap CMS, Keystatic, Pages CMS.

### API-based (SaaS)

Content lives in a vendor's database and is fetched over an API at build time. Easy to start, but you depend on the vendor's uptime and pricing.

### Self-hosted application

You run the CMS server yourself, with its own database. Maximum control, maximum maintenance.

For a small static site with a handful of editors, the Git-based approach usually wins: there is nothing to host, nothing to pay for and every change is reviewable as a pull request.
