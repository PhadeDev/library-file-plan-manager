import json, sys, uuid, zipfile

OUT = sys.argv[1]
FLOW_ID, RES_ID, API_ID, CONN_ID = (str(uuid.uuid4()) for _ in range(4))
NAME = "FP-RenameLibrary(App)"
DESC = "Changes the web address (URL) of one document library by moving its root folder, then keeps LibraryFilePlan and PermissionIndex in step. Does nothing but check unless Confirm is RENAME."
ICON = "https://static.powerapps.com/resource/ppcr/releases/v1.0.1827/1.0.1827.4913/sharepointonline/icon.png"
MAIN = "https://modgovuk.sharepoint.com/teams/1598"
CCF = "https://modgovuk.sharepoint.com/teams/1598/CCF"
AUTH = {"value": "@json(decodeBase64(triggerOutputs().headers['X-MS-APIM-Tokens']))['$ConnectionKey']", "type": "Raw"}
HOST = {"apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline", "connectionName": "shared_sharepointonline", "operationId": "HttpRequest"}

def o(n):
    return f"outputs('{n}')"

LIB, NEWN, NEWU = o("Lib_Url"), o("New_Name"), o("New_Url")
esc_old = f"replace({LIB}, decodeUriComponent('%27'), decodeUriComponent('%27%27'))"

manifest = {
    "schema": "1.0",
    "details": {"displayName": NAME, "description": DESC, "createdTime": "2026-11-09T10:00:00.0000000Z",
                "packageTelemetryId": "00000000-0000-0000-0000-000000000000", "creator": "N/A", "sourceEnvironment": ""},
    "resources": {
        RES_ID: {"type": "Microsoft.Flow/flows", "suggestedCreationType": "New", "creationType": "New, Update",
                 "details": {"displayName": NAME}, "configurableBy": "User", "hierarchy": "Root", "dependsOn": [API_ID, CONN_ID]},
        API_ID: {"id": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline", "name": "shared_sharepointonline",
                 "type": "Microsoft.PowerApps/apis", "suggestedCreationType": "Existing",
                 "details": {"displayName": "SharePoint", "iconUri": ICON}, "configurableBy": "System", "hierarchy": "Child", "dependsOn": []},
        CONN_ID: {"type": "Microsoft.PowerApps/apis/connections", "suggestedCreationType": "Existing", "creationType": "Existing",
                  "details": {"displayName": "Your SharePoint connection", "iconUri": ICON}, "configurableBy": "User", "hierarchy": "Child", "dependsOn": [API_ID]},
    },
}

trigger = {"manual": {"type": "Request", "kind": "PowerAppV2", "inputs": {"schema": {"type": "object", "properties": {
    "LibraryUrl": {"type": "string", "title": "Library to change: its address, e.g. /teams/1598/Old_Name", "x-ms-content-hint": "TEXT"},
    "NewUrlName": {"type": "string", "title": "New last part of the address only, e.g. New_Name", "x-ms-content-hint": "TEXT"},
    "Confirm": {"type": "string", "title": "Type RENAME to really change it. Anything else only checks.", "x-ms-content-hint": "TEXT"},
}, "required": ["LibraryUrl", "NewUrlName"]}}}}

forbidden = ["'/'", "decodeUriComponent('%5C')", "' '", "'#'", "'%'", "'?'", "':'", "'*'", "decodeUriComponent('%22')", "'<'", "'>'", "'|'", "'~'",
             "'&'", "'{'", "'}'", "decodeUriComponent('%27')", "'+'", "','", "';'", "'='", "'['", "']'", "'^'", "'..'"]
safe_checks = [
    f"not(empty({NEWN}))", f"lessOrEquals(length({NEWN}), 100)", f"not(startsWith({NEWN}, '.'))", f"not(endsWith({NEWN}, '.'))",
    f"not(contains(createArray('forms','lists','_catalogs','_layouts','_api','sitepages','siteassets','ccf'), toLower({NEWN})))",
] + [f"not(contains({NEWN}, {c}))" for c in forbidden]

def resp(ok, dry, msg, run_after):
    return {"runAfter": run_after, "type": "Response", "kind": "PowerApp", "inputs": {
        "schema": {"type": "object", "properties": {"Success": {"type": "boolean"}, "DryRun": {"type": "boolean"},
                   "OldUrl": {"type": "string"}, "NewUrl": {"type": "string"}, "Message": {"type": "string"}}},
        "statusCode": 200,
        "body": {"Success": ok, "DryRun": dry, "OldUrl": f"@{{{LIB}}}", "NewUrl": f"@{{{NEWU}}}", "Message": msg}}}

