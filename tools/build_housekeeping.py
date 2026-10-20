"""Restore housekeeping on the 20 October Vault screen without editing the Vault.

Input is the read-only Vault snapshot; output is a full-screen paste and an update
of the existing real-tenant-export-based stats package. Never writes credentials.
"""
from pathlib import Path
import copy
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORK = Path('C:/Temp/flow-check/housekeeping-20261020')
MAIN = 'https://modgovuk.sharepoint.com/teams/1598'
CCF = MAIN + '/CCF'
BASE = ROOT / 'flows/RebuildLibraryStats_MultiSite_flow_import.zip'
OUT = ROOT / 'flows/RebuildLibraryStats_FileCounts_flow_import.zip'


def build_flow():
    with zipfile.ZipFile(BASE) as z:
        files = {n: z.read(n) for n in z.namelist()}
    name = next(n for n in files if n.endswith('/definition.json'))
    doc = json.loads(files[name])
    definition = doc['properties']['definition']
    sites = definition['actions']['Apply_to_each_Site']
    sites['foreach'] = f"@createArray('{MAIN}', '{CCF}')"
    sites['runtimeConfiguration'] = {'concurrency': {'repetitions': 1}}
    sites['runAfter'] = {'Initialize_FileCount': ['Succeeded']}
    actions = sites['actions']
    actions['Get_Libraries']['inputs']['parameters']['parameters/uri'] = '_api/web/lists?$filter=BaseTemplate eq 101 and Hidden eq false&$select=Id,Title,Created,ItemCount,RootFolder/ServerRelativeUrl&$expand=RootFolder&$top=5000'
    actions['Select_LibraryStats']['inputs']['select']['Id'] = "@item()?['Id']"
    loop = actions['Apply_to_each_Library']
    loop['runtimeConfiguration'] = {'concurrency': {'repetitions': 1}}
    lookup = loop['actions']['Get_Existing_Row']['inputs']['parameters']
    lookup['dataset'] = MAIN
    # Library URLs may contain apostrophes. Escape the OData literal before URL encoding.
    lookup['parameters/uri'] = "_api/web/lists/getbytitle('LibraryFilePlan')/items?$filter=LibraryUrl eq '@{encodeUriComponent(replace(items('Apply_to_each_Library')?['Url'], decodeUriComponent('%27'), decodeUriComponent('%27%27')))}'&$select=Id&$top=1"
    tracked = loop['actions']['If_Not_Tracked']['else']['actions']
    update = tracked.pop('Update_LibraryFilePlan_Row')
    http_template = copy.deepcopy(actions['Get_Libraries'])
    http_template['runAfter'] = {}
    def http(uri):
        action = copy.deepcopy(http_template)
        action['inputs']['parameters']['parameters/uri'] = uri
        return action
    def setvar(variable, value, after=None):
        return {'type': 'SetVariable', 'inputs': {'name': variable, 'value': value}, 'runAfter': {after: ['Succeeded']} if after else {}}
    tracked['Reset_FileCount'] = setvar('fpFileCount', 0)
    tracked['Set_First_Page'] = setvar('fpNextPage', "@concat('_api/web/lists(guid', decodeUriComponent('%27'), items('Apply_to_each_Library')?['Id'], decodeUriComponent('%27'), ')/items?$select=Id,FileSystemObjectType&$top=5000')", 'Reset_FileCount')
    page = http("@variables('fpNextPage')")
    pages = {
        'Get_Item_Page': page,
        'Files_In_Page': {'type': 'Query', 'inputs': {'from': "@body('Get_Item_Page')['d']['results']", 'where': "@equals(item()?['FileSystemObjectType'], 0)"}, 'runAfter': {'Get_Item_Page': ['Succeeded']}},
        'Add_Page_FileCount': {'type': 'IncrementVariable', 'inputs': {'name': 'fpFileCount', 'value': "@length(body('Files_In_Page'))"}, 'runAfter': {'Files_In_Page': ['Succeeded']}},
        'Set_Next_Page': setvar('fpNextPage', "@if(empty(body('Get_Item_Page')?['d']?['__next']), '', last(split(body('Get_Item_Page')?['d']?['__next'], '/_api/')))", 'Add_Page_FileCount'),
    }
    # Continuation URI must retain _api/; split removes its leading slash only.
    pages['Set_Next_Page']['inputs']['value'] = "@if(empty(body('Get_Item_Page')?['d']?['__next']), '', concat('_api/', last(split(body('Get_Item_Page')?['d']?['__next'], '/_api/'))))"
    tracked['Count_All_File_Pages'] = {'type': 'Until', 'expression': "@equals(variables('fpNextPage'), '')", 'limit': {'count': 5000, 'timeout': 'PT1H'}, 'operationOptions': 'FailWhenLimitsReached', 'actions': pages, 'runAfter': {'Set_First_Page': ['Succeeded']}}
    update['runAfter'] = {'Count_All_File_Pages': ['Succeeded']}
    params = update['inputs']['parameters']
    params['dataset'] = MAIN
    params['parameters/body'] = '{"__metadata":{"type":"SP.Data.LibraryFilePlanListItem"},"LibraryCreated":"@{items(\'Apply_to_each_Library\')?[\'Created\']}","LibraryItemCount":@{items(\'Apply_to_each_Library\')?[\'ItemCount\']},"LibraryFileCount":@{variables(\'fpFileCount\')}}'
    tracked['Update_LibraryFilePlan_Row'] = update
    definition['actions'] = {
        'Initialize_NextPage': {'type': 'InitializeVariable', 'inputs': {'variables': [{'name': 'fpNextPage', 'type': 'string', 'value': ''}]}, 'runAfter': {}},
        'Initialize_FileCount': {'type': 'InitializeVariable', 'inputs': {'variables': [{'name': 'fpFileCount', 'type': 'integer', 'value': 0}]}, 'runAfter': {'Initialize_NextPage': ['Succeeded']}},
        'Apply_to_each_Site': sites,
    }
    definition['description'] = 'Housekeeping: main + CCF; real library Created, existing item count, and paged file-only count (including nested folders). Writes only tracked central LibraryFilePlan rows. Sequential loops protect counters. No partial count is saved if pagination fails.'
    files[name] = json.dumps(doc, indent=2).encode('utf-8')
    with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, data in files.items():
            z.writestr(n, data)
    print('Built', OUT.name)


