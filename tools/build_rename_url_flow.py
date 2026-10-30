import json, sys, uuid, zipfile

OUT = sys.argv[1]
FLOW_ID, RES_ID, API_ID, CONN_ID = (str(uuid.uuid4()) for _ in range(4))
NAME = "FP-RenameLibraryUrl(App)"
DESC = "Changes the URL of one tracked library by moving its root folder, then updates its LibraryFilePlan row. Dry run unless Confirm is exactly RENAME."
ICON = "https://static.powerapps.com/resource/ppcr/releases/v1.0.1827/1.0.1827.4913/sharepointonline/icon.png"
MAIN = "https://modgovuk.sharepoint.com/teams/1598"
CCF = "https://modgovuk.sharepoint.com/teams/1598/CCF"
AUTH = {"value": "@json(decodeBase64(triggerOutputs().headers['X-MS-APIM-Tokens']))['$ConnectionKey']", "type": "Raw"}
HOST = {"apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline", "connectionName": "shared_sharepointonline", "operationId": "HttpRequest"}

OLD = "triggerBody()?['LibraryUrl']"
NEW = "triggerBody()?['NewUrlName']"

manifest = {
    "schema": "1.0",
    "details": {"displayName": NAME, "description": DESC, "createdTime": "2026-10-30T10:00:00.0000000Z",
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
    "LibraryUrl": {"type": "string", "title": "Current library URL, server-relative (e.g. /teams/1598/Old_Name)", "x-ms-content-hint": "TEXT"},
    "NewUrlName": {"type": "string", "title": "New URL name, one word with no spaces (e.g. New_Name)", "x-ms-content-hint": "TEXT"},
    "Confirm": {"type": "string", "title": "Type RENAME to really rename, anything else is a dry run", "x-ms-content-hint": "TEXT"},
}, "required": ["LibraryUrl", "NewUrlName"]}}}}

forbidden = ["'/'", "decodeUriComponent('%5C')", "' '", "'#'", "'%'", "'?'", "':'", "'*'", "decodeUriComponent('%22')", "'<'", "'>'", "'|'", "'~'",
             "'&'", "'{'", "'}'", "decodeUriComponent('%27')", "'+'", "','", "';'", "'='", "'['", "']'", "'^'", "'..'"]
checks = [
    f"not(empty(trim({NEW})))",
    f"equals(trim({NEW}), {NEW})",
    f"lessOrEquals(length({NEW}), 100)",
    f"not(startsWith({NEW}, '.'))",
    f"not(endsWith({NEW}, '.'))",
    f"not(contains(createArray('forms','lists','_catalogs','_layouts','_api','sitepages'), toLower({NEW})))",
    f"startsWith(toLower({OLD}), '/teams/1598/')",
] + [f"not(contains({NEW}, {c}))" for c in forbidden] + [f"not(contains({OLD}, '..'))"]
safe_expr = "@and(" + ", ".join(checks) + ")"

site_expr = f"@if(startsWith(toLower({OLD}), '/teams/1598/ccf/'), '{CCF}', '{MAIN}')"
new_url_expr = f"@concat(substring({OLD}, 0, lastIndexOf({OLD}, '/')), '/', {NEW})"
esc_old = f"replace({OLD}, decodeUriComponent('%27'), decodeUriComponent('%27%27'))"

def resp(rn, ok, dry, msg, run_after):
    return {"runAfter": run_after, "type": "Response", "kind": "PowerApp", "inputs": {
        "schema": {"type": "object", "properties": {"Success": {"type": "boolean"}, "DryRun": {"type": "boolean"},
                   "OldUrl": {"type": "string"}, "NewUrl": {"type": "string"}, "Message": {"type": "string"}}},
        "statusCode": 200,
        "body": {"Success": ok, "DryRun": dry, "OldUrl": f"@{{{OLD}}}", "NewUrl": "@{outputs('New_Url')}", "Message": msg}}}