not_allowed_msg = ("@{if(not(" + o("Path_Is_Valid") + "), 'Not changed: that is not a library address this can change. It must be a library directly under /teams/1598/ or /teams/1598/CCF/, for example /teams/1598/My_Library.', "
    "if(not(" + o("Name_Is_Safe") + "), 'Not changed: the new name is empty, too long, a reserved word, or contains a character that is not allowed (spaces, slashes, # % ? : * quotes and similar). Use letters, numbers, hyphens and underscores only.', "
    "'Not changed: the new name is the same as the current one.'))}")

dry_msg = ("@{concat('Check passed, nothing changed. This would change the address from ', " + LIB + ", ' to ', " + NEWU + ", '.', "
    "if(greater(length(body('Get_Tracked_Row')?['d']?['results']), 0), ' It is tracked in the file plan, so that record will be updated too.', ' It is not tracked in the file plan, so only the address changes.'))}")

def http(method, uri, dataset, headers, body=None):
    p = {"dataset": dataset, "parameters/method": method, "parameters/uri": uri, "parameters/headers": headers}
    if body is not None:
        p["parameters/body"] = body
    return {"type": "OpenApiConnection", "inputs": {"parameters": p, "host": HOST, "authentication": AUTH}}

JSON_H = {"Accept": "application/json;odata=verbose", "Content-Type": "application/json;odata=verbose", "IF-MATCH": "*", "X-HTTP-Method": "MERGE"}

rename_branch = {
    "Rename_Library_Folder": {"runAfter": {}, **http("POST",
        "_api/web/GetFolderByServerRelativeUrl('@{" + esc_old + "}')/MoveTo(newUrl='@{" + NEWU + "}')", "@" + o("Site_Url"),
        {"Accept": "application/json;odata=verbose"})},
    "Get_Index_Rows": {"runAfter": {"Rename_Library_Folder": ["Succeeded"]}, **http("GET",
        "_api/web/lists/getbytitle('PermissionIndex')/items?$filter=LibraryUrl eq '@{encodeUriComponent(" + esc_old + ")}'&$select=Id&$top=5000", MAIN,
        {"Accept": "application/json;odata=verbose"})},
    "Select_Index_Ids": {"runAfter": {"Get_Index_Rows": ["Succeeded"]}, "type": "Select",
        "inputs": {"from": "@body('Get_Index_Rows')?['d']?['results']", "select": "@item()?['Id']"}},
    "Apply_to_each_Index_Row": {"runAfter": {"Select_Index_Ids": ["Succeeded"]}, "type": "Foreach", "foreach": "@body('Select_Index_Ids')",
        "runtimeConfiguration": {"concurrency": {"repetitions": 20}},
        "actions": {"Update_Index_Row": {"runAfter": {}, **http("POST",
            "_api/web/lists/getbytitle('PermissionIndex')/items(@{items('Apply_to_each_Index_Row')})", MAIN, JSON_H,
            "{\"__metadata\":{\"type\":\"SP.Data.PermissionIndexListItem\"},\"LibraryUrl\":\"@{" + NEWU + "}\"}")}}},
    "If_Tracked": {"runAfter": {"Apply_to_each_Index_Row": ["Succeeded"]}, "type": "If",
        "expression": {"greater": ["@length(body('Get_Tracked_Row')?['d']?['results'])", 0]},
        "actions": {"Update_Tracked_Row": {"runAfter": {}, **http("POST",
            "_api/web/lists/getbytitle('LibraryFilePlan')/items(@{body('Get_Tracked_Row')?['d']?['results'][0]?['Id']})", MAIN, JSON_H,
            "{\"__metadata\":{\"type\":\"SP.Data.LibraryFilePlanListItem\"},\"LibraryUrl\":\"@{" + NEWU + "}\"}")}},
        "else": {"actions": {}}},
    "Response_Renamed": resp(True, False, "@{concat('Done. The address is now ', " + NEWU + ", '. Old links to the previous address no longer work.')}",
                             {"If_Tracked": ["Succeeded"]}),
}

