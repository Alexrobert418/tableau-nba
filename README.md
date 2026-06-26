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

## Collaboration
Teammates collaborate on the **code** here via normal GitHub (clone / branch / PR). Note that
editing in the Tableau site itself depends on Tableau licensing — see the team's setup notes.
