"""Stats controls and CSV export, using only the proven SharePoint connection."""
from pathlib import Path
import copy, datetime, json, re, uuid, zipfile

ROOT = Path(__file__).resolve().parents[1]
MAIN = 'https://modgovuk.sharepoint.com/teams/1598'
BASE = ROOT / 'flows/RebuildLibraryStats_FileCounts_flow_import.zip'
WORK = Path('C:/Temp/flow-check/report-20261021')
CONTROL = "_api/web/lists/getbytitle('LibraryStatsControl')/items"
FIELDS = 'Id,Title,ScanState,StartedAt,LastSuccessAt,ScanMessage,ReportUrl'
with zipfile.ZipFile(BASE) as z:
    original = {n:z.read(n) for n in z.namelist()}
DEFNAME = next(n for n in original if n.endswith('/definition.json'))
original_doc = json.loads(original[DEFNAME])
http_base = original_doc['properties']['definition']['actions']['Apply_to_each_Site']['actions']['Get_Libraries']

def after(name, states=None):
    return {name: states or ['Succeeded']} if name else {}

def http(uri, method='GET', body=None, dependency=None, etag=None):
    a = copy.deepcopy(http_base)
    p = a['inputs']['parameters']
    p.update({'dataset': MAIN, 'parameters/method':method, 'parameters/uri':uri})
    p['parameters/headers'] = {'Accept':'application/json;odata=verbose'}
    if body is not None:
        p['parameters/body'] = json.dumps(body) if isinstance(body,dict) else body
        p['parameters/headers']['Content-Type'] = 'application/json;odata=verbose'
    if etag is not None:
        p['parameters/headers'].update({'IF-MATCH':etag,'X-HTTP-Method':'MERGE'})
    a['runAfter'] = after(dependency)
    return a

def status_get():
    return http(CONTROL+"?$filter=Title eq 'LibraryStats'&$select="+FIELDS+'&$top=2')

def status_write(values, dependency=None, lock=False):
    values = {'__metadata':{'type':"@{body('Get_Stats_Control')['d']['results'][0]['__metadata']['type']}"}, **values}
    return http(CONTROL+"(@{body('Get_Stats_Control')['d']['results'][0]['Id']})", 'POST', values, dependency,
                "@body('Get_Stats_Control')['d']['results'][0]['__metadata']['etag']" if lock else '*')

def response(started, message, url='', dependency=None, states=None):
    return {'type':'Response','kind':'PowerApp','runAfter':after(dependency,states), 'inputs':{
        'schema':{'type':'object','properties':{'started':{'type':'boolean'},'message':{'type':'string'},'reporturl':{'type':'string'}}},
        'statusCode':200,'body':{'started':started,'message':message,'reporturl':url}}}

def conditional(expression, yes, no, dependency=None):
    return {'type':'If','expression':expression,'actions':yes,'else':{'actions':no},'runAfter':after(dependency)}

def scope(actions, dependency=None):
    return {'type':'Scope','actions':actions,'runAfter':after(dependency)}

def package(doc, filename, new=False):
    files = dict(original)
    name = DEFNAME
    if new:
        guid = '0aa53889-2848-47ba-aec7-d9ae82973e47'
        oldguid = DEFNAME.split('/')[2]
        files = {n.replace('/'+oldguid+'/', '/'+guid+'/'):b for n,b in files.items()}
        name = DEFNAME.replace(oldguid,guid)
        manifest=json.loads(files['manifest.json'])
        resource=manifest['resources'].pop(oldguid)
        resource['suggestedCreationType']='New'
        resource['details']['displayName']='FP-ExportLibraryReport(App)'
        manifest['resources'][guid]=resource
        manifest['details']['displayName']='Library report export setup'
        manifest['details']['createdTime']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        files['manifest.json']=json.dumps(manifest).encode()
        fm=json.loads(files['Microsoft.Flow/flows/manifest.json'])
        fm['flowAssets']['assetPaths']=[guid]
        files['Microsoft.Flow/flows/manifest.json']=json.dumps(fm).encode()
        doc['name']=guid
        doc['id']='/providers/Microsoft.Flow/flows/'+guid
        doc['properties']['displayName']='FP-ExportLibraryReport(App)'
    files[name]=json.dumps(doc,indent=2).encode()
    out=ROOT/'flows'/filename
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in files.items():z.writestr(n,b)
    print('Built',filename)