actions = {
    "Lib_Url_A": {"runAfter": {}, "type": "Compose", "inputs": "@trim(replace(trim(coalesce(triggerBody()?['LibraryUrl'], '')), 'https://modgovuk.sharepoint.com', ''))"},
    "Lib_Url_B": {"runAfter": {"Lib_Url_A": ["Succeeded"]}, "type": "Compose",
        "inputs": "@if(contains(outputs('Lib_Url_A'), '/'), outputs('Lib_Url_A'), concat('/teams/1598/', outputs('Lib_Url_A')))"},
    "Lib_Url": {"runAfter": {"Lib_Url_B": ["Succeeded"]}, "type": "Compose",
        "inputs": "@if(and(greater(length(outputs('Lib_Url_B')), 1), endsWith(outputs('Lib_Url_B'), '/')), substring(outputs('Lib_Url_B'), 0, sub(length(outputs('Lib_Url_B')), 1)), outputs('Lib_Url_B'))"},
    "New_Name": {"runAfter": {"Lib_Url": ["Succeeded"]}, "type": "Compose", "inputs": "@trim(coalesce(triggerBody()?['NewUrlName'], ''))"},
    "Name_Is_Safe": {"runAfter": {"New_Name": ["Succeeded"]}, "type": "Compose", "inputs": "@and(" + ", ".join(safe_checks) + ")"},
    "Site_Prefix": {"runAfter": {"Name_Is_Safe": ["Succeeded"]}, "type": "Compose",
        "inputs": f"@if(startsWith(toLower({LIB}), '/teams/1598/ccf/'), '/teams/1598/CCF/', '/teams/1598/')"},
    "Current_Segment": {"runAfter": {"Site_Prefix": ["Succeeded"]}, "type": "Compose",
        "inputs": f"@if(startsWith(toLower({LIB}), toLower({o('Site_Prefix')})), substring({LIB}, length({o('Site_Prefix')})), '')"},
    "Path_Is_Valid": {"runAfter": {"Current_Segment": ["Succeeded"]}, "type": "Compose",
        "inputs": f"@and(not(empty({o('Current_Segment')})), not(contains({o('Current_Segment')}, '/')), not(contains({LIB}, '..')), "
                  f"not(contains(createArray('lists','sitepages','siteassets','_catalogs','_layouts','_api','forms','ccf'), toLower({o('Current_Segment')}))))"},
    "New_Url": {"runAfter": {"Path_Is_Valid": ["Succeeded"]}, "type": "Compose",
        "inputs": f"@if(greater(lastIndexOf({LIB}, '/'), 0), concat(substring({LIB}, 0, lastIndexOf({LIB}, '/')), '/', {NEWN}), {LIB})"},
    "Site_Url": {"runAfter": {"New_Url": ["Succeeded"]}, "type": "Compose",
        "inputs": f"@if(startsWith(toLower({LIB}), '/teams/1598/ccf/'), '{CCF}', '{MAIN}')"},
    "Get_Tracked_Row": {"runAfter": {"Site_Url": ["Succeeded"]}, **http("GET",
        "_api/web/lists/getbytitle('LibraryFilePlan')/items?$filter=LibraryUrl eq '@{encodeUriComponent(" + esc_old + ")}'&$select=Id&$top=1", MAIN,
        {"Accept": "application/json;odata=verbose"})},
    "If_Allowed": {"runAfter": {"Get_Tracked_Row": ["Succeeded"]}, "type": "If",
        "expression": {"and": [
            {"equals": ["@" + o("Name_Is_Safe"), True]},
            {"equals": ["@" + o("Path_Is_Valid"), True]},
            {"not": {"equals": [f"@toLower({LIB})", f"@toLower({NEWU})"]}}]},
        "actions": {"If_Confirmed": {"runAfter": {}, "type": "If",
            "expression": {"equals": ["@toUpper(coalesce(triggerBody()?['Confirm'], ''))", "RENAME"]},
            "actions": rename_branch,
            "else": {"actions": {"Response_Dry_Run": resp(True, True, dry_msg, {})}}}},
        "else": {"actions": {"Response_Not_Allowed": resp(False, False, not_allowed_msg, {})}}},
}

definition = {"name": FLOW_ID, "id": "/providers/Microsoft.Flow/flows/" + FLOW_ID, "type": "Microsoft.Flow/flows",
    "properties": {"apiId": "/providers/Microsoft.PowerApps/apis/shared_logicflows", "displayName": NAME,
        "connectionReferences": {"shared_sharepointonline": {"connectionName": "a3a09ec6fc274de596228408c04aa18d", "source": "Invoker",
            "id": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline", "tier": "NotSpecified", "apiName": "sharepointonline",
            "isProcessSimpleApiReferenceConversionAlreadyDone": False}},
        "definition": {"$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {"$authentication": {"defaultValue": {}, "type": "SecureObject"}, "$connections": {"defaultValue": {}, "type": "Object"}},
            "triggers": trigger, "actions": actions},
        "flowFailureAlertSubscribed": False, "isManaged": False}}

base = "Microsoft.Flow/flows/" + RES_ID + "/"
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("manifest.json", json.dumps(manifest))
    z.writestr("Microsoft.Flow/flows/manifest.json", json.dumps({"packageSchemaVersion": "1.0", "flowAssets": {"assetPaths": [RES_ID]}}))
    z.writestr(base + "apisMap.json", json.dumps({"shared_sharepointonline": API_ID}))
    z.writestr(base + "connectionsMap.json", json.dumps({"shared_sharepointonline": CONN_ID}))
    z.writestr(base + "definition.json", json.dumps(definition))
print("wrote", OUT, "flow", RES_ID)