why_not = ("@{if(not(outputs('Name_Is_Safe')), 'Not changed: the new URL name is empty, too long, uses a reserved word, or contains a character that is not allowed (spaces, slashes, # % ? : * quotes and similar). Use letters, numbers, hyphens and underscores only.', "
           "if(equals(length(body('Get_Tracked_Row')?['d']?['results']), 0), 'Not changed: that library is not tracked in LibraryFilePlan. Run Backfill File Plan first.', "
           f"'Not changed: the new name is the same as the current URL name.'))}}")

actions = {
    "Name_Is_Safe": {"runAfter": {}, "type": "Compose", "inputs": safe_expr},
    "New_Url": {"runAfter": {"Name_Is_Safe": ["Succeeded"]}, "type": "Compose", "inputs": new_url_expr},
    "Site_Url": {"runAfter": {"New_Url": ["Succeeded"]}, "type": "Compose", "inputs": site_expr},
    "Get_Tracked_Row": {"runAfter": {"Site_Url": ["Succeeded"]}, "type": "OpenApiConnection", "inputs": {"parameters": {
        "dataset": MAIN, "parameters/method": "GET",
        "parameters/uri": "_api/web/lists/getbytitle('LibraryFilePlan')/items?$filter=LibraryUrl eq '@{encodeUriComponent(" + esc_old + ")}'&$select=Id&$top=1",
        "parameters/headers": {"Accept": "application/json;odata=verbose"}}, "host": HOST, "authentication": AUTH}},
    "If_Allowed": {"runAfter": {"Get_Tracked_Row": ["Succeeded"]}, "type": "If",
        "expression": {"and": [
            {"equals": ["@outputs('Name_Is_Safe')", True]},
            {"greater": ["@length(body('Get_Tracked_Row')?['d']?['results'])", 0]},
            {"not": {"equals": [f"@toLower({OLD})", "@toLower(outputs('New_Url'))"]}}]},
        "actions": {"If_Confirmed": {"runAfter": {}, "type": "If",
            "expression": {"equals": ["@triggerBody()?['Confirm']", "RENAME"]},
            "actions": {
                "Rename_Library_Folder": {"runAfter": {}, "type": "OpenApiConnection", "inputs": {"parameters": {
                    "dataset": "@outputs('Site_Url')", "parameters/method": "POST",
                    "parameters/uri": "_api/web/GetFolderByServerRelativeUrl('@{" + esc_old + "}')/MoveTo(newUrl='@{outputs('New_Url')}')",
                    "parameters/headers": {"Accept": "application/json;odata=verbose"}}, "host": HOST, "authentication": AUTH}},
                "Update_Tracked_Row": {"runAfter": {"Rename_Library_Folder": ["Succeeded"]}, "type": "OpenApiConnection", "inputs": {"parameters": {
                    "dataset": MAIN, "parameters/method": "POST",
                    "parameters/uri": "_api/web/lists/getbytitle('LibraryFilePlan')/items(@{body('Get_Tracked_Row')?['d']?['results'][0]?['Id']})",
                    "parameters/headers": {"Accept": "application/json;odata=verbose", "Content-Type": "application/json;odata=verbose", "IF-MATCH": "*", "X-HTTP-Method": "MERGE"},
                    "parameters/body": "{\"__metadata\":{\"type\":\"SP.Data.LibraryFilePlanListItem\"},\"LibraryUrl\":\"@{outputs('New_Url')}\"}"},
                    "host": HOST, "authentication": AUTH}},
                "Response_Renamed": resp("Response_Renamed", True, False,
                    "Renamed. The old address no longer works. Run Refresh Index on Group Search so the permission index picks up the new URL.",
                    {"Update_Tracked_Row": ["Succeeded"]}),
            },
            "else": {"actions": {"Response_Dry_Run": resp("Response_Dry_Run", True, True,
                "Dry run only, nothing changed. Would rename to the NewUrl shown. Send Confirm = RENAME to do it for real.", {})}}}},
        "else": {"actions": {"Response_Not_Allowed": resp("Response_Not_Allowed", False, False, why_not, {})}}},
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
