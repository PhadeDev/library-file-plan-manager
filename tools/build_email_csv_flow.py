import io, json, sys, uuid, zipfile

OUT = sys.argv[1]
FLOW_ID = str(uuid.uuid4())
RES_ID = str(uuid.uuid4())
API_ID = str(uuid.uuid4())
CONN_ID = str(uuid.uuid4())
NAME = "FP-EmailLibraryCsv(App)"
DESC = "Emails the CSV text sent from Manage Libraries to the person who pressed the button, as an attached .csv file. Uses only the invoker's own Office 365 Outlook connection. Nothing is stored anywhere."
ICON = "https://static.powerapps.com/resource/ppcr/releases/v1.0.1813/1.0.1813.4769/office365/icon.png"

manifest = {
    "schema": "1.0",
    "details": {"displayName": NAME, "description": DESC, "createdTime": "2026-10-21T10:00:00.0000000Z",
                "packageTelemetryId": "00000000-0000-0000-0000-000000000000", "creator": "N/A", "sourceEnvironment": ""},
    "resources": {
        RES_ID: {"type": "Microsoft.Flow/flows", "suggestedCreationType": "New", "creationType": "New, Update",
                 "details": {"displayName": NAME}, "configurableBy": "User", "hierarchy": "Root",
                 "dependsOn": [API_ID, CONN_ID]},
        API_ID: {"id": "/providers/Microsoft.PowerApps/apis/shared_office365", "name": "shared_office365",
                 "type": "Microsoft.PowerApps/apis", "suggestedCreationType": "Existing",
                 "details": {"displayName": "Office 365 Outlook", "iconUri": ICON},
                 "configurableBy": "System", "hierarchy": "Child", "dependsOn": []},
        CONN_ID: {"type": "Microsoft.PowerApps/apis/connections", "suggestedCreationType": "Existing", "creationType": "Existing",
                  "details": {"displayName": "Your Office 365 Outlook connection", "iconUri": ICON},
                  "configurableBy": "User", "hierarchy": "Child", "dependsOn": [API_ID]},
    },
}

trigger = {
    "manual": {
        "type": "Request", "kind": "PowerAppV2",
        "inputs": {"schema": {"type": "object", "properties": {
            "CsvText": {"type": "string", "title": "CSV text", "x-ms-content-hint": "TEXT"},
            "Recipient": {"type": "string", "title": "Email address to send to", "x-ms-content-hint": "TEXT"},
            "Summary": {"type": "string", "title": "One-line summary for the email body", "x-ms-content-hint": "TEXT"},
        }, "required": ["CsvText", "Recipient"]}},
    }
}

body_html = "<p>Library report attached as a CSV file.</p><p>@{coalesce(triggerBody()?['Summary'], '')}</p><p>Counts come from the last saved stats scan. This email was sent from the Library &amp; File Plan Manager app.</p>"
stamp = "@{formatDateTime(convertTimeZone(utcNow(), 'UTC', 'GMT Standard Time'), 'yyyyMMdd_HHmm')}"
actions = {
    "Send_Library_Report_Email": {
        "runAfter": {},
        "type": "OpenApiConnection",
        "inputs": {
            "parameters": {
                "emailMessage/To": "@triggerBody()?['Recipient']",
                "emailMessage/Subject": "Library report " + "@{formatDateTime(convertTimeZone(utcNow(), 'UTC', 'GMT Standard Time'), 'dd/MM/yyyy HH:mm')}",
                "emailMessage/Body": body_html,
                "emailMessage/Attachments": [{
                    "Name": "LibraryReport_" + stamp + ".csv",
                    "ContentBytes": "@base64ToBinary(base64(concat(uriComponentToString('%EF%BB%BF'), triggerBody()?['CsvText'])))",
                }],
                "emailMessage/Importance": "Normal",
            },
            "host": {"apiId": "/providers/Microsoft.PowerApps/apis/shared_office365",
                     "connectionName": "shared_office365", "operationId": "SendEmailV2"},
            "authentication": {"value": "@json(decodeBase64(triggerOutputs().headers['X-MS-APIM-Tokens']))['$ConnectionKey']", "type": "Raw"},
        },
    },
    "Response": {
        "runAfter": {"Send_Library_Report_Email": ["Succeeded"]},
        "type": "Response", "kind": "PowerApp",
        "inputs": {
            "schema": {"type": "object", "properties": {"Success": {"type": "boolean"}, "SentTo": {"type": "string"}}},
            "statusCode": 200,
            "body": {"Success": True, "SentTo": "@{triggerBody()?['Recipient']}"},
        },
    },
}

definition = {
    "name": FLOW_ID,
    "id": "/providers/Microsoft.Flow/flows/" + FLOW_ID,
    "type": "Microsoft.Flow/flows",
    "properties": {
        "apiId": "/providers/Microsoft.PowerApps/apis/shared_logicflows",
        "displayName": NAME,
        "connectionReferences": {"shared_office365": {
            "connectionName": "a3a09ec6fc274de596228408c04aa18d", "source": "Invoker",
            "id": "/providers/Microsoft.PowerApps/apis/shared_office365", "tier": "NotSpecified",
            "apiName": "office365", "isProcessSimpleApiReferenceConversionAlreadyDone": False}},
        "definition": {
            "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {"$authentication": {"defaultValue": {}, "type": "SecureObject"}, "$connections": {"defaultValue": {}, "type": "Object"}},
            "triggers": trigger, "actions": actions,
        },
        "flowFailureAlertSubscribed": False, "isManaged": False,
    },
}

base = "Microsoft.Flow/flows/" + RES_ID + "/"
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("manifest.json", json.dumps(manifest))
    z.writestr("Microsoft.Flow/flows/manifest.json", json.dumps({"packageSchemaVersion": "1.0", "flowAssets": {"assetPaths": [RES_ID]}}))
    z.writestr(base + "apisMap.json", json.dumps({"shared_office365": API_ID}))
    z.writestr(base + "connectionsMap.json", json.dumps({"shared_office365": CONN_ID}))
    z.writestr(base + "definition.json", json.dumps(definition))
print("wrote", OUT, "flow", RES_ID)
