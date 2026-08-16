# FM Fantasy

Standalone Football Manager fantasy-football web app.

## Architecture

- `index.html` — the full FM Fantasy UI/importer. `.fm` saves are parsed in the creator's browser.
- `config.js` — public Supabase project URL + publishable key only. Never put a service-role key here.
- `supabase/schema.sql` — isolated FM Fantasy auth/world/manager-state schema with RLS.
- `.github/workflows/pages.yml` — GitHub Pages deployment.

## Account model

- **FPL Creator** creates a world and receives a six-character creator code. Only the creator can upload/publish the shared FM database.
- **FPL User** creates their own username/password and joins using the creator code.
- Every manager gets the same football world/database but has their own squad, captain, chips, transfers and points state.
- The raw `.fm` file is never uploaded to GitHub or Supabase; only the parsed FM Fantasy payload is published.

## Supabase setup

1. Create a brand-new Supabase project for FM Fantasy only.
2. Run `supabase/schema.sql` in that project.
3. In Authentication settings, disable email confirmation so the username-only synthetic-email login can establish a session immediately.
4. Put the project's URL and **publishable/anon** key into `config.js`.
5. Never place the service-role key in this public repository.

## Production fixes in v52

- canonical FM football display-name normalization, including preferred/known-as + football surname handling;
- exact player-match deduplication before season aggregates are rebuilt;
- Star XI rebuilt from deduplicated weekly points rather than duplicate retained rows;
- player drawer Gameweek/recent-match stats normalized from all matching fixtures in a Gameweek.
