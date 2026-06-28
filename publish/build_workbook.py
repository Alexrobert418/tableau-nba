"""Assemble a Tableau .twbx from a .hyper extract by generating the .twb XML.

Tableau has no headless authoring API, so we hand-author the workbook. Layout
of the "NBA Scoring Overview" dashboard (Lynk-branded, purple #6749F4 on white):
  - purple title banner
  - 3 KPI stat tiles  : Total Made FGs / Seasons / Teams (regular season)
    (label = a text zone; value = a title-less worksheet so the number is clean)
  - line worksheet    : league-wide made field goals by season (purple)
  - bar worksheet     : made field goals by team (near-black, sorted, all 30)
All worksheets read the embedded Hyper extract via a federated connection.

Usage:  python publish/build_workbook.py <input.hyper> <output.twbx>
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

# Relative path of the extract inside the .twbx package; connection dbname must match.
HYPER_REL = "Data/nba_team_scoring.hyper"

DS = "federated.nba"
HYPERCONN = "hyper.nba"

# --- Lynk brand palette (extracted from getlynk.ai) ---
ACCENT = "#6749F4"   # Lynk purple — hero accent
INK = "#171717"      # near-black — bars / body
LABEL = "#78737D"    # muted grey — KPI labels
BANNERTXT = "#FFFFFF"
BLANK_TITLE = "<layout-options><title><formatted-text><run>&#160;</run></formatted-text></title></layout-options>"


def kpi_worksheet(name: str, value_instance: str, deps_extra: str) -> str:
    """A title-less BAN worksheet: one big purple number, filtered to regular season."""
    return f"""    <worksheet name='{name}'>
      {BLANK_TITLE}
      <table>
        <view>
          <datasources>
            <datasource caption='NBA Team Scoring (dbt)' name='{DS}' />
          </datasources>
          <datasource-dependencies datasource='{DS}'>
            <column datatype='string' name='[SEASON_TYPE]' role='dimension' type='nominal' />
            {deps_extra}
            <column-instance column='[SEASON_TYPE]' derivation='None' name='[none:SEASON_TYPE:nk]' pivot='key' type='nominal' />
          </datasource-dependencies>
          <filter class='categorical' column='[{DS}].[none:SEASON_TYPE:nk]'>
            <groupfilter function='member' level='[none:SEASON_TYPE:nk]' member='&quot;Regular&quot;' />
          </filter>
          <slices>
            <column>[{DS}].[none:SEASON_TYPE:nk]</column>
          </slices>
        </view>
        <style>
          <style-rule element='mark'>
            <format attr='mark-color' value='{ACCENT}' />
            <format attr='font-size' value='26' />
          </style-rule>
        </style>
        <panes>
          <pane>
            <view><breakdown value='auto' /></view>
            <mark class='Text' />
            <encodings>
              <text column='[{DS}].{value_instance}' />
            </encodings>
          </pane>
        </panes>
        <rows></rows>
        <cols></cols>
      </table>
    </worksheet>
"""


def label_zone(zid: int, x: int, w: int, text: str) -> str:
    return f"""          <zone h='2200' id='{zid}' type-v2='text' w='{w}' x='{x}' y='5000'>
            <formatted-text>
              <run bold='true' fontcolor='{LABEL}' fontsize='10'>{text}</run>
            </formatted-text>
            <zone-style>
              <format attr='background-color' value='#FFFFFF' />
              <format attr='border-style' value='none' />
              <format attr='margin' value='4' />
              <format attr='padding-top' value='6' />
              <format attr='padding-left' value='10' />
            </zone-style>
          </zone>
"""


def number_zone(zid: int, x: int, w: int, name: str) -> str:
    return f"""          <zone h='8800' id='{zid}' name='{name}' w='{w}' x='{x}' y='7200'>
            <zone-style>
              <format attr='border-color' value='#E5E5E5' />
              <format attr='border-style' value='solid' />
              <format attr='border-width' value='1' />
              <format attr='margin' value='4' />
            </zone-style>
          </zone>
