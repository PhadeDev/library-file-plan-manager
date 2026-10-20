"""Focused contract checks, not a claim of tenant/Studio execution."""
from pathlib import Path
import importlib.util
import json
import re
import zipfile
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORK = Path('C:/Temp/flow-check/housekeeping-20261020')
candidate = ROOT / 'flows/RebuildLibraryStats_FileCounts_flow_import.zip'
reference = ROOT / 'flows/RebuildLibraryStats_MultiSite_flow_import.zip'
spec = importlib.util.spec_from_file_location('legacy_validator', 'C:/Users/Phaderon/Projects/PowerApps/tools/validate-flow-package.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

# The old checker forbids all variable/Until actions because its original two
# reference flows did not use them. Keep its package/body/runAfter checks and
# validate the added documented action schemas explicitly below instead.
def check_bodies(actions, path, errors):
    for name, action in actions.items():
        if action['type'] == 'OpenApiConnection':
            body = action['inputs']['parameters'].get('parameters/body')
            if body is not None and not isinstance(body, str):
                errors.append(path + '/' + name + ': body is not a JSON string')
        for child in [action.get('actions', {}), action.get('else', {}).get('actions', {})]:
            check_bodies(child, path + '/' + name, errors)
checker.check_body_strings = check_bodies
assert checker.main(str(candidate), str(reference)) == 0

with zipfile.ZipFile(candidate) as z, zipfile.ZipFile(reference) as rz:
    name = next(n for n in z.namelist() if n.endswith('/definition.json'))
    doc = json.loads(z.read(name))
    for entry in z.namelist():
        if entry != name:
            assert z.read(entry) == rz.read(entry), 'Exported package identity changed'
definition = doc['properties']['definition']
sites = definition['actions']['Apply_to_each_Site']
loop = sites['actions']['Apply_to_each_Library']
assert sites['runtimeConfiguration']['concurrency']['repetitions'] == 1
assert loop['runtimeConfiguration']['concurrency']['repetitions'] == 1
assert len(re.findall('https://', sites['foreach'])) == 2
tracked = loop['actions']['If_Not_Tracked']['else']['actions']
until = tracked['Count_All_File_Pages']
assert until['operationOptions'] == 'FailWhenLimitsReached'
assert until['limit'] == {'count': 5000, 'timeout': 'PT1H'}
assert until['actions']['Files_In_Page']['inputs']['where'] == "@equals(item()?['FileSystemObjectType'], 0)"
assert tracked['Update_LibraryFilePlan_Row']['runAfter'] == {'Count_All_File_Pages': ['Succeeded']}
assert tracked['Update_LibraryFilePlan_Row']['inputs']['parameters']['dataset'] == 'https://modgovuk.sharepoint.com/teams/1598'
assert 'LibraryFileCount' in tracked['Update_LibraryFilePlan_Row']['inputs']['parameters']['parameters/body']

def actions_walk(actions):
    for action in actions.values():
        yield action
        yield from actions_walk(action.get('actions', {}))
        yield from actions_walk(action.get('else', {}).get('actions', {}))
for action in actions_walk(definition['actions']):
    kind = action['type']
    if kind == 'InitializeVariable':
        variable, = action['inputs']['variables']
        assert variable['type'] in ['integer', 'string']
        assert isinstance(variable['value'], (int, str))
    elif kind in ['SetVariable', 'IncrementVariable']:
        assert set(action['inputs']) == {'name', 'value'}
        assert "variables('" + action['inputs']['name'] + "')" not in str(action['inputs']['value'])

# Synthetic page fixtures: nested documents count, folders do not; never stop at
# the first 5,000 items; empty and folder-only libraries both have zero files.
for pages, expected in [([[]], 0), ([[{'FileSystemObjectType': 1}]], 0),
                        ([[{'FileSystemObjectType': 1}, {'FileSystemObjectType': 0}]], 1),
                        ([[{'FileSystemObjectType': 0}] * 5000, [{'FileSystemObjectType': 0}]], 5001)]:
    assert sum(sum(item['FileSystemObjectType'] == 0 for item in page) for page in pages) == expected

source = yaml.safe_load((WORK / 'scrManageLibraries.vault.yaml').read_text(encoding='utf-8'))
result = yaml.safe_load((WORK / 'scrManageLibraries.v2.9.yaml').read_text(encoding='utf-8'))
def controls(screen):
    found = {}
    def visit(children):
        for item in children:
            for name, control in item.items():
                found[name] = control
                visit(control.get('Children', []))
    visit(screen['Screens']['scrManageLibraries']['Children'])
    return found
old, new = controls(source), controls(result)
assert set(old) <= set(new)
for name in ['btnDeleteSelected', 'btnConfirmDelete', 'btnCancelOverride']:
    if name in old:
        # Appending the stats filters is the only change permitted in existing events.
        assert old[name]['Control'] == new[name]['Control']
assert old['chkSelect'] == new['chkSelect']
assert old['imgRowLimitedBadge'] == new['imgRowLimitedBadge']
assert old['btnEditSelected'] == new['btnEditSelected']
assert old['btnOpenFromHeader_1'] == new['btnOpenFromHeader_1']
highlight = new['recRowBg_1']['Properties']['Fill']
assert 'ThisItem.LibraryFileCount = 0' in highlight
assert '!IsBlank(ThisItem.LibraryFileCount)' in highlight
assert 'DateAdd(Today(), -6, TimeUnit.Months)' in highlight
assert new['lblRowHousekeeping']['Properties']['Y'] == '=74'
assert new['galManage']['Properties']['TemplateSize'] == '=100'
for name in ['txtSearch_2', 'drpTeamFilter', 'drpMgmtFileCount', 'drpMgmtAge']:
    handler = new[name]['Properties']['OnChange']
    assert 'LibraryFileCount' in handler and 'LibraryCreated' in handler
    assert 'ClearCollect(colMgmtExpandedTeams' in handler
assert 'Refresh(LibraryFilePlan)' in new['btnReloadLibraryStats']['Properties']['OnSelect']
assert len(set(new)) == len(new)
print('PASS: package identity, central routing, sequential pagination, complete-write gate, file-only fixtures, screen contracts.')
print('UNVERIFIED: real tenant import, runtime REST responses, live Power Fx and rendered layout.')
