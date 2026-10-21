from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
WORK=Path('C:/Temp/flow-check/report-20261021')
text=(ROOT/'docs/downloads/scrManageLibraries-v2.9.yaml').read_text(encoding='utf-8')
status='''Set(varStatsStatusError, false);
IfError(
    Refresh(LibraryStatsControl);
    Set(varStatsControl, LookUp(LibraryStatsControl, Title = "LibraryStats")),
    Set(varStatsStatusError, true)
)'''

def event(formula, indent=14):
    return '\n'.join(' '*indent+line for line in ('='+formula).splitlines())+'\n'

def button(name, label, x, width, action, mode='=DisplayMode.Edit'):
    return f'''      - {name}:
          Control: ModernButton@1.0.0
          Properties:
            DisplayMode: {mode}
            Height: =36
            OnSelect: |-
{event(action)}            Text: ="{label}"
            Visible: =varIsAdmin
            Width: ={width}
            X: ={x}
            Y: =218
'''

onvisible=''';
        Set(varShowStatsWarning, false);
        Set(varRequestStatsBusy, false);
        Set(varExportReportBusy, false);
'''+ '\n'.join('        '+line for line in status.splitlines())+'\n'
text=text.replace('        Set(varDeleteStatus, "")\n    Children:', '        Set(varDeleteStatus, "")'+onvisible+'    Children:',1)
assert 'Set(varShowStatsWarning' in text
text=text.replace('Text: =CountRows(colSelectedLibraries) & " selected"','Text: =CountRows(colSelectedLibraries) & " selected"',1)
# Add status refresh to the existing saved-data reload event, not a new OnStart.
marker='              Notify("Latest saved stats loaded.'
pos=text.index(marker)
text=text[:pos]+'\n'.join('              '+line for line in status.splitlines())+';\n'+text[pos:]
busy='varStatsStatusError || IsBlank(varStatsControl.Id) || varRequestStatsBusy || varExportReportBusy || varStatsControl.ScanState in ["Running", "Exporting"]'
controls=button('btnRequestLibraryStats','Rebuild library stats',684,200,'Set(varShowStatsWarning, true)',f'=If({busy}, DisplayMode.Disabled, DisplayMode.Edit)')
export='''Set(varExportReportBusy, true);
Set(varExportReportError, false);
IfError(
    Set(varLibraryReportResponse, 'FP-ExportLibraryReport(App)'.Run()),
    Set(varExportReportError, true)
);
Set(varExportReportBusy, false);
If(
    varExportReportError,
    Notify("Report request failed or timed out. Reload status and check Last report before trying again.", NotificationType.Error),
    If(
        varLibraryReportResponse.started && !IsBlank(varLibraryReportResponse.reporturl),
        Notify(varLibraryReportResponse.message, NotificationType.Success);
        Launch(varLibraryReportResponse.reporturl),
        Notify(varLibraryReportResponse.message, NotificationType.Warning)
    )
);
'''+status
controls+=button('btnExportLibraryReport','Export CSV report',900,210,export,f'=If({busy} || varStatsControl.ScanState <> "Succeeded" || IsBlank(varStatsControl.LastSuccessAt), DisplayMode.Disabled, DisplayMode.Edit)')
controls+=button('btnOpenLastLibraryReport','Last report',1126,180,'Launch(varStatsControl.ReportUrl)','=If(varStatsStatusError || IsBlank(varStatsControl.ReportUrl), DisplayMode.Disabled, DisplayMode.Edit)')
controls+='''      - lblSharedStatsStatus:
          Control: Label@2.5.1
          Properties:
            Color: =If(varStatsStatusError || varStatsControl.ScanState = "Failed", RGBA(170, 40, 40, 1), RGBA(80, 80, 100, 1))
            Font: =Font.'Open Sans'
            Height: =40
            Size: =11
            Text: '=If(varStatsStatusError, "Stats status unavailable. Reload before starting or exporting.", IsBlank(varStatsControl.Id), "Set up LibraryStatsControl before starting or exporting.", "Stats: " & Coalesce(varStatsControl.ScanState, "Unknown") & " | Last completed: " & If(IsBlank(varStatsControl.LastSuccessAt), "not recorded", Text(varStatsControl.LastSuccessAt, "dd mmm yyyy HH:mm")) & If(varStatsControl.ScanState = "Succeeded", " | Reload saved stats for latest figures", ""))'
            Visible: =varIsAdmin
            Width: =430
            X: =232
            Y: =212
      - tmrLibraryStatsStatus:
          Control: Timer@2.1.0
          Properties:
            AutoStart: =true
            Duration: =30000
            OnTimerEnd: |-
'''+event(status)+'''            Repeat: =true
            Start: =varIsAdmin
            Visible: =false
'''
# New normal controls go behind existing deletion overlays.
text=text.replace('      - recOverlayBg_1:',controls+'      - recOverlayBg_1:',1)
confirm='''Set(varShowStatsWarning, false);
Set(varRequestStatsBusy, true);
Set(varRequestStatsError, false);
IfError(
    Set(varStatsStartResponse, RebuildLibraryStats.Run()),
    Set(varRequestStatsError, true)
);
Set(varRequestStatsBusy, false);
If(
    varRequestStatsError,
    Notify("Could not confirm whether the scan started. Reload status and check flow history before trying again.", NotificationType.Error),
    Notify(varStatsStartResponse.message, If(varStatsStartResponse.started, NotificationType.Information, NotificationType.Warning))
);
'''+status
text+='''      - recStatsWarningShade:
          Control: Classic/Button@2.2.0
          Properties:
            BorderThickness: =0
            DisplayMode: =DisplayMode.View
            Fill: =RGBA(0, 0, 0, 0.4)
            Height: =Parent.Height
            Text: =""
            Visible: =varShowStatsWarning
            Width: =Parent.Width
      - recStatsWarningPanel:
          Control: Classic/Button@2.2.0
          Properties:
            BorderThickness: =0
            DisplayMode: =DisplayMode.View
            Fill: =RGBA(255, 255, 255, 1)
            Height: =260
            Text: =""
            Visible: =varShowStatsWarning
            Width: =620
            X: =(Parent.Width - Self.Width) / 2
            Y: =(Parent.Height - Self.Height) / 2
      - lblStatsWarningTitle:
          Control: Label@2.5.1
          Properties:
            Font: =Font.'Open Sans'
            FontWeight: =FontWeight.Semibold
            Height: =36
            Size: =20
            Text: ="Rebuild library stats?"
            Visible: =varShowStatsWarning
            Width: =556
            X: =(Parent.Width - 620) / 2 + 32
            Y: =(Parent.Height - 260) / 2 + 20
      - lblStatsWarningText:
          Control: Label@2.5.1
          Properties:
            Font: =Font.'Open Sans'
            Height: =130
            Size: =13
            Text: ="This scans the main site and CCF and normally takes 15 minutes or longer. You can continue using the app. Spreadsheet exports are blocked until the scan finishes successfully. Counts update gradually; click Reload saved stats after completion."
            Visible: =varShowStatsWarning
            Width: =556
            X: =(Parent.Width - 620) / 2 + 32
            Y: =(Parent.Height - 260) / 2 + 60
      - btnCancelStatsScan:
          Control: ModernButton@1.0.0
          Properties:
            Height: =36
            OnSelect: =Set(varShowStatsWarning, false)
            Text: ="Cancel"
            Visible: =varShowStatsWarning
            Width: =130
            X: =(Parent.Width - 620) / 2 + 310
            Y: =(Parent.Height - 260) / 2 + 204
      - btnConfirmStatsScan:
          Control: ModernButton@1.0.0
          Properties:
            DisplayMode: =If(varRequestStatsBusy, DisplayMode.Disabled, DisplayMode.Edit)
            Height: =36
            OnSelect: |-
'''+event(confirm)+'''            Text: ="Start scan"
            Visible: =varShowStatsWarning
            Width: =130
            X: =(Parent.Width - 620) / 2 + 458
            Y: =(Parent.Height - 260) / 2 + 204
'''
# Modal visibility explicitly includes the admin gate as defence in depth.
text=text.replace('Visible: =varShowStatsWarning','Visible: =varIsAdmin && varShowStatsWarning')
out=WORK/'scrManageLibraries.v3.0.yaml'
out.write_text(text,encoding='utf-8')
print('Built',out)