"""


KPIS = (
    kpi_worksheet(
        "Total Made FGs",
        "[sum:MADE_FIELD_GOALS:qk]",
        "<column datatype='integer' name='[MADE_FIELD_GOALS]' caption='Made Field Goals' role='measure' type='quantitative' />\n"
        "            <column-instance column='[MADE_FIELD_GOALS]' derivation='Sum' name='[sum:MADE_FIELD_GOALS:qk]' pivot='key' type='quantitative' />",
    )
    + kpi_worksheet(
        "Seasons",
        "[ctd:SEASON_YEAR:qk]",
        "<column datatype='integer' name='[SEASON_YEAR]' caption='Season' role='dimension' type='ordinal' />\n"
        "            <column-instance column='[SEASON_YEAR]' derivation='CountD' name='[ctd:SEASON_YEAR:qk]' pivot='key' type='quantitative' />",
    )
    + kpi_worksheet(
        "Teams",
        "[ctd:TEAM_ID:qk]",
        "<column datatype='integer' name='[TEAM_ID]' role='dimension' type='ordinal' />\n"
        "            <column-instance column='[TEAM_ID]' derivation='CountD' name='[ctd:TEAM_ID:qk]' pivot='key' type='quantitative' />",
    )
)

TWB = f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook source-build='2023.3' source-platform='win' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
    <preference name='ui.shelf.height' value='26' />
  </preferences>
  <datasources>
    <datasource caption='NBA Team Scoring (dbt)' inline='true' name='{DS}' version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='nba_team_scoring' name='{HYPERCONN}'>
            <connection class='hyper' dbname='{HYPER_REL}' default-settings='yes' schema='Extract' />
          </named-connection>
        </named-connections>
        <relation connection='{HYPERCONN}' name='Extract' table='[Extract].[Extract]' type='table' />
        <cols>
          <map key='[SEASON_ID]' value='[Extract].[SEASON_ID]' />
          <map key='[SEASON_YEAR]' value='[Extract].[SEASON_YEAR]' />
          <map key='[SEASON_TYPE]' value='[Extract].[SEASON_TYPE]' />
          <map key='[TEAM_ID]' value='[Extract].[TEAM_ID]' />
          <map key='[TEAM_NAME]' value='[Extract].[TEAM_NAME]' />
          <map key='[GAMES]' value='[Extract].[GAMES]' />
          <map key='[MADE_FIELD_GOALS]' value='[Extract].[MADE_FIELD_GOALS]' />
          <map key='[FREE_THROW_EVENTS]' value='[Extract].[FREE_THROW_EVENTS]' />
        </cols>
      </connection>
      <column datatype='integer' name='[SEASON_ID]' role='dimension' type='ordinal' />
      <column datatype='integer' name='[SEASON_YEAR]' caption='Season' role='dimension' type='ordinal' />
      <column datatype='string' name='[SEASON_TYPE]' role='dimension' type='nominal' />
      <column datatype='integer' name='[TEAM_ID]' role='dimension' type='ordinal' />
      <column datatype='string' name='[TEAM_NAME]' caption='Team' role='dimension' type='nominal' />
      <column datatype='integer' name='[GAMES]' role='measure' type='quantitative' />
      <column datatype='integer' name='[MADE_FIELD_GOALS]' caption='Made Field Goals' role='measure' type='quantitative' />
      <column datatype='integer' name='[FREE_THROW_EVENTS]' caption='Free Throw Events' role='measure' type='quantitative' />
    </datasource>
  </datasources>
  <worksheets>
{KPIS}    <worksheet name='Made FGs by Season'>
      <table>
        <view>
          <datasources>
            <datasource caption='NBA Team Scoring (dbt)' name='{DS}' />
          </datasources>
          <datasource-dependencies datasource='{DS}'>
            <column datatype='integer' name='[SEASON_YEAR]' caption='Season' role='dimension' type='ordinal' />
            <column datatype='string' name='[SEASON_TYPE]' role='dimension' type='nominal' />
            <column datatype='integer' name='[MADE_FIELD_GOALS]' caption='Made Field Goals' role='measure' type='quantitative' />
            <column-instance column='[SEASON_YEAR]' derivation='None' name='[none:SEASON_YEAR:ok]' pivot='key' type='ordinal' />
            <column-instance column='[SEASON_TYPE]' derivation='None' name='[none:SEASON_TYPE:nk]' pivot='key' type='nominal' />
            <column-instance column='[MADE_FIELD_GOALS]' derivation='Sum' name='[sum:MADE_FIELD_GOALS:qk]' pivot='key' type='quantitative' />
          </datasource-dependencies>
          <filter class='categorical' column='[{DS}].[none:SEASON_TYPE:nk]'>
            <groupfilter function='member' level='[none:SEASON_TYPE:nk]' member='&quot;Regular&quot;' />
          </filter>
          <slices>
            <column>[{DS}].[none:SEASON_TYPE:nk]</column>
          </slices>
        </view>
        <style>
          <style-rule element='mark'>
            <format attr='mark-color' value='{ACCENT}' />
          </style-rule>
        </style>
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class='Line' />
          </pane>
        </panes>
        <rows>[{DS}].[sum:MADE_FIELD_GOALS:qk]</rows>
        <cols>[{DS}].[none:SEASON_YEAR:ok]</cols>
      </table>
    </worksheet>
    <worksheet name='Made FGs by Team'>
      <table>
        <view>
          <datasources>
            <datasource caption='NBA Team Scoring (dbt)' name='{DS}' />
          </datasources>
          <datasource-dependencies datasource='{DS}'>
            <column datatype='string' name='[TEAM_NAME]' caption='Team' role='dimension' type='nominal' />
            <column datatype='string' name='[SEASON_TYPE]' role='dimension' type='nominal' />
            <column datatype='integer' name='[MADE_FIELD_GOALS]' caption='Made Field Goals' role='measure' type='quantitative' />
            <column-instance column='[TEAM_NAME]' derivation='None' name='[none:TEAM_NAME:nk]' pivot='key' type='nominal' />
            <column-instance column='[SEASON_TYPE]' derivation='None' name='[none:SEASON_TYPE:nk]' pivot='key' type='nominal' />
            <column-instance column='[MADE_FIELD_GOALS]' derivation='Sum' name='[sum:MADE_FIELD_GOALS:qk]' pivot='key' type='quantitative' />
          </datasource-dependencies>
          <filter class='categorical' column='[{DS}].[none:SEASON_TYPE:nk]'>
            <groupfilter function='member' level='[none:SEASON_TYPE:nk]' member='&quot;Regular&quot;' />
          </filter>
          <slices>
            <column>[{DS}].[none:SEASON_TYPE:nk]</column>
          </slices>
          <sort class='computed' column='[{DS}].[none:TEAM_NAME:nk]' direction='DESC' using='[{DS}].[sum:MADE_FIELD_GOALS:qk]' />
        </view>
        <style>
          <style-rule element='mark'>
            <format attr='mark-color' value='{INK}' />
          </style-rule>
        </style>
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class='Bar' />
          </pane>
        </panes>
        <rows>[{DS}].[none:TEAM_NAME:nk]</rows>
        <cols>[{DS}].[sum:MADE_FIELD_GOALS:qk]</cols>
      </table>
    </worksheet>
  </worksheets>
  <dashboards>
    <dashboard name='NBA Scoring Overview'>
      <style />
      <size maxheight='1600' maxwidth='1200' minheight='1600' minwidth='1200' />
      <zones>
        <zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>
          <zone h='5000' id='10' type-v2='text' w='100000' x='0' y='0'>
            <formatted-text>
              <run bold='true' fontcolor='{BANNERTXT}' fontsize='22'>NBA Scoring Overview</run>
            </formatted-text>
            <zone-style>
              <format attr='background-color' value='{ACCENT}' />
              <format attr='background-opacity' value='1.0' />
              <format attr='border-style' value='none' />
              <format attr='border-width' value='0' />
              <format attr='margin' value='0' />
              <format attr='padding-top' value='12' />
              <format attr='padding-left' value='16' />
            </zone-style>
          </zone>
{label_zone(20, 0, 33333, "TOTAL MADE FIELD GOALS")}{label_zone(21, 33333, 33334, "REGULAR SEASONS")}{label_zone(22, 66667, 33333, "TEAMS")}{number_zone(11, 0, 33333, "Total Made FGs")}{number_zone(12, 33333, 33334, "Seasons")}{number_zone(13, 66667, 33333, "Teams")}          <zone h='21000' id='14' name='Made FGs by Season' w='100000' x='0' y='16000'>
            <zone-style>
              <format attr='border-style' value='none' />
              <format attr='border-width' value='0' />
              <format attr='margin' value='6' />
            </zone-style>
          </zone>
          <zone h='63000' id='15' name='Made FGs by Team' w='100000' x='0' y='37000'>
            <zone-style>
              <format attr='border-style' value='none' />
              <format attr='border-width' value='0' />
              <format attr='margin' value='6' />
            </zone-style>
          </zone>
        </zone>
      </zones>
    </dashboard>
  </dashboards>
  <windows source-height='30'>
    <window class='worksheet' name='Total Made FGs' />
    <window class='worksheet' name='Seasons' />
    <window class='worksheet' name='Teams' />
    <window class='worksheet' name='Made FGs by Season' />
    <window class='worksheet' name='Made FGs by Team'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
      </cards>
    </window>
    <window class='dashboard' name='NBA Scoring Overview'>
      <viewpoints>
        <viewpoint name='Total Made FGs' />
        <viewpoint name='Seasons' />
        <viewpoint name='Teams' />
        <viewpoint name='Made FGs by Season' />
        <viewpoint name='Made FGs by Team' />
      </viewpoints>
      <active id='-1' />
    </window>
  </windows>
</workbook>
"""


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("Usage: python publish/build_workbook.py <input.hyper> <output.twbx>")
    hyper_in = Path(sys.argv[1])
    twbx_out = Path(sys.argv[2])
    if not hyper_in.exists():
        sys.exit(f"Hyper not found: {hyper_in}")
    twbx_out.parent.mkdir(parents=True, exist_ok=True)

    import xml.dom.minidom as minidom
    minidom.parseString(TWB)  # well-formedness check

    if twbx_out.exists():
        twbx_out.unlink()
    with zipfile.ZipFile(twbx_out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("nba_overview.twb", TWB)
        z.write(hyper_in, HYPER_REL)
    print(f"Packaged {twbx_out} ({twbx_out.stat().st_size} bytes)")
    with zipfile.ZipFile(twbx_out) as z:
        print("Contents:", z.namelist())


if __name__ == "__main__":
    main()