def stats_flow():
    doc=copy.deepcopy(original_doc)
    definition=doc['properties']['definition']
    old=definition['actions']
    scan=old.pop('Apply_to_each_Site')
    scan['runAfter']={}
    work={'Apply_to_each_Site':scan,
          'Mark_Scan_Succeeded':status_write({'ScanState':'Succeeded','LastSuccessAt':'@{utcNow()}','ScanMessage':'File-count scan completed successfully.'},'Apply_to_each_Site')}
    start={
        'Acquire_Scan_Lock':status_write({'ScanState':'Running','StartedAt':'@{utcNow()}','ScanMessage':'Scanning both sites. Normally 15 minutes or longer.'},lock=True),
        'Respond_Scan_Started':response(True,'Scan started. It normally takes 15 minutes or longer. You can continue using the app.',dependency='Acquire_Scan_Lock'),
        'Scan_Work':scope(work,'Respond_Scan_Started'),
        'Mark_Scan_Failed':status_write({'ScanState':'Failed','ScanMessage':'Scan did not finish successfully. Counts may be partially refreshed; inspect flow history and rerun before exporting.'}),
        'Respond_Lock_Failed':response(False,'Could not reserve the scan. Another request may have started; reload status and check run history.',dependency='Acquire_Scan_Lock',states=['Failed','TimedOut']),
    }
    start['Mark_Scan_Failed']['runAfter']=after('Scan_Work',['Failed','TimedOut'])
    available={
        'Check_Not_Busy':conditional("@not(or(equals(body('Get_Stats_Control')['d']['results'][0]['ScanState'], 'Running'), equals(body('Get_Stats_Control')['d']['results'][0]['ScanState'], 'Exporting')))",start,{'Respond_Busy':response(False,'A scan or export is already running. Reload status; do not start another.')})
    }
    get=status_get();get['runAfter']=after('Initialize_FileCount')
    definition['actions']={**old,'Get_Stats_Control':get,'Check_Control_Row':conditional("@equals(length(body('Get_Stats_Control')['d']['results']), 1)",available,{'Respond_Setup_Required':response(False,'Create exactly one LibraryStatsControl row titled LibraryStats first.')},'Get_Stats_Control')}
    definition['description']='15-minute background scan. ETag-protected shared lock; responds to the app before scanning; completion/failure status in central LibraryStatsControl. Cancelled runs require manual status recovery after verifying the run has stopped.'
    package(doc,'RebuildLibraryStats_Status_flow_import.zip')

