"""Export the live "NBA Scoring Overview" dashboard from Tableau Cloud to a
static site folder (PNG + PDF + index.html) for GitHub Pages.

Pure stdlib (urllib) — no pip install. Runs on GitHub's runners (clean internet,
default TLS) and locally (set TABLEAU_CA_BUNDLE to the corporate CA bundle if your
network MITM-intercepts TLS).

Env:
  TABLEAU_PAT_NAME, TABLEAU_PAT_SECRET   (required — a Tableau Personal Access Token)
  TABLEAU_SERVER   (default https://prod-uk-a.online.tableau.com)
  TABLEAU_SITE     (default laila-5f52a99af6)
  TABLEAU_API_VER  (default 3.19)
  DASHBOARD_VIEW   (default "NBA Scoring Overview")
  TABLEAU_CA_BUNDLE (optional path to a CA bundle for local proxied networks)

Usage:  python publish/export_dashboard.py [output_dir]   (default: site)
"""
from __future__ import annotations

import os
import ssl
import sys
import datetime
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib import request, error

# Lynk wordmark (getlynk.ai), inlined so the page is self-contained on GitHub Pages.
# fill="currentColor" lets CSS paint it white on the purple header.
LOGO_SVG = ('<svg class="logo" viewBox="0 0 110 33" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Lynk">'
    '<path d="M29.8705 9.12306H25.5139C24.8248 9.12306 24.5453 9.12306 24.2008 8.90485C23.7299 8.65218 23.5117 8.15451 23.5117 7.68363V2.67627C23.9099 2.82557 24.2927 2.99784 24.6679 3.18926V7.77551C24.6679 7.99372 24.7942 7.99372 25.0737 7.99372H29.3843C29.568 8.3574 29.7288 8.73641 29.8666 9.12306H29.8705Z" fill="currentColor"/>'
    '<path d="M32.4789 14.8422H24.8875C24.409 14.8422 24.118 14.8919 23.1112 14.7962C22.2958 14.6508 21.4804 14.3636 20.7606 13.9311C19.3212 13.0659 18.2646 11.5728 17.9775 9.88841C17.8818 9.50558 17.832 9.02321 17.832 8.63656V0C18.4178 0.0650805 18.992 0.160795 19.5586 0.283299V8.63274C19.5586 8.91986 19.6045 9.25674 19.6543 9.54769C19.8954 10.7498 20.6611 11.8102 21.6679 12.4342C22.1962 12.7711 22.7705 12.9625 23.3485 13.0582C24.0185 13.108 24.4052 13.108 24.8837 13.108H32.2071C32.3258 13.6746 32.4177 14.2526 32.4751 14.8383L32.4789 14.8422Z" fill="currentColor"/>'
    '<path d="M2.60938 9.12306H6.96594C7.65503 9.12306 7.93449 9.12306 8.27903 8.90485C8.74991 8.65218 8.96811 8.15451 8.96811 7.68363V2.67627C8.56997 2.82557 8.18714 2.99784 7.81197 3.18926V7.77551C7.81197 7.99372 7.68564 7.99372 7.40617 7.99372H3.09557C2.91182 8.3574 2.75102 8.73641 2.61321 9.12306H2.60938Z" fill="currentColor"/>'
    '<path d="M0 14.8422H7.59145C8.06998 14.8422 8.36091 14.8919 9.36775 14.7962C10.1832 14.6508 10.9986 14.3636 11.7183 13.9311C13.1577 13.0659 14.2143 11.5728 14.5015 9.88841C14.5972 9.50558 14.6469 9.02321 14.6469 8.63656V0C14.0612 0.0650805 13.487 0.160795 12.9204 0.283299V8.63274C12.9204 8.91986 12.8744 9.25674 12.8247 9.54769C12.5835 10.7498 11.8178 11.8102 10.811 12.4342C10.2827 12.7711 9.70846 12.9625 9.1304 13.0582C8.46045 13.108 8.07379 13.108 7.59526 13.108H0.271792C0.153116 13.6746 0.0612559 14.2526 0.003832 14.8383L0 14.8422Z" fill="currentColor"/>'
    '<path d="M29.8705 23.6167H25.5139C24.8248 23.6167 24.5453 23.6167 24.2008 23.8349C23.7299 24.0876 23.5117 24.5853 23.5117 25.0561V30.0635C23.9099 29.9142 24.2927 29.7419 24.6679 29.5505V24.9643C24.6679 24.746 24.7942 24.746 25.0737 24.746H29.3843C29.568 24.3824 29.7288 24.0034 29.8666 23.6167H29.8705Z" fill="currentColor"/>'
    '<path d="M32.4789 17.9011H24.8875C24.409 17.9011 24.118 17.8513 23.1112 17.9471C22.2958 18.0925 21.4804 18.3797 20.7606 18.8122C19.3212 19.6774 18.2646 21.1705 17.9775 22.8549C17.8818 23.2377 17.832 23.7201 17.832 24.1067V32.7433C18.4178 32.6782 18.992 32.5825 19.5586 32.46V24.1106C19.5586 23.8234 19.6045 23.4865 19.6543 23.1956C19.8954 21.9935 20.6611 20.9331 21.6679 20.3091C22.1962 19.9722 22.7705 19.7808 23.3485 19.6851C24.0185 19.6353 24.4052 19.6353 24.8837 19.6353H32.2071C32.3258 19.0687 32.4177 18.4907 32.4751 17.905L32.4789 17.9011Z" fill="currentColor"/>'
    '<path d="M2.60938 23.6167H6.96594C7.65503 23.6167 7.93449 23.6167 8.27903 23.8349C8.74991 24.0876 8.96811 24.5853 8.96811 25.0561V30.0635C8.56997 29.9142 8.18714 29.7419 7.81197 29.5505V24.9643C7.81197 24.746 7.68564 24.746 7.40617 24.746H3.09557C2.91182 24.3824 2.75102 24.0034 2.61321 23.6167H2.60938Z" fill="currentColor"/>'
    '<path d="M0 17.9011H7.59145C8.06998 17.9011 8.36091 17.8513 9.36775 17.9471C10.1832 18.0925 10.9986 18.3797 11.7183 18.8122C13.1577 19.6774 14.2143 21.1705 14.5015 22.8549C14.5972 23.2377 14.6469 23.7201 14.6469 24.1067V32.7433C14.0612 32.6782 13.487 32.5825 12.9204 32.46V24.1106C12.9204 23.8234 12.8744 23.4865 12.8247 23.1956C12.5835 21.9935 11.8178 20.9331 10.811 20.3091C10.2827 19.9722 9.70846 19.7808 9.1304 19.6851C8.46045 19.6353 8.07379 19.6353 7.59526 19.6353H0.271792C0.153116 19.0687 0.0612559 18.4907 0.003832 17.905L0 17.9011Z" fill="currentColor"/>'
    '<path d="M61.2262 23.1553H55.9815C53.206 23.1553 51.2383 21.5665 51.2383 18.6494V4.89062H53.0644V18.9825C53.0644 19.6218 53.3745 20.2381 53.9678 20.8583C54.3468 21.2373 55.013 21.4287 55.9853 21.4287H61.2301V23.1591L61.2262 23.1553Z" fill="currentColor"/>'
    '<path d="M70.006 27.8793H68.0612L70.1017 22.7303L64.9297 9.63379H66.8974L71.2157 20.3568L75.7713 9.63379H77.6701L70.006 27.8793Z" fill="currentColor"/>'
    '<path d="M94.1818 23.1552H92.3558V15.2537C92.3558 14.1167 91.927 13.1405 91.1001 12.3136C90.2693 11.4829 89.3199 11.0809 88.2059 11.0809C87.0919 11.0809 86.0927 11.4829 85.2658 12.3136C84.4351 13.1443 84.0331 14.1167 84.0331 15.2537V23.1552H82.207V15.4451C82.207 13.688 82.7775 12.2409 83.9144 11.0809C85.0514 9.91712 86.4755 9.32373 88.2097 9.32373C89.9439 9.32373 91.3413 9.91712 92.4821 11.0809C93.6191 12.2447 94.1895 13.6918 94.1895 15.4451V23.1552H94.1818Z" fill="currentColor"/>'
    '<path d="M110.002 23.1552H107.651L103.26 17.8416L101.101 20.5711V23.1552H99.1562V4.86377H101.032V17.7459L107.295 9.63378H109.55L104.401 16.4443L110.002 23.159V23.1552Z" fill="currentColor"/>'
    '</svg>')

