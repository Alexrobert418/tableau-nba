# tableau-nba

Automation + assets for putting the NBA dbt marts (`NBA.DBT_DEMO` in Snowflake) onto a
**Tableau** dashboard — the BI layer on top of the
[`dbt-nba`](https://github.com/lynkai-test-projects/dbt-nba) project.

> **Note — this is NOT a "Tableau pulls from git" integration.** Unlike dbt-on-Snowflake
> (where Snowflake clones the repo), Tableau does not read from this repo. This is plain
> version control for our automation code + workbook templates; content is pushed to
> Tableau via the REST API (`publish/`).

## Contents
| Path | Purpose |
|------|---------|
| `publish/publish_workbook.py` | Publish a `.twbx` workbook to Tableau Cloud via the REST API (PAT auth) |
| `publish/config.example.toml` | Copy to `config.toml`, fill in site URL / site name / project |
| `workbooks/` | Tableau workbook template(s) built on the dbt marts |
| `datasources/` | Optional published Snowflake connection (`.tds`) |

## Prerequisites
- A Tableau site — the free **Developer Sandbox** (https://www.tableau.com/developer) — plus a **Personal Access Token**.
- The Snowflake `NBA.DBT_DEMO` marts (from `dbt-nba`) + a read-only Snowflake credential for Tableau.
- Python 3.11+, then `pip install -r publish/requirements.txt`.

## Publish a workbook
1. `cp publish/config.example.toml publish/config.toml` and edit the values.
2. Put your PAT in the environment (never commit it):
   ```bash
   export TABLEAU_PAT_NAME=claude-mcp
   export TABLEAU_PAT_SECRET=********
   ```
3. `python publish/publish_workbook.py`

## Public dashboard on GitHub Pages (auto-deploy)

`.github/workflows/deploy-pages.yml` publishes a **static snapshot** of the dashboard
(PNG + downloadable PDF, wrapped in a small `index.html`) to GitHub Pages at
`https://lynkai-test-projects.github.io/tableau-nba/`. It exports whatever is
**live on Tableau Cloud** via `publish/export_dashboard.py` (stdlib only), on every
relevant push, **nightly** (to catch edits made in the Tableau UI), and on demand.

**One-time setup:**
1. **Make this repo public** — Settings → General → *Change visibility* → Public. *(Free GitHub Pages requires a public repo.)*
2. **Enable Pages via Actions** — Settings → Pages → *Build and deployment* → **Source: GitHub Actions**.
3. **Add two repo secrets** — Settings → Secrets and variables → Actions → *New repository secret*:
   - `TABLEAU_PAT_NAME`  (your Tableau Personal Access Token name)
   - `TABLEAU_PAT_SECRET` (the token secret)
4. Run it once from the **Actions** tab (*Deploy dashboard to GitHub Pages* → *Run workflow*), or push a change.

**Notes on behaviour:**
- The page reflects the **currently published** Tableau Cloud dashboard. If you change
  the workbook *code* here, run `publish/publish_workbook.py` first so Cloud has the new
  version, then the export picks it up. Edits made directly in the Tableau UI are picked
  up automatically by the nightly run.
- It's a **static image** (GitHub Pages can't host the interactive Tableau engine). For a
  clickable public dashboard, publish to **Tableau Public** instead.
- A GitHub Action can't be triggered *by* a Tableau-UI edit (Tableau doesn't notify
  GitHub) — that's why there's a nightly `schedule` in addition to `push`.

## Collaboration
Teammates collaborate on the **code** here via normal GitHub (clone / branch / PR). Note that
editing in the Tableau site itself depends on Tableau licensing — see the team's setup notes.
