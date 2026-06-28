"""Assemble a Tableau .twbx from a .hyper extract by generating the .twb XML.

Tableau has no headless authoring API, so we hand-author the workbook. The
"NBA Scoring Overview" dashboard (Lynk-branded, purple #6749F4 on white):
  - purple title banner
  - 4 KPI stat tiles : Total Points / League PPG / Seasons / Teams
  - line   : league points-per-game by season (purple)
  - scatter: offense (PPG) vs defense (opp PPG) per team, colored by win %
  - bar    : win % by team (near-black, sorted, all 30)
Ratios (PPG, opp PPG, win %) are aggregate calculated fields over the embedded
Hyper extract (team x season grain). A SEASON_TYPE filter card is global.

Usage:  python publish/build_workbook.py <input.hyper> <output.twbx>
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

HYPER_REL = "Data/nba_team_scoring.hyper"
DS = "federated.nba"
HYPERCONN = "hyper.nba"

# --- Lynk brand palette (from getlynk.ai) ---
ACCENT = "#6749F4"
INK = "#171717"
LABEL = "#78737D"
BANNERTXT = "#FFFFFF"

BLANK_TITLE = "<layout-options><title><formatted-text><run>&#160;</run></formatted-text></title></layout-options>"

# Regular-season filter applied to every worksheet (the season-type filter card
# lets a signed-in viewer switch this).
FILTER = f"""          <filter class='categorical' column='[{DS}].[none:SEASON_TYPE:nk]'>
            <groupfilter function='member' level='[none:SEASON_TYPE:nk]' member='&quot;Regular Season&quot;' />
          </filter>
          <slices>
            <column>[{DS}].[none:SEASON_TYPE:nk]</column>
          </slices>"""

SEASON_TYPE_DEP = "<column datatype='string' name='[SEASON_TYPE]' role='dimension' type='nominal' />\n            <column-instance column='[SEASON_TYPE]' derivation='None' name='[none:SEASON_TYPE:nk]' pivot='key' type='nominal' />"

# base measure columns referenced by the calcs (needed in dependencies)
BASE_MEASURES = (
    "<column datatype='integer' name='[GAMES]' role='measure' type='quantitative' />\n"
    "            <column datatype='integer' name='[WINS]' role='measure' type='quantitative' />\n"
    "            <column datatype='real' name='[POINTS_FOR]' role='measure' type='quantitative' />\n"
    "            <column datatype='real' name='[POINTS_AGAINST]' role='measure' type='quantitative' />"
)
CALC_PPG = "<column caption='Points Per Game' datatype='real' name='[PPG]' role='measure' type='quantitative'><calculation class='tableau' formula='SUM([POINTS_FOR]) / SUM([GAMES])' /></column>"
CALC_OPP = "<column caption='Opp Points Per Game' datatype='real' name='[OPP_PPG]' role='measure' type='quantitative'><calculation class='tableau' formula='SUM([POINTS_AGAINST]) / SUM([GAMES])' /></column>"
CALC_WIN = "<column caption='Win %' datatype='real' default-format='p0%' name='[WIN_PCT]' role='measure' type='quantitative'><calculation class='tableau' formula='SUM([WINS]) / SUM([GAMES])' /></column>"


def kpi(name: str, value_ref: str, deps: str) -> str:
    return f"""    <worksheet name='{name}'>
      {BLANK_TITLE}
      <table>
        <view>
          <datasources>
            <datasource caption='NBA Team Scoring (dbt)' name='{DS}' />
          </datasources>
          <datasource-dependencies datasource='{DS}'>
            {SEASON_TYPE_DEP}
            {deps}
          </datasource-dependencies>
{FILTER}
        </view>
        <style>
          <style-rule element='mark'>
            <format attr='mark-color' value='{ACCENT}' />
            <format attr='font-size' value='24' />
          </style-rule>
        </style>
        <panes>
          <pane>
            <view><breakdown value='auto' /></view>
            <mark class='Text' />
            <encodings>
              <text column='[{DS}].{value_ref}' />
            </encodings>
          </pane>
        </panes>
        <rows></rows>
        <cols></cols>
      </table>
    </worksheet>
"""


def label_zone(zid: int, x: int, w: int, text: str) -> str:
    return f"""          <zone h='1800' id='{zid}' type-v2='text' w='{w}' x='{x}' y='4000'>
            <formatted-text><run bold='true' fontcolor='{LABEL}' fontsize='9'>{text}</run></formatted-text>
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
    return f"""          <zone h='7000' id='{zid}' name='{name}' w='{w}' x='{x}' y='5800'>
            <zone-style>
              <format attr='border-color' value='#E5E5E5' />
              <format attr='border-style' value='solid' />
              <format attr='border-width' value='1' />
              <format attr='margin' value='4' />
            </zone-style>
          </zone>
"""