NS = {"t": "http://tableau.com/api"}
SERVER = os.environ.get("TABLEAU_SERVER", "https://prod-uk-a.online.tableau.com")
SITE = os.environ.get("TABLEAU_SITE", "laila-5f52a99af6")
VER = os.environ.get("TABLEAU_API_VER", "3.19")
VIEW_NAME = os.environ.get("DASHBOARD_VIEW", "NBA Scoring Overview")
_CA = os.environ.get("TABLEAU_CA_BUNDLE")
CTX = ssl.create_default_context(cafile=_CA if _CA and os.path.exists(_CA) else None)


def api(path: str) -> str:
    return f"{SERVER}/api/{VER}/{path}"


def call(url, data=None, method="GET", headers=None, ctype=None) -> bytes:
    h = dict(headers or {})
    if ctype:
        h["Content-Type"] = ctype
    req = request.Request(url, data=data, method=method, headers=h)
    with request.urlopen(req, timeout=120, context=CTX) as resp:
        return resp.read()


def main() -> None:
    name = os.environ.get("TABLEAU_PAT_NAME")
    secret = os.environ.get("TABLEAU_PAT_SECRET")
    if not name or not secret:
        sys.exit("Set TABLEAU_PAT_NAME and TABLEAU_PAT_SECRET (repo secrets).")

    out = Path(sys.argv[1] if len(sys.argv) > 1 else "site")
    out.mkdir(parents=True, exist_ok=True)

    body = (f'<tsRequest><credentials personalAccessTokenName="{name}" '
            f'personalAccessTokenSecret="{secret}"><site contentUrl="{SITE}" />'
            f'</credentials></tsRequest>').encode()
    cred = ET.fromstring(call(api("auth/signin"), body, "POST", ctype="application/xml")).find("t:credentials", NS)
    token = cred.get("token")
    site_id = cred.find("t:site", NS).get("id")
    auth = {"X-Tableau-Auth": token}

    views = ET.fromstring(call(api(f"sites/{site_id}/views?pageSize=1000"), headers=auth))
    view_id = next((v.get("id") for v in views.iter("{http://tableau.com/api}view")
                    if v.get("name") == VIEW_NAME), None)
    if not view_id:
        sys.exit(f"View {VIEW_NAME!r} not found on site {SITE}.")

    png = call(api(f"sites/{site_id}/views/{view_id}/image?resolution=high&maxAge=1"), headers=auth)
    (out / "nba_overview.png").write_bytes(png)

    # The PDF is only a "Download" convenience link. Some servers reject the PDF
    # endpoint for large dashboards (HTTP 400) — never let that fail the deploy.
    pdf_link = ""
    try:
        pdf = call(api(f"sites/{site_id}/views/{view_id}/pdf?maxAge=1"), headers=auth)
        (out / "nba_overview.pdf").write_bytes(pdf)
        pdf_link = ('<a class="btn" href="nba_overview.pdf">'
                    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                    'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                    '<path d="M12 3v12M7 11l5 5 5-5M4 21h16"/></svg>Download PDF</a>')
        print(f"PDF exported ({len(pdf):,} B)")
    except Exception as e:
        print(f"WARN: PDF export skipped ({e}); deploying PNG only.")

    updated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    (out / "index.html").write_text(f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>NBA Scoring Overview · Lynk</title>
<meta name="description" content="NBA Scoring Overview — an executive Tableau dashboard built on the dbt marts (NBA.DBT_DEMO), powered by Lynk.">
<style>
  :root {{
    --brand:#6749F4; --brand-deep:#4b2fd6; --ink:#141118; --muted:#6b6577;
    --surface:#ffffff; --line:#e9e6f2; --bg:#f5f4fa;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
         color:var(--ink); background:var(--bg); -webkit-font-smoothing:antialiased; }}
  header {{ background:linear-gradient(135deg,#6749F4 0%,#4b2fd6 100%); color:#fff; }}
  .nav {{ max-width:1120px; margin:0 auto; padding:16px 24px; display:flex; align-items:center;
          justify-content:space-between; gap:12px; flex-wrap:wrap; }}
  .nav .logo {{ height:26px; width:auto; display:block; color:#fff; }}
  .cta {{ font-size:12.5px; color:#fff; text-decoration:none; border:1px solid rgba(255,255,255,.38);
          padding:7px 13px; border-radius:999px; white-space:nowrap; transition:background .15s; }}
  .cta:hover {{ background:rgba(255,255,255,.14); }}
  .hero {{ max-width:1120px; margin:0 auto; padding:10px 24px 34px; }}
  .hero h1 {{ margin:0; font-size:30px; line-height:1.15; letter-spacing:-0.02em; font-weight:700; }}
  .hero p {{ margin:9px 0 0; font-size:14.5px; opacity:.92; max-width:64ch; }}
  .tags {{ margin-top:18px; display:flex; gap:8px; flex-wrap:wrap; }}
  .tag {{ font-size:12px; background:rgba(255,255,255,.15); border:1px solid rgba(255,255,255,.24);
          padding:5px 12px; border-radius:999px; }}
  main {{ max-width:1120px; margin:-18px auto 0; padding:0 24px; }}
  .card {{ background:var(--surface); border:1px solid var(--line); border-radius:16px;
           box-shadow:0 14px 44px -14px rgba(38,20,90,.28); overflow:hidden; }}
  .toolbar {{ display:flex; align-items:center; justify-content:space-between; gap:12px;
              padding:14px 18px; border-bottom:1px solid var(--line); flex-wrap:wrap; }}
  .updated {{ font-size:12.5px; color:var(--muted); }}
  .dot {{ display:inline-block; width:7px; height:7px; border-radius:50%; background:#22c55e;
          margin-right:7px; vertical-align:middle; }}
  a.btn {{ display:inline-flex; align-items:center; gap:7px; background:var(--brand); color:#fff;
           text-decoration:none; padding:9px 16px; border-radius:9px; font-size:13.5px; font-weight:600;
           transition:background .15s; }}
  a.btn:hover {{ background:var(--brand-deep); }}
  .card img {{ display:block; width:100%; height:auto; }}
  footer {{ max-width:1120px; margin:22px auto 44px; padding:0 24px; color:var(--muted);
            font-size:12.5px; text-align:center; line-height:1.65; }}
  footer a {{ color:var(--brand); text-decoration:none; font-weight:600; }}
  @media (max-width:620px) {{ .hero h1 {{ font-size:24px; }} }}
</style></head>
<body>
  <header>
    <div class="nav">
      {LOGO_SVG}
      <a class="cta" href="https://www.getlynk.ai/" target="_blank" rel="noopener">The AI-Native Data Platform ↗</a>
    </div>
    <div class="hero">
      <h1>NBA Scoring Overview</h1>
      <p>Executive dashboard · built on the dbt marts (NBA.DBT_DEMO)</p>
      <div class="tags">
        <span class="tag">Live from Tableau Cloud</span>
        <span class="tag">Refreshed nightly</span>
        <span class="tag">Modeled in dbt · NBA.DBT_DEMO</span>
      </div>
    </div>
  </header>
  <main>
    <div class="card">
      <div class="toolbar">
        <span class="updated"><span class="dot"></span>Live snapshot · updated {updated}</span>
        {pdf_link}
      </div>
      <img src="nba_overview.png" alt="NBA Scoring Overview dashboard">
    </div>
  </main>
  <footer>
    Snapshot of the live Tableau dashboard · auto-published from the tableau-nba repo.<br>
    Built on the dbt marts (NBA.DBT_DEMO), powered by <a href="https://www.getlynk.ai/" target="_blank" rel="noopener">Lynk</a> — the AI-Native Data Platform.
  </footer>
</body></html>
""", encoding="utf-8")

    print(f"Wrote {out}/index.html + nba_overview.png ({len(png):,} B)")


if __name__ == "__main__":
    main()
