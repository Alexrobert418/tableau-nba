"""Export a published Tableau view to local PNG + PDF (no Tableau login needed
to view the output files). Useful for sharing a dashboard with people who can't
sign in to the sandbox.

Usage:  python publish/export_view.py <viewId> <output_basepath>
Env:    TABLEAU_PAT_NAME, TABLEAU_PAT_SECRET (+ CA bundle via REQUESTS_CA_BUNDLE)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import tableauserverclient as TSC

SERVER = os.environ.get("TABLEAU_SERVER", "https://prod-uk-a.online.tableau.com")
SITE = os.environ.get("TABLEAU_SITE", "laila-5f52a99af6")


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("Usage: python publish/export_view.py <viewId> <output_basepath>")
    view_id = sys.argv[1]
    base = Path(sys.argv[2])
    base.parent.mkdir(parents=True, exist_ok=True)

    name = os.environ["TABLEAU_PAT_NAME"]
    secret = os.environ["TABLEAU_PAT_SECRET"]
    auth = TSC.PersonalAccessTokenAuth(name, secret, site_id=SITE)
    server = TSC.Server(SERVER, use_server_version=True)

    with server.auth.sign_in(auth):
        view = server.views.get_by_id(view_id)

        img_req = TSC.ImageRequestOptions(
            imageresolution=TSC.ImageRequestOptions.Resolution.High
        )
        server.views.populate_image(view, img_req)
        png = base.with_suffix(".png")
        png.write_bytes(view.image)
        print(f"Wrote {png} ({png.stat().st_size} bytes)")

        pdf_req = TSC.PDFRequestOptions(
            orientation=TSC.PDFRequestOptions.Orientation.Portrait
        )
        server.views.populate_pdf(view, pdf_req)
        pdf = base.with_suffix(".pdf")
        pdf.write_bytes(view.pdf)
        print(f"Wrote {pdf} ({pdf.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
