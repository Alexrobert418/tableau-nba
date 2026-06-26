"""Assemble a Tableau .twbx from a .hyper extract by generating the .twb XML.

Tableau has no headless authoring API, so we hand-author a minimal workbook:
two worksheets over the embedded Hyper extract (a federated connection) —
  1. "Made FGs by Team"   : bar, made field goals by team (regular season)
  2. "Made FGs by Season" : line, league-wide made field goals by season
— laid out together on the "NBA Scoring Overview" dashboard.

Usage:  python publish/build_workbook.py <input.hyper> <output.twbx>
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

# Relative path of the extract inside the .twbx package; the connection dbname
# must match this exactly.
HYPER_REL = "Data/nba_team_scoring.hyper"

DS = "federated.nba"
HYPERCONN = "hyper.nba"

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
        <style />
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Bar' />
            <encodings>
              <color column='[{DS}].[sum:MADE_FIELD_GOALS:qk]' />
            </encodings>
          </pane>
        </panes>
        <rows>[{DS}].[none:TEAM_NAME:nk]</rows>
        <cols>[{DS}].[sum:MADE_FIELD_GOALS:qk]</cols>
      </table>
    </worksheet>
    <worksheet name='Made FGs by Season'>
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
        <style />
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Line' />
          </pane>
        </panes>
        <rows>[{DS}].[sum:MADE_FIELD_GOALS:qk]</rows>
        <cols>[{DS}].[none:SEASON_YEAR:ok]</cols>
      </table>
    </worksheet>
  </worksheets>
  <dashboards>
    <dashboard name='NBA Scoring Overview'>
      <style />
      <size maxheight='1100' maxwidth='1200' minheight='1100' minwidth='1200' />
      <zones>
        <zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>
          <zone h='32000' id='2' name='Made FGs by Season' w='99000' x='500' y='500'>
            <zone-style>
              <format attr='border-color' value='#000000' />
              <format attr='border-style' value='none' />
              <format attr='border-width' value='0' />
              <format attr='margin' value='4' />
            </zone-style>
          </zone>
          <zone h='66500' id='3' name='Made FGs by Team' w='99000' x='500' y='33000'>
            <zone-style>
              <format attr='border-color' value='#000000' />
              <format attr='border-style' value='none' />
              <format attr='border-width' value='0' />
              <format attr='margin' value='4' />
            </zone-style>
          </zone>
        </zone>
      </zones>
    </dashboard>
  </dashboards>
  <windows source-height='30'>
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
    <window class='worksheet' name='Made FGs by Season'>
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

    # Sanity: XML must be well-formed.
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
