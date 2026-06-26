"""Publish a Tableau workbook (.twbx) to Tableau Cloud via the REST API.

Auth: Personal Access Token (PAT). Set these env vars (never commit them):
    TABLEAU_PAT_NAME    - the PAT name
    TABLEAU_PAT_SECRET  - the PAT secret

Config: copy config.example.toml -> config.toml and edit it.
Run:    python publish/publish_workbook.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

import tableauserverclient as TSC


def load_config() -> dict:
    cfg_path = Path(__file__).with_name("config.toml")
    if not cfg_path.exists():
        sys.exit(
            f"Missing {cfg_path}.\n"
            "Copy publish/config.example.toml -> publish/config.toml and edit it."
        )
    with cfg_path.open("rb") as fh:
        return tomllib.load(fh)


def main() -> None:
    cfg = load_config()

    pat_name = os.environ.get("TABLEAU_PAT_NAME")
    pat_secret = os.environ.get("TABLEAU_PAT_SECRET")
    if not pat_name or not pat_secret:
        sys.exit("Set TABLEAU_PAT_NAME and TABLEAU_PAT_SECRET in the environment.")

    workbook_file = (Path(__file__).parent / cfg["workbook_file"]).resolve()
    if not workbook_file.exists():
        sys.exit(
            f"Workbook not found: {workbook_file}\n"
            "Build it in Tableau and save it under workbooks/ first."
        )

    auth = TSC.PersonalAccessTokenAuth(
        pat_name, pat_secret, site_id=cfg["site_content_url"]
    )
    server = TSC.Server(cfg["server_url"], use_server_version=True)

    with server.auth.sign_in(auth):
        projects, _ = server.projects.get()
        project = next((p for p in projects if p.name == cfg["project_name"]), None)
        if project is None:
            names = ", ".join(sorted(p.name for p in projects))
            sys.exit(f"Project '{cfg['project_name']}' not found. Available: {names}")

        workbook = TSC.WorkbookItem(project_id=project.id, name=cfg["workbook_name"])
        workbook = server.workbooks.publish(
            workbook,
            str(workbook_file),
            mode=TSC.Server.PublishMode.Overwrite,
        )
        print(f"Published '{workbook.name}' -> {workbook.webpage_url}")


if __name__ == "__main__":
    main()