def export_flow():
    doc=copy.deepcopy(original_doc)
    definition=doc['properties']['definition']
    definition['triggers']['manual']['inputs']['schema']={'type':'object','properties':{},'required':[]}
    init_next={'type':'InitializeVariable','inputs':{'variables':[{'name':'reportNextPage','type':'string','value':"_api/web/lists/getbytitle('LibraryFilePlan')/items?$select=Id,Title,PrettyName,LibraryUrl,Team,SubTeam,IsLimited,LibraryCreated,LibraryFileCount&$top=5000"}]},'runAfter':{}}
    init_rows={'type':'InitializeVariable','inputs':{'variables':[{'name':'reportRows','type':'array','value':[]}]},'runAfter':after('Initialize_Report_NextPage')}
    get=status_get();get['runAfter']=after('Initialize_Report_Rows')
    page=http("@variables('reportNextPage')")
    pages={
        'Get_Report_Page':page,
        'Merge_Report_Rows':{'type':'Compose','inputs':"@union(variables('reportRows'), body('Get_Report_Page')['d']['results'])",'runAfter':after('Get_Report_Page')},
        'Store_Report_Rows':{'type':'SetVariable','inputs':{'name':'reportRows','value':"@outputs('Merge_Report_Rows')"},'runAfter':after('Merge_Report_Rows')},
        'Set_Report_NextPage':{'type':'SetVariable','inputs':{'name':'reportNextPage','value':"@if(empty(body('Get_Report_Page')?['d']?['__next']), '', concat('_api/', last(split(body('Get_Report_Page')?['d']?['__next'], '/_api/'))))"},'runAfter':after('Store_Report_Rows')},
    }
    # CSV replaces the unconfigured Excel branch. No template, script, Excel
    # connection, or tenant-specific workbook identifiers are required.
    def literal(expr):
        trimmed=f'trim(string({expr}))'
        unsafe='or('+','.join(f"startsWith({trimmed}, '{c}')" for c in ['=','+','-','@'])+')'
        return f"@if({unsafe}, concat(decodeUriComponent('%27'), string({expr})), string({expr}))"
    name="if(empty(item()?['PrettyName']), coalesce(item()?['Title'], 'Unnamed library'), item()?['PrettyName'])"
    known_count="not(equals(item()?['LibraryFileCount'], null))"
    known_date="not(empty(item()?['LibraryCreated']))"
    cutoff="convertToUtc(addToTime(startOfDay(convertTimeZone(utcNow(), 'UTC', 'GMT Standard Time')), -6, 'Month'), 'GMT Standard Time')"
    ltd="or(equals(item()?['IsLimited'], true), contains(toUpper(coalesce(item()?['LibraryUrl'], '')), '_LTD'), contains(toUpper("+name+"), '(LTD)'))"
    work={
        'Read_All_Report_Pages':{'type':'Until','expression':"@equals(variables('reportNextPage'), '')",'limit':{'count':5000,'timeout':'PT10M'},'operationOptions':'FailWhenLimitsReached','actions':pages,'runAfter':{}},
        'Report_FileName':{'type':'Compose','inputs':"@concat('LibraryReport-', formatDateTime(utcNow(),'yyyyMMdd-HHmmss'), '-', workflow()['run']['name'], '.csv')",'runAfter':after('Read_All_Report_Pages')},
        'Select_CSV_Rows':{'type':'Select','runAfter':after('Report_FileName'),'inputs':{'from':"@variables('reportRows')",'select':{
            'Library':literal(name),
            'Team':literal("if(empty(item()?['Team']), 'Uncategorised', item()?['Team'])"),
            'Sub-Team':literal("if(empty(item()?['SubTeam']), 'None', item()?['SubTeam'])"),
            'LTD':"@if("+ltd+", 'Yes', 'No')",
            'Created':"@if("+known_date+", formatDateTime(item()?['LibraryCreated'], 'yyyy-MM-dd'), 'Not checked')",
            'Files':"@if("+known_count+", string(item()?['LibraryFileCount']), 'Not checked')",
            'Empty':"@if("+known_count+", if(equals(item()?['LibraryFileCount'], 0), 'Yes', 'No'), 'Not checked')",
            'Review':"@if(and("+known_count+", "+known_date+"), if(and(equals(item()?['LibraryFileCount'], 0), lessOrEquals(ticks(if(empty(item()?['LibraryCreated']), '9999-12-31T00:00:00Z', item()?['LibraryCreated'])), ticks("+cutoff+"))), 'Empty, 6+ months old', 'No'), 'Not checked')",
            'Library link':"@concat('https://modgovuk.sharepoint.com', coalesce(item()?['LibraryUrl'], ''))",
            'Successful scan (UTC)':"@body('Get_Stats_Control')['d']['results'][0]['LastSuccessAt']",
        }}},
        'Create_CSV_Table':{'type':'Table','inputs':{'from':"@body('Select_CSV_Rows')",'format':'CSV'},'runAfter':after('Select_CSV_Rows')},
        'Save_CSV_Report':http("_api/web/GetFolderByServerRelativeUrl('/teams/1598/LibraryReports')/Files/add(url='@{outputs('Report_FileName')}',overwrite=false)",'POST',"@concat(decodeUriComponent('%EF%BB%BF'), body('Create_CSV_Table'))",'Create_CSV_Table'),
        'Release_Export_Lock':status_write({'ScanState':'Succeeded','ScanMessage':'CSV report exported from the completed scan.','ReportUrl':"@{concat('https://modgovuk.sharepoint.com/teams/1598/LibraryReports/', outputs('Report_FileName'))}"},'Save_CSV_Report'),
        'Respond_Report_Ready':response(True,'CSV report created from all tracked libraries.',"@concat('https://modgovuk.sharepoint.com/teams/1598/LibraryReports/', outputs('Report_FileName'))",'Release_Export_Lock'),
    }
    work['Create_CSV_Table']['inputs']['columns']=[{'header':key,'value':"@item()?['"+key+"']"} for key in work['Select_CSV_Rows']['inputs']['select']]
    work['Save_CSV_Report']['inputs']['parameters']['parameters/headers']['Content-Type']='text/csv; charset=utf-8'
    start={
        'Acquire_Export_Lock':status_write({'ScanState':'Exporting','ScanMessage':'Creating a CSV report from the completed scan.'},lock=True),
        'Export_Work':scope(work,'Acquire_Export_Lock'),
        'Release_Failed_Export':status_write({'ScanState':'Succeeded','ScanMessage':'CSV export failed. The completed scan is still valid; inspect the export flow history.'}),
        'Respond_Export_Error':response(False,'Report creation failed. Check the export flow history; the completed scan is still available.',dependency='Release_Failed_Export'),
        'Respond_Export_Lock_Failed':response(False,'Another scan or export may have started. Reload status and try again later.',dependency='Acquire_Export_Lock',states=['Failed','TimedOut']),
    }
    start['Release_Failed_Export']['runAfter']=after('Export_Work',['Failed','TimedOut'])
    ready="@and(equals(body('Get_Stats_Control')['d']['results'][0]['ScanState'], 'Succeeded'), not(empty(body('Get_Stats_Control')['d']['results'][0]['LastSuccessAt'])))"
    rows_ok={'Check_Export_Ready':conditional(ready,start,{'Respond_Not_Ready':response(False,'Export requires a completed successful scan. Reload status.')})}
    definition['actions']={'Initialize_Report_NextPage':init_next,'Initialize_Report_Rows':init_rows,'Get_Stats_Control':get,'Check_Control_Row':conditional("@equals(length(body('Get_Stats_Control')['d']['results']), 1)",rows_ok,{'Respond_Export_Control_Missing':response(False,'Create exactly one LibraryStatsControl row titled LibraryStats first.')},'Get_Stats_Control')}
    definition['description']='CSV report using only SharePoint. Exports all tracked libraries under an ETag lock after a successful scan. UTF-8 BOM, quoted CSV fields, missing counts preserved and formula-like text escaped. No Excel/Office Scripts/template dependency.'
    package(doc,'ExportLibraryReport_CSV_flow_import.zip',new=True)

if __name__=='__main__':
    stats_flow();export_flow()
