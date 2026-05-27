# Docs Maintenance Guide
Use this file as the handoff checklist for future edits to this documentation PR.
## Source Layout
- The docs source lives in `docs/`.
- `docs.json` is the Docs Cloud configuration for publishing, previews, and content roots.
- The managed runtime lives in `.docs/site`; edit authored markdown at the repo root instead of generated runtime pages under `.docs/site/app/docs`.
- Keep every page grounded in README content, package metadata, source exports, CLI help, environment examples, or existing docs.
## Docs Routes
- /docs - Introduction
- /docs/installation - Installation
- /docs/quickstart - Quickstart
- /docs/concepts - Core Concepts
- /docs/configuration - Configuration
- /docs/scheduler - Scheduling
- /docs/cli - CLI Reference
- /docs/architecture - Architecture
- /docs/roadmap - Roadmap
## Editing Guidelines
- Prefer reader-facing setup, usage, and troubleshooting notes over source inventories.
- Do not add commands, flags, environment variables, routes, imports, or framework names unless they are present in the repository.
- If you add or rename a page, keep its frontmatter title and description accurate and make sure the navigation ordering still includes it.
- Avoid analyzer language such as generated from, source evidence, implementation map, source surface, or detected in files.
## Verification
- Build the docs site with `cd .docs/site && pnpm install && pnpm build` before handing off a docs PR.
- Open `/docs` and at least one generated leaf page to confirm the sidebar and page content match the PR.
