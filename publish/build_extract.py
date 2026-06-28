"""Build a Tableau .hyper extract from the dbt-modeled NBA marts in Snowflake.

Reads `NBA.DBT_DEMO.FCT_GAME` (joined to DIM_TEAM), unpivots each game into one
row per team, and aggregates to a team x season grain with games / wins /
points-for / points-against. A workbook embeds this single Hyper table and
derives ratios (PPG, opponent PPG, win %) as calculated fields.

Connection uses key-pair auth (same key the Snowflake MCP uses); we only read
the key to authenticate.

Usage:  python publish/build_extract.py [output.hyper]
Env overrides: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_ROLE,
               SNOWFLAKE_WAREHOUSE, SNOWFLAKE_PRIVATE_KEY_FILE
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# The corporate network MITM-intercepts TLS, so the bundled certifi CA yields
# "certificate verify failed" / connection timeouts. The Snowflake MCP writes a
# combined CA bundle (certifi + Windows ROOT/CA stores) to win_ca_bundle.pem.
# Point OpenSSL/requests at it BEFORE importing snowflake.connector.
_CA_BUNDLE = os.environ.get(
    "SNOWFLAKE_CA_BUNDLE", "C:/Users/USUARIO/snowflake-mcp/win_ca_bundle.pem"
)
if os.path.exists(_CA_BUNDLE):
    os.environ.setdefault("SSL_CERT_FILE", _CA_BUNDLE)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _CA_BUNDLE)

import snowflake.connector
from tableauhyperapi import (
    Connection,
    CreateMode,
    HyperProcess,
    Inserter,
    Nullability,
    SqlType,
    TableDefinition,
    TableName,
    Telemetry,
)

# Team x season aggregates, built from game-level fct_game (unpivoted home/away).
# Limited to 1996+ for a clean, modern, 30-team view.
QUERY = """
WITH per_team AS (
    SELECT season_id, season_type, team_id_home AS team_id,
           pts_home AS pts_for, pts_away AS pts_against,
           IFF(wl_home = 'W', 1, 0) AS win
    FROM NBA.DBT_DEMO.FCT_GAME
    UNION ALL
    SELECT season_id, season_type, team_id_away AS team_id,
           pts_away AS pts_for, pts_home AS pts_against,
           IFF(wl_away = 'W', 1, 0) AS win
    FROM NBA.DBT_DEMO.FCT_GAME
)
SELECT
    p.season_id,
    MOD(p.season_id, 10000)         AS season_year,
    p.season_type,
    p.team_id,
    t.team_name,
    COUNT(*)                        AS games,
    SUM(p.win)                      AS wins,
    SUM(p.pts_for)                  AS points_for,
    SUM(p.pts_against)              AS points_against
FROM per_team p
JOIN NBA.DBT_DEMO.DIM_TEAM t ON t.team_id = p.team_id
WHERE MOD(p.season_id, 10000) >= 1996
GROUP BY 1, 2, 3, 4, 5
"""

EXTRACT_TABLE = TableName("Extract", "Extract")


def fetch_rows():
    conn = snowflake.connector.connect(
        account=os.environ.get("SNOWFLAKE_ACCOUNT", "a5628485664271-lynkai_partner"),
        user=os.environ.get("SNOWFLAKE_USER", "LAILA"),
        authenticator="snowflake_jwt",
        private_key_file=os.environ.get(
            "SNOWFLAKE_PRIVATE_KEY_FILE",
            "C:/Users/USUARIO/.snowflake/keys/rsa_key.p8",
        ),
        role=os.environ.get("SNOWFLAKE_ROLE", "DBT_NBA_DEVELOPER"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database="NBA",
        schema="DBT_DEMO",
    )
    try:
        cur = conn.cursor()
        cur.execute(QUERY)
        rows = cur.fetchall()
    finally:
        conn.close()
    norm = []
    for (sid, syear, stype, tid, tname, games, wins, pf, pa) in rows:
        norm.append([
            int(sid),
            int(syear),
            str(stype),
            None if tid is None else int(tid),
            None if tname is None else str(tname),
            None if games is None else int(games),
            None if wins is None else int(wins),
            None if pf is None else float(pf),
            None if pa is None else float(pa),
        ])
    return norm


def write_hyper(rows, hyper_path: Path) -> None:
    hyper_path.parent.mkdir(parents=True, exist_ok=True)
    if hyper_path.exists():
        hyper_path.unlink()

    def col(name, sqltype, nullable=Nullability.NULLABLE):
        return TableDefinition.Column(name, sqltype, nullable)

    table_def = TableDefinition(
        EXTRACT_TABLE,
        [
            col("SEASON_ID", SqlType.big_int(), Nullability.NOT_NULLABLE),
            col("SEASON_YEAR", SqlType.int(), Nullability.NOT_NULLABLE),
            col("SEASON_TYPE", SqlType.text(), Nullability.NOT_NULLABLE),
            col("TEAM_ID", SqlType.big_int()),
            col("TEAM_NAME", SqlType.text()),
            col("GAMES", SqlType.big_int()),
            col("WINS", SqlType.big_int()),
            col("POINTS_FOR", SqlType.double()),
            col("POINTS_AGAINST", SqlType.double()),
        ],
    )

    with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(
            hyper.endpoint, str(hyper_path), CreateMode.CREATE_AND_REPLACE
        ) as conn:
            conn.catalog.create_schema("Extract")
            conn.catalog.create_table(table_def)
            with Inserter(conn, table_def) as inserter:
                inserter.add_rows(rows)
                inserter.execute()
            count = conn.execute_scalar_query(f"SELECT COUNT(*) FROM {EXTRACT_TABLE}")
    print(f"Wrote {count} rows -> {hyper_path}")


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("build/nba_team_scoring.hyper")
    rows = fetch_rows()
    print(f"Fetched {len(rows)} rows from Snowflake.")
    if rows:
        types = sorted({r[2] for r in rows})
        years = sorted({r[1] for r in rows})
        print("season_type values:", types)
        print("season_year range:", years[0], "-", years[-1])
        print("Sample:", rows[0])
    write_hyper(rows, out)


if __name__ == "__main__":
    main()
