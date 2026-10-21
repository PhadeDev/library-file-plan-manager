"""Local contracts; not tenant import/execution verification."""
from pathlib import Path
import importlib.util,json,re,zipfile,yaml

ROOT=Path(__file__).resolve().parents[1]
WORK=Path('C:/Temp/flow-check/report-20261021')
spec=importlib.util.spec_from_file_location('previous',ROOT/'tools/check_housekeeping.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
reference=ROOT/'flows/RebuildLibraryStats_FileCounts_flow_import.zip'

def walk(actions):
    for name,action in actions.items():
        yield name,action
        yield from walk(action.get('actions',{}))
        yield from walk(action.get('else',{}).get('actions',{}))

def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for child in value.values():yield from strings(child)
    elif isinstance(value,list):
        for child in value:yield from strings(child)

def balanced(expression):
    depth=0;quoted=False;i=0
    while i<len(expression):
        c=expression[i]
        if c=="'":
            if quoted and i+1<len(expression) and expression[i+1]=="'":i+=2;continue
            quoted=not quoted
        elif not quoted:
            if c=='(':depth+=1
            if c==')':
                depth-=1
                assert depth>=0,expression
        i+=1
    assert depth==0 and not quoted,expression

docs=[]
for filename in ['RebuildLibraryStats_Status_flow_import.zip','ExportLibraryReport_CSV_flow_import.zip']:
    candidate=ROOT/'flows'/filename
    assert previous.checker.main(str(candidate),str(reference))==0
    with zipfile.ZipFile(candidate) as z:
        name=next(n for n in z.namelist() if n.endswith('/definition.json'))
        doc=json.loads(z.read(name))
        manifest=json.loads(z.read('manifest.json'))
        assert name.split('/')[2] in manifest['resources']
    docs.append(doc)
    actions=dict(walk(doc['properties']['definition']['actions']))
    schemas=[]
    for name,action in actions.items():
        for value in strings(action):
            for expr in re.findall(r'@\{([^{}]+)\}',value):balanced(expr)
            if value.startswith('@') and not value.startswith('@{'):balanced(value[1:])
            for ref in re.findall(r"(?:body|outputs|items)\('([^']+)'\)",value):assert ref in actions,ref
        if action['type']=='Response':schemas.append(action['inputs']['schema'])
        if action['type']=='SetVariable':
            assert "variables('"+action['inputs']['name']+"')" not in str(action['inputs']['value'])
    assert all(s==schemas[0] for s in schemas)
    locks=[a for n,a in actions.items() if n in ['Acquire_Scan_Lock','Acquire_Export_Lock']]
    assert len(locks)==1
    assert "['etag']" in locks[0]['inputs']['parameters']['parameters/headers']['IF-MATCH']
    writes=[a for a in actions.values() if a['type']=='OpenApiConnection' and a['inputs']['parameters']['parameters/method']=='POST']
    assert all(a['inputs']['parameters']['dataset']=='https://modgovuk.sharepoint.com/teams/1598' for a in writes)

scan=dict(walk(docs[0]['properties']['definition']['actions']))
assert scan['Scan_Work']['runAfter']=={'Respond_Scan_Started':['Succeeded']}
assert scan['Respond_Scan_Started']['runAfter']=={'Acquire_Scan_Lock':['Succeeded']}
assert scan['Mark_Scan_Failed']['runAfter']=={'Scan_Work':['Failed','TimedOut']}
export=dict(walk(docs[1]['properties']['definition']['actions']))
assert export['Create_CSV_Table']['type']=='Table'
assert export['Create_CSV_Table']['inputs']['format']=='CSV'
assert len(export['Create_CSV_Table']['inputs']['columns'])==10
assert 'LastSuccessAt' in export['Check_Export_Ready']['expression']
assert 'Excel' not in str(export)
assert export['Save_CSV_Report']['inputs']['parameters']['parameters/headers']['Content-Type']=='text/csv; charset=utf-8'
assert export['Release_Export_Lock']['runAfter']=={'Save_CSV_Report':['Succeeded']}

base=yaml.safe_load((ROOT/'docs/downloads/scrManageLibraries-v2.9.yaml').read_text(encoding='utf-8'))
new=yaml.safe_load((WORK/'scrManageLibraries.v3.0.yaml').read_text(encoding='utf-8'))
old_controls=previous.controls(base);new_controls=previous.controls(new)
assert set(old_controls)<=set(new_controls)
for name in old_controls:
    if name not in ['btnReloadLibraryStats']:
        assert old_controls[name]==new_controls[name] or name=='galManage',(name,'existing control altered')
assert old_controls['galManage']['Properties']==new_controls['galManage']['Properties']
assert 'ScanState <> "Succeeded"' in new_controls['btnExportLibraryReport']['Properties']['DisplayMode']
assert new_controls['tmrLibraryStatsStatus']['Properties']['Duration']=='=30000'
top=new['Screens']['scrManageLibraries']['Children']
names=[next(iter(c)) for c in top]
assert names.index('btnExportLibraryReport')<names.index('recOverlayBg_1')
assert names.index('recStatsWarningShade')>names.index('btnConfirmOverride') if 'btnConfirmOverride' in names else True
for name in ['recStatsWarningShade','recStatsWarningPanel','lblStatsWarningTitle','lblStatsWarningText','btnCancelStatsScan','btnConfirmStatsScan']:
    assert new_controls[name]['Properties']['Visible']=='=varIsAdmin && varShowStatsWarning'
print('PASS: flow package structures, expressions/references, atomic locks, early response, failure guards, CSV-only export and screen preservation/overlays.')
print('UNVERIFIED: tenant import, live flow execution and Studio appearance.')
