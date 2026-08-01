# Contributing

Sourdough Manager uses a two-stage development workflow so ongoing work does
not disrupt the stable version offered through HACS.

## Branch workflow

- `main` contains stable, releasable code only.
- `dev` is the integration branch for completed development work.
- Create every feature or fix branch from the latest `dev` branch.
- Open feature and fix pull requests against `dev`, not `main`.
- Promote a tested release from `dev` to `main` with a dedicated release pull
  request.

Before merging, the branch must be current with its target and the `hacs`,
`hassfest`, `tests` and `repository_policy` checks must pass. Do not bypass a
failed or pending check.

## Protected project identity

Do not change these project identifiers or publication assets:

- repository owner and name: `Trusties13/sourdough-manager`
- integration domain: `sourdough_manager`
- integration owner: `@Trusties13`
- root `hacs.json`
- required `manifest.json` fields
- brand icons

The repository policy workflow validates these invariants on every push and
pull request.

## Releases

1. Complete development through feature pull requests into `dev`.
2. Open a release pull request from `dev` to `main`.
3. Update the manifest version in that release pull request.
4. Merge only after every required check passes.
5. Create the matching `vX.Y.Z` tag from the resulting `main` commit.

The release workflow verifies that the tag matches the manifest version, that
the tagged commit belongs to `main`, and that validation passes before it
publishes a GitHub release. Do not tag experimental or unreviewed commits.
