# Archived frontend prototype

`adeline-world` is a preserved, non-production prototype. It is not the Dear
Adeline application deployed to families.

Production frontend: `adeline-ui`

Production API: `adeline-brain`

Evidence for isolation:

- the root `pnpm-workspace.yaml` includes only `adeline-core` and `adeline-ui`;
- the root production build targets `adeline-ui`;
- Vercel configuration lives under `adeline-ui`;
- Railway configuration and Docker entrypoint live under `adeline-brain`;
- no production package imports `adeline-world`;
- ordinary `dev`, `build`, and `start` commands in this directory fail closed.

The old source remains available for historical reference. Intentional local
inspection must use the explicitly named `dev:legacy`, `build:legacy`, or
`test:legacy` scripts. Do not add production features, API callers, or deployment
configuration here.
