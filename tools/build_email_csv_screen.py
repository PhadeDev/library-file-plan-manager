import io, sys

SRC, OUT = sys.argv[1], sys.argv[2]
text = io.open(SRC, encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in text else '\n'
text = text.replace('\r\n', '\n')

def q(expr):
    return 'Char(34) & Substitute(' + expr + ', Char(34), Char(34) & Char(34)) & Char(34)'

def safe(field):
    return 'If(Left(' + field + ', 1) in ["=", "+", "-", "@"], "\'" & ' + field + ', ' + field + ')'

row = ' & "," & '.join([
    q(safe('EffectiveName')),
    q('varTenantHost & LibraryUrl'),
    q(safe('TeamName')),
    q(safe('SubTeamName')),
    'If(IsLimited || NameSaysLtd, "Yes", "No")',
    'If(IsBlank(LibraryCreated), "", Text(LibraryCreated, "dd/mm/yyyy"))',
    'If(IsBlank(LibraryFileCount), "", Text(LibraryFileCount, "0"))',
    'If(IsBlank(LibraryFileCount), "Unknown", If(LibraryFileCount = 0, "Yes", "No"))',
    'If(IsBlank(LibraryFileCount) || IsBlank(LibraryCreated), "Unknown", If(LibraryFileCount = 0 && LibraryCreated <= DateAdd(Today(), -6, TimeUnit.Months), "Yes", "No"))',
]) + ' & Char(13) & Char(10)'

header = 'Library,Library URL,Team,Sub-Team,Limited,Created,File count,Empty,Review (empty and created 6+ months ago)'
summary = ('"Libraries included: " & CountRows(colManageFiltered) & " of " & CountRows(colFilePlanFiltered) & ". Team: " & Coalesce(drpTeamFilter.Selected.TeamName, "All Teams") '
           '& ". File count: " & Coalesce(drpMgmtFileCount.Selected.Value, "All file counts") & ". Age: " & Coalesce(drpMgmtAge.Selected.Value, "Any library age") '
           '& If(IsBlank(Trim(txtSearch_2.Text)), "", ". Search: " & txtSearch_2.Text) & "."')

block = f'''      - lblEmailCsvStatus:
          Control: Label@2.5.1
          Properties:
            Align: =Align.Right
            Color: =If(varCsvEmailError, RGBA(192, 57, 43, 1), If(varCsvEmailBusy, RGBA(60, 60, 80, 1), RGBA(21, 62, 53, 1)))
            Font: =Font.'Open Sans'
            FontWeight: =FontWeight.Semibold
            Height: =40
            Size: =12
            Text: =varCsvEmailStatus
            Visible: =varIsAdmin && !IsBlank(varCsvEmailStatus)
            Width: =440
            X: =640
            Y: =216
      - btnEmailLibraryCsv:
          Control: ModernButton@1.0.0
          Properties:
            DisplayMode: =If(varCsvEmailBusy, DisplayMode.Disabled, DisplayMode.Edit)
            Height: =40
            OnSelect: |-
              =If(
                  CountRows(colManageFiltered) = 0,
                  Notify("There are no libraries in the current view to export.", NotificationType.Warning),
                  Set(varCsvEmailBusy, true);
                  Set(varCsvEmailError, false);
                  Set(varCsvEmailStatus, "Sending to " & User().Email & "... this takes a few seconds.");
                  Set(varLibraryCsv, "{header}" & Char(13) & Char(10) & Concat(SortByColumns(colManageFiltered, "TeamName", SortOrder.Ascending, "SubTeamName", SortOrder.Ascending, "EffectiveName", SortOrder.Ascending), {row}));
                  IfError(
                      'FP-EmailLibraryCsv(App)'.Run(varLibraryCsv, User().Email, {{Summary: {summary}}}),
                      Set(varCsvEmailError, true)
                  );
                  Set(varCsvEmailBusy, false);
                  If(
                      varCsvEmailError,
                      Set(varCsvEmailStatus, "The CSV could not be emailed. Check My flows > FP-EmailLibraryCsv(App) in Power Automate for the failed run.");
                      Notify("The CSV could not be emailed. Check My flows > FP-EmailLibraryCsv(App) in Power Automate for the failed run.", NotificationType.Error),
                      Set(varCsvEmailStatus, "Sent to " & User().Email & " at " & Text(Now(), "hh:mm") & " (" & CountRows(colManageFiltered) & " libraries). It should arrive within a couple of minutes; check Junk if it does not.");
                      Notify("CSV emailed to " & User().Email & ". It should arrive within a minute or two (check Junk if it does not).", NotificationType.Success)
                  )
              )
            Text: =If(varCsvEmailBusy, "Sending...", "Email CSV (current view)")
            Visible: =varIsAdmin
            Width: =210
            X: =1096
            Y: =216
'''

anchor = '      - lblSelectedCount:\n'
assert text.count(anchor) == 1
text = text.replace(anchor, block + anchor, 1)
io.open(OUT, 'w', encoding='utf-8', newline='').write(text.replace('\n', nl))
print('wrote', OUT, len(text), 'chars')
