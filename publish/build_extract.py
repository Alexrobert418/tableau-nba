"""Build a Tableau .hyper extract from the dbt-modeled NBA marts in Snowflake.

Reads `NBA.DBT_DEMO.MART_TEAM_SCORING_BY_SEASON` and writes a single-table
Hyper extract (schema "Extract", table "Extract" — the Tableau convention) so a
workbook can embed it. Connection uses key-pair auth (same key the Snowflake MCP
uses); we only read the key to authenticate.

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

QUERY = """
SELECT
    season_id,
    MOD(season_id, 10000) AS season_year,
    CASE FLOOR(season_id / 10000)
        WHEN 1 THEN 'Pre-season'
        WHEN 2 THEN 'Regular'
        WHEN 4 THEN 'Playoffs'
        ELSE 'Other'
    END AS season_type,
    team_id,
    team_name,
    games,
    made_field_goals,
    free_throw_events
FROM NBA.DBT_DEMO.MART_TEAM_SCORING_BY_SEASON
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
    # Normalize: ints for numeric cols, str/None for text.
    norm = []
    for (sid, syear, stype, tid, tname, games, fg, ft) in rows:
        norm.append([
            int(sid),
            int(syear),
            str(stype),
            None if tid is None else int(tid),
            None if tname is None else str(tname),
            None if games is None else int(games),
            None if fg is None else int(fg),
            None if ft is None else int(ft),
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
            col("MADE_FIELD_GOALS", SqlType.big_int()),
            col("FREE_THROW_EVENTS", SqlType.big_int()),
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
        print("Sample:", rows[0])
    write_hyper(rows, out)


if __name__ == "__main__":
    main()