def build_screen():
    source = (WORK / 'scrManageLibraries.vault.yaml').read_text(encoding='utf-8')
    text = source
    file_filter = '(Switch(Coalesce(drpMgmtFileCount.Selected.Value, "All file counts"), "0 files", !IsBlank(LibraryFileCount) && LibraryFileCount = 0, "5 or fewer files", !IsBlank(LibraryFileCount) && LibraryFileCount <= 5, "10 or fewer files", !IsBlank(LibraryFileCount) && LibraryFileCount <= 10, "Stats missing", IsBlank(LibraryFileCount) || IsBlank(LibraryCreated), true))'
    age_filter = '(Switch(Coalesce(drpMgmtAge.Selected.Value, "Any library age"), "6+ months old", !IsBlank(LibraryCreated) && LibraryCreated <= DateAdd(Today(), -6, TimeUnit.Months), "1+ year old", !IsBlank(LibraryCreated) && LibraryCreated <= DateAdd(Today(), -12, TimeUnit.Months), true))'
    condition = '(IsBlank(Trim(txtSearch_2.Text)) || txtSearch_2.Text in EffectiveName) && (Coalesce(drpTeamFilter.Selected.TeamName, "All Teams") = "All Teams" || TeamName = drpTeamFilter.Selected.TeamName) && ' + file_filter + ' && ' + age_filter
    initial = 'ClearCollect(colManageFiltered, AddColumns(colFilePlanFiltered, NameSaysLtd,'
    assert initial in text
    text = text.replace(initial, 'ClearCollect(colManageFiltered, AddColumns(Filter(colFilePlanFiltered, ' + condition + '), NameSaysLtd,', 1)
    pattern = r'\(IsBlank\(Trim\(txtSearch_2.Text\)\) \|\| txtSearch_2.Text in EffectiveName\) &&\s*\(drpTeamFilter.Selected.TeamName = "All Teams" \|\| TeamName = drpTeamFilter.Selected.TeamName\)'
    text, count = re.subn(pattern, condition, text)
    assert count >= 4, count
    expand = '!IsBlank(Trim(txtSearch_2.Text)) || drpTeamFilter.Selected.TeamName <> "All Teams"'
    text = text.replace(expand, expand + ' || Coalesce(drpMgmtFileCount.Selected.Value, "All file counts") <> "All file counts" || Coalesce(drpMgmtAge.Selected.Value, "Any library age") <> "Any library age"')

    def block(name):
        m = re.search(r'(?m)^( +)- ' + re.escape(name) + r':\n', text)
        assert m, name
        end = re.search(r'(?m)^ {0,' + str(len(m[1])) + r'}- \w', text[m.end():])
        return m.start(), m.end() + end.start() if end else len(text)

    def prop(name, key, value):
        nonlocal text
        start, end = block(name)
        chunk = text[start:end]
        pat = r'(?m)^( +)' + re.escape(key) + r':[^\n]*(?:\n\1  [^\n]*)*'
        chunk, n = re.subn(pat, lambda m: m[1] + key + ': ' + value, chunk, count=1)
        assert n == 1, (name, key)
        text = text[:start] + chunk + text[end:]

    for name in ['recRowBg_1', 'recMgmtTeamHeaderBg', 'recMgmtSubTeamHeaderBg']:
        prop(name, 'Height', '=100')
    prop('galManage', 'TemplateSize', '=100')
    is_old_empty = '!IsBlank(ThisItem.LibraryFileCount) && ThisItem.LibraryFileCount = 0 && !IsBlank(ThisItem.LibraryCreated) && ThisItem.LibraryCreated <= DateAdd(Today(), -6, TimeUnit.Months)'
    prop('recRowBg_1', 'Fill', '=If(' + is_old_empty + ', RGBA(255, 229, 229, 1), If(ThisItem.LibraryUrl in colSelectedLibraries.LibraryUrl, RGBA(238, 233, 255, 1), If(ThisItem.IsLimited, RGBA(253, 240, 236, 1), RGBA(255, 255, 255, 1))))')
    prop('recRowBg_1', 'BorderColor', '=If(' + is_old_empty + ', RGBA(190, 50, 50, 1), If(ThisItem.LibraryUrl in colSelectedLibraries.LibraryUrl, RGBA(124, 77, 255, 1), RGBA(230, 233, 245, 1)))')
    prop('recRowBg_1', 'BorderThickness', '=If(ThisItem.LibraryUrl in colSelectedLibraries.LibraryUrl, 2, 1)')
    prop('lblRowSubTeam', 'Height', '=48')
    prop('lblSubtitle_1', 'Text', '=\"Pale red row = zero files and created at least six months ago. Counts include files inside folders; folders themselves are excluded. Use the filters below to narrow the list.\"')
    prop('lblSubtitle_1', 'Width', '=1280')

    # Reuse the proven complete filter/group/expand handler from the uploaded screen.
    start, end = block('txtSearch_2')
    onchange = re.search(r'(?ms)^            OnChange: \|-\n(.*?)(?=^            \w+:)', text[start:end])[1]
    def dropdown(name, items, default, x, width):
        return f'''      - {name}:
          Control: ModernDropdown@1.0.3
          Properties:
            Default: '={{Value: "{default}"}}'
            Height: =44
            ItemDisplayText: =ThisItem.Value
            Items: ={json.dumps(items)}
            OnChange: |-
{onchange}            Visible: =varIsAdmin
            Width: ={width}
            X: ={x}
            Y: =166
'''
    controls = dropdown('drpMgmtFileCount', ['All file counts', '0 files', '5 or fewer files', '10 or fewer files', 'Stats missing'], 'All file counts', 684, 190)
    controls += dropdown('drpMgmtAge', ['Any library age', '6+ months old', '1+ year old'], 'Any library age', 890, 190)
    controls += '''      - btnReloadLibraryStats:
          Control: ModernButton@1.0.0
          Properties:
            Height: =44
            OnSelect: |-
              =Refresh(LibraryFilePlan);
              ClearCollect(colFilePlan, LibraryFilePlan);
              ClearCollect(colFilePlanFiltered, AddColumns(colFilePlan, TeamName, If(IsBlank(Team.Value) || Team.Value = "", "Uncategorised", Team.Value), SubTeamName, Coalesce(SubTeam.Value, ""), EffectiveName, If(IsBlank(PrettyName) || PrettyName = "", Title, PrettyName)));
''' + onchange.replace('              =ClearCollect(', '              ClearCollect(', 1).rstrip() + ''';
              Notify("Latest saved stats loaded. To update the counts, run FP - Rebuild Library Stats in Power Automate, wait for it to finish, then reload here.", NotificationType.Information)
            Text: ="Reload saved stats"
            Visible: =varIsAdmin
            Width: =210
            X: =1096
            Y: =166
'''
    text = text.replace('      - lblSelectedCount:', controls + '      - lblSelectedCount:', 1)
    stats_text = '="Created: " & If(IsBlank(ThisItem.LibraryCreated), "not checked", Text(ThisItem.LibraryCreated, "dd mmm yyyy")) & "   |   Files: " & If(IsBlank(ThisItem.LibraryFileCount), "not checked", Text(ThisItem.LibraryFileCount, "#,##0")) & If(' + is_old_empty + ', "   |   REVIEW: empty and 6+ months old", "")'
    label = f'''            - lblRowHousekeeping:
                Control: Label@2.5.1
                Properties:
                  Color: =If({is_old_empty}, RGBA(150, 30, 30, 1), RGBA(80, 80, 100, 1))
                  Font: =Font.'Open Sans'
                  FontWeight: =FontWeight.Semibold
                  Height: =24
                  Size: =12
                  Text: '{stats_text.replace(chr(39), chr(39)*2)}'
                  Visible: =ThisItem.RowType = "Library"
                  Width: =1050
                  X: =80
                  Y: =74
'''
    text = text.replace('            - lblRowLibURL:', label + '            - lblRowLibURL:', 1)
    # Preserve a complete UTF-8 screen, including its existing delete/edit handlers.
    out = WORK / 'scrManageLibraries.v2.9.yaml'
    out.write_text(text, encoding='utf-8')
    print('Built', out, 'filter sites:', count)


if __name__ == '__main__':
    build_flow()
    build_screen()