def chart_zone(zid: int, name: str, y: int, h: int) -> str:
    return f"""          <zone h='{h}' id='{zid}' name='{name}' w='100000' x='0' y='{y}'>
            <zone-style>
              <format attr='border-style' value='none' />
              <format attr='border-width' value='0' />
              <format attr='margin' value='6' />
            </zone-style>
          </zone>
"""


KPIS = (
    kpi("Total Points", "[sum:POINTS_FOR:qk]",
        "<column datatype='real' default-format='#,##0' name='[POINTS_FOR]' caption='Points For' role='measure' type='quantitative' />\n"
        "            <column-instance column='[POINTS_FOR]' derivation='Sum' name='[sum:POINTS_FOR:qk]' pivot='key' type='quantitative' />")
    + kpi("League PPG", "[PPG]",
        BASE_MEASURES + "\n            " + CALC_PPG)
    + kpi("Seasons", "[ctd:SEASON_YEAR:qk]",
        "<column datatype='integer' name='[SEASON_YEAR]' caption='Season' role='dimension' type='ordinal' />\n"
        "            <column-instance column='[SEASON_YEAR]' derivation='CountD' name='[ctd:SEASON_YEAR:qk]' pivot='key' type='quantitative' />")
    + kpi("Teams", "[ctd:TEAM_ID:qk]",
        "<column datatype='integer' name='[TEAM_ID]' role='dimension' type='ordinal' />\n"
        "            <column-instance column='[TEAM_ID]' derivation='CountD' name='[ctd:TEAM_ID:qk]' pivot='key' type='quantitative' />")
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
          <map key='[WINS]' value='[Extract].[WINS]' />
          <map key='[POINTS_FOR]' value='[Extract].[POINTS_FOR]' />
          <map key='[POINTS_AGAINST]' value='[Extract].[POINTS_AGAINST]' />
        </cols>
      </connection>
      <column datatype='integer' name='[SEASON_ID]' role='dimension' type='ordinal' />
      <column datatype='integer' name='[SEASON_YEAR]' caption='Season' role='dimension' type='ordinal' />
      <column datatype='string' name='[SEASON_TYPE]' role='dimension' type='nominal' />
      <column datatype='integer' name='[TEAM_ID]' role='dimension' type='ordinal' />
      <column datatype='string' name='[TEAM_NAME]' caption='Team' role='dimension' type='nominal' />
      <column datatype='integer' name='[GAMES]' role='measure' type='quantitative' />
      <column datatype='integer' name='[WINS]' role='measure' type='quantitative' />
      <column datatype='real' default-format='#,##0' name='[POINTS_FOR]' caption='Points For' role='measure' type='quantitative' />
      <column datatype='real' default-format='#,##0' name='[POINTS_AGAINST]' caption='Points Against' role='measure' type='quantitative' />
      <column caption='Points Per Game' datatype='real' name='[PPG]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='SUM([POINTS_FOR]) / SUM([GAMES])' />
      </column>
      <column caption='Opp Points Per Game' datatype='real' name='[OPP_PPG]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='SUM([POINTS_AGAINST]) / SUM([GAMES])' />
      </column>
      <column caption='Win %' datatype='real' default-format='p0%' name='[WIN_PCT]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='SUM([WINS]) / SUM([GAMES])' />
      </column>
    </datasource>
  </datasources>
  <worksheets>
{KPIS}    <worksheet name='PPG by Season'>
      <table>
        <view>
          <datasources>
            <datasource caption='NBA Team Scoring (dbt)' name='{DS}' />
          </datasources>
          <datasource-dependencies datasource='{DS}'>
            {SEASON_TYPE_DEP}
            <column datatype='integer' name='[SEASON_YEAR]' caption='Season' role='dimension' type='ordinal' />
            <column-instance column='[SEASON_YEAR]' derivation='None' name='[none:SEASON_YEAR:ok]' pivot='key' type='ordinal' />
            {BASE_MEASURES}
            {CALC_PPG}
          </datasource-dependencies>
{FILTER}
        </view>
        <style>
          <style-rule element='mark'><format attr='mark-color' value='{ACCENT}' /></style-rule>
        </style>
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class='Line' />
          </pane>
        </panes>
        <rows>[{DS}].[PPG]</rows>
        <cols>[{DS}].[none:SEASON_YEAR:ok]</cols>
      </table>
    </worksheet>
    <worksheet name='PPG Heatmap'>
      <table>
        <view>
          <datasources>
            <datasource caption='NBA Team Scoring (dbt)' name='{DS}' />
          </datasources>
          <datasource-dependencies datasource='{DS}'>
            {SEASON_TYPE_DEP}
            <column datatype='integer' name='[SEASON_YEAR]' caption='Season' role='dimension' type='ordinal' />
            <column-instance column='[SEASON_YEAR]' derivation='None' name='[none:SEASON_YEAR:ok]' pivot='key' type='ordinal' />
            <column datatype='string' name='[TEAM_NAME]' caption='Team' role='dimension' type='nominal' />
            <column-instance column='[TEAM_NAME]' derivation='None' name='[none:TEAM_NAME:nk]' pivot='key' type='nominal' />
            {BASE_MEASURES}
            {CALC_PPG}
          </datasource-dependencies>
{FILTER}
          <sort class='computed' column='[{DS}].[none:TEAM_NAME:nk]' direction='DESC' using='[{DS}].[PPG]' />
        </view>
        <style />
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class='Square' />
            <encodings>
              <color column='[{DS}].[PPG]' />
            </encodings>
          </pane>
        </panes>
        <rows>[{DS}].[none:TEAM_NAME:nk]</rows>
        <cols>[{DS}].[none:SEASON_YEAR:ok]</cols>
      </table>
    </worksheet>
    <worksheet name='Win Pct by Team'>
      <table>
        <view>
          <datasources>
            <datasource caption='NBA Team Scoring (dbt)' name='{DS}' />
          </datasources>
          <datasource-dependencies datasource='{DS}'>
            {SEASON_TYPE_DEP}
            <column datatype='string' name='[TEAM_NAME]' caption='Team' role='dimension' type='nominal' />
            <column-instance column='[TEAM_NAME]' derivation='None' name='[none:TEAM_NAME:nk]' pivot='key' type='nominal' />
            {BASE_MEASURES}
            {CALC_WIN}
          </datasource-dependencies>
{FILTER}
          <sort class='computed' column='[{DS}].[none:TEAM_NAME:nk]' direction='DESC' using='[{DS}].[WIN_PCT]' />
        </view>
        <style>
          <style-rule element='mark'><format attr='mark-color' value='{INK}' /></style-rule>
        </style>
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class='Bar' />
          </pane>
        </panes>
        <rows>[{DS}].[none:TEAM_NAME:nk]</rows>
        <cols>[{DS}].[WIN_PCT]</cols>
      </table>
    </worksheet>
  </worksheets>
  <dashboards>
    <dashboard name='NBA Scoring Overview'>
      <style />
      <size maxheight='2000' maxwidth='1700' minheight='2000' minwidth='1700' />
      <zones>
        <zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>
          <zone h='4000' id='10' type-v2='text' w='100000' x='0' y='0'>
            <formatted-text><run bold='true' fontcolor='{BANNERTXT}' fontsize='22'>NBA Scoring Overview</run></formatted-text>
            <zone-style>
              <format attr='background-color' value='{ACCENT}' />
              <format attr='background-opacity' value='1.0' />
              <format attr='border-style' value='none' />
              <format attr='border-width' value='0' />
              <format attr='margin' value='0' />
              <format attr='padding-top' value='10' />
              <format attr='padding-left' value='16' />
            </zone-style>
          </zone>
{label_zone(20, 0, 25000, "TOTAL POINTS SCORED")}{label_zone(21, 25000, 25000, "LEAGUE PPG")}{label_zone(22, 50000, 25000, "REGULAR SEASONS")}{label_zone(23, 75000, 25000, "TEAMS")}{number_zone(11, 0, 25000, "Total Points")}{number_zone(12, 25000, 25000, "League PPG")}{number_zone(13, 50000, 25000, "Seasons")}{number_zone(14, 75000, 25000, "Teams")}{chart_zone(15, "PPG by Season", 13000, 13000)}{chart_zone(16, "PPG Heatmap", 26000, 36000)}{chart_zone(17, "Win Pct by Team", 62000, 38000)}        </zone>
      </zones>
    </dashboard>
  </dashboards>
  <windows source-height='30'>
    <window class='worksheet' name='Total Points' />
    <window class='worksheet' name='League PPG' />
    <window class='worksheet' name='Seasons' />
    <window class='worksheet' name='Teams' />
    <window class='worksheet' name='PPG by Season' />
    <window class='worksheet' name='PPG Heatmap' />
    <window class='worksheet' name='Win Pct by Team'>
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
        <viewpoint name='Total Points' />
        <viewpoint name='League PPG' />
        <viewpoint name='Seasons' />
        <viewpoint name='Teams' />
        <viewpoint name='PPG by Season' />
        <viewpoint name='PPG Heatmap' />
        <viewpoint name='Win Pct by Team' />
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
    minidom.parseString(TWB)

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
