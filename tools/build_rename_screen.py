import io, sys

SRC, OUT = sys.argv[1], sys.argv[2]
text = io.open(SRC, encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in text else '\n'
text = text.replace('\r\n', '\n')

FLOW = "'FP-RenameLibrary(App)'"
HOST = "varTenantHost"

def rep(old, new):
    global text
    assert text.count(old) == 1, (old[:80], text.count(old))
    text = text.replace(old, new)

def indent(block, n):
    pad = ' ' * n
    return '\n'.join((pad + l if l.strip() else l) for l in block.split('\n'))

# ---- shared Power Fx pieces -------------------------------------------------
REBUILD_COLLECTIONS = """ClearCollect(colFilePlan, LibraryFilePlan);
ClearCollect(colFilePlanFiltered, AddColumns(colFilePlan, TeamName, If(IsBlank(Team.Value) || Team.Value = "", "Uncategorised", Team.Value), SubTeamName, Coalesce(SubTeam.Value, ""), EffectiveName, If(IsBlank(PrettyName) || PrettyName = "", Title, PrettyName)));
ClearCollect(colTeamGroups, Sort(AddColumns(GroupBy(colFilePlanFiltered, TeamName, GroupedItems), ItemCount, CountRows(GroupedItems), TeamSortKey, If(TeamName = "Uncategorised", "zzz_" & TeamName, TeamName)), TeamSortKey, SortOrder.Ascending));
ClearCollect(colSubTeamGroups, AddColumns(GroupBy(Filter(colFilePlanFiltered, !IsBlank(SubTeamName) && SubTeamName <> ""), TeamName, SubTeamName, GroupedItems), ItemCount, CountRows(GroupedItems)));
Clear(colFlatSource);
Collect(colFlatSource, AddColumns(colTeamGroups, RowType, "Team", SortKey, TeamSortKey, SubSortKey, "", RankInGroup, 0));
Collect(colFlatSource, AddColumns(colSubTeamGroups, RowType, "SubTeam", SortKey, If(TeamName = "Uncategorised", "zzz_" & TeamName, TeamName), SubSortKey, SubTeamName, RankInGroup, 1));
Collect(colFlatSource, AddColumns(colFilePlanFiltered, RowType, "Library", SortKey, If(TeamName = "Uncategorised", "zzz_" & TeamName, TeamName), SubSortKey, If(IsBlank(SubTeamName) || SubTeamName = "", "zzz_none", SubTeamName), RankInGroup, If(IsBlank(SubTeamName) || SubTeamName = "", 1, 2)));"""

UNFILTERED_MANAGE = """ClearCollect(colManageTeamFilterOptions, Table({TeamName: "All Teams"}));
Collect(colManageTeamFilterOptions, colTeamGroups);
ClearCollect(colManageFiltered, AddColumns(colFilePlanFiltered, NameSaysLtd, "_LTD" in Upper(LibraryUrl) || "(LTD)" in Upper(EffectiveName), PermsBroken, LibraryUrl in colPermissionIndex.LibraryUrl));
ClearCollect(colManageTeamGroups, Sort(AddColumns(GroupBy(colManageFiltered, TeamName, GroupedItems), ItemCount, CountRows(GroupedItems), TeamSortKey, If(TeamName = "Uncategorised", "zzz_" & TeamName, TeamName)), TeamSortKey, SortOrder.Ascending));
ClearCollect(colManageSubTeamGroups, AddColumns(GroupBy(Filter(colManageFiltered, !IsBlank(SubTeamName) && SubTeamName <> ""), TeamName, SubTeamName, GroupedItems), ItemCount, CountRows(GroupedItems)));
Clear(colManageFlatSource);
Collect(colManageFlatSource, AddColumns(colManageTeamGroups, RowType, "Team", SortKey, TeamSortKey, SubSortKey, "", RankInGroup, 0));
Collect(colManageFlatSource, AddColumns(colManageSubTeamGroups, RowType, "SubTeam", SortKey, If(TeamName = "Uncategorised", "zzz_" & TeamName, TeamName), SubSortKey, SubTeamName, RankInGroup, 1));
Collect(colManageFlatSource, AddColumns(colManageFiltered, RowType, "Library", SortKey, If(TeamName = "Uncategorised", "zzz_" & TeamName, TeamName), SubSortKey, If(IsBlank(SubTeamName) || SubTeamName = "", "zzz_none", SubTeamName), RankInGroup, If(IsBlank(SubTeamName) || SubTeamName = "", 1, 2)));"""

# ---- 1) OnVisible: always load fresh data, ignore the (not yet drawn) filter boxes
a = text.index('      OnVisible: |-\n')
b = text.index('    Children:\n', a)
on_visible = ("      OnVisible: |-\n" + indent(
    "=Set(varMgmtLoading, true);\n"
    "Reset(txtSearch_2);\nReset(drpTeamFilter);\nReset(drpMgmtFileCount);\nReset(drpMgmtAge);\n"
    "Refresh(LibraryFilePlan);\n" + REBUILD_COLLECTIONS + "\n" + UNFILTERED_MANAGE + "\n"
    "Clear(colMgmtExpandedTeams);\nClear(colMgmtExpandedSubTeams);\nClear(colSelectedLibraries);\n"
    "Set(varConfirmOverrideVisible, false);\nSet(varRenameVisible, false);\nSet(varDeleteStatus, \"\");\nSet(varMgmtLoading, false)", 8) + "\n")
text = text[:a] + on_visible + text[b:]

# ---- 2) suggestion expression (keeps the file-plan number code, tidies the words)
def suggestion(rec):
    return (
        'With({_seg: Substitute(Last(Split(' + rec + '.LibraryUrl, "/")).Value, "%20", " "), _nm: Trim(' + rec + '.EffectiveName)}, '
        'With({_code: Coalesce(Match(_seg, "^[0-9]([0-9_\\-]*[0-9])?").FullMatch, ""), '
        '_words: Mid(_nm, Len(Coalesce(Match(_nm, "^[0-9]([0-9_\\-\\. ]*[0-9])?[ _\\-\\.]*").FullMatch, "")) + 1)}, '
        'With({_slug: Concat(MatchAll(Substitute(Substitute(Trim(_words), "&", "and"), " ", "_"), "[A-Za-z0-9_\\-]"), FullMatch)}, '
        'If(IsBlank(_slug), _code, If(IsBlank(_code), _slug, _code & "_" & _slug)))))')

NEWNAME = 'Trim(txtRenameNew.Text)'
CURSEG = 'Last(Split(varRenameTarget.LibraryUrl, "/")).Value'
VALID = ('(IsMatch(' + NEWNAME + ', "[A-Za-z0-9][A-Za-z0-9_\\-]*") && Len(' + NEWNAME + ') <= 100 && Lower(' + NEWNAME + ') <> Lower(' + CURSEG + '))')
PARENT = 'Left(varRenameTarget.LibraryUrl, Len(varRenameTarget.LibraryUrl) - Len(' + CURSEG + '))'

# ---- 3) per-row Rename button (inserted at the end of the gallery children)
row_btn = f"""            - btnRowRename:
                Control: ModernButton@1.0.0
                Properties:
                  Appearance: =ButtonAppearance.Outline
                  Height: =32
                  OnSelect: |-
                    =Set(varRenameTarget, ThisItem);
                    Set(varRenameStatus, "");
                    Set(varRenameStatusOk, false);
                    Set(varRenameChecked, "");
                    Set(varRenameSuggestion, {suggestion('ThisItem')});
                    Reset(txtRenameNew);
                    Set(varRenameVisible, true)
                  Text: ="Rename URL"
                  Tooltip: ="Change this library's web address"
                  Visible: =ThisItem.RowType = "Library"
                  Width: =100
                  X: =1157
                  Y: =58
"""
anchor = '      - recOverlayBg_1:\n'
rep(anchor, row_btn + anchor)

# ---- 4) loading label + rename dialog (top of z-order, at the end of the screen)
reload_src = text.index('      - btnReloadLibraryStats:')
r_on = text.index('            OnSelect: |-\n', reload_src) + len('            OnSelect: |-\n')
r_end = text.index('            Text: ="Reload saved stats"', r_on)
reload_body = text[r_on:r_end].rstrip('\n')
lines = reload_body.split('\n')
assert lines[-1].strip().startswith('Notify('), lines[-1][:60]
body_lines = [l[14:] if l.startswith(' ' * 14) else l for l in lines[:-1]]
body_lines[0] = body_lines[0].lstrip('=')
reload_body_no_notify = '\n'.join(body_lines).rstrip()
# reload_body is already indented by 14 spaces and starts with '=' on its first line

def yv(v):
    return "'" + v.replace("'", "''") + "'" if (': ' in v or ' #' in v) else v

def label(name, props, visible='varRenameVisible'):
    out = f"      - {name}:\n          Control: Label@2.5.1\n          Properties:\n"
    for k, v in props.items():
        out += f"            {k}: {yv(v)}\n"
    out += f"            Visible: ={visible}\n"
    return out

def block_text(name, expr, extra):
    out = f"      - {name}:\n          Control: Label@2.5.1\n          Properties:\n"
    for k, v in extra.items():
        out += f"            {k}: {v}\n"
    out += "            Text: |-\n              =" + expr + "\n"
    return out

GREY = "=RGBA(80, 80, 100, 1)"
dialog = ""
dialog += label("lblMgmtLoading", {"Color": GREY, "Font": "=Font.'Open Sans'", "FontWeight": "=FontWeight.Semibold", "Height": "=30", "Size": "=14",
                                    "Text": '="Loading libraries..."', "Width": "=400", "X": "=32", "Y": "=292"}, visible="varIsAdmin && varMgmtLoading")
dialog += """      - recRenameOverlay:
          Control: Classic/Button@2.2.0
          Properties:
            BorderThickness: =0
            DisplayMode: =DisplayMode.View
            Fill: =RGBA(0, 0, 0, 0.45)
            Height: =768
            HoverFill: =Self.Fill
            PressedFill: =Self.Fill
            Text: =""
            Visible: =varRenameVisible
            Width: =1318
      - recRenameCard:
          Control: Classic/Button@2.2.0
          Properties:
            BorderColor: =RGBA(200, 202, 214, 1)
            BorderThickness: =1
            DisplayMode: =DisplayMode.View
            Fill: =RGBA(255, 255, 255, 1)
            Height: =520
            HoverFill: =Self.Fill
            PressedFill: =Self.Fill
            RadiusBottomLeft: =12
            RadiusBottomRight: =12
            RadiusTopLeft: =12
            RadiusTopRight: =12
            Text: =""
            Visible: =varRenameVisible
            Width: =680
            X: =319
            Y: =120
"""
T = {"Font": "=Font.'Open Sans'", "Width": "=632", "X": "=343"}
dialog += label("lblRenameTitle", {**T, "Color": "=RGBA(30, 30, 45, 1)", "FontWeight": "=FontWeight.Semibold", "Height": "=32", "Size": "=18", "Text": '="Change web address"', "Y": "=136"})
dialog += block_text("lblRenameLib", '"Library: " & varRenameTarget.EffectiveName', {**T, "Color": "=RGBA(30, 30, 45, 1)", "FontWeight": "=FontWeight.Semibold", "Height": "=24", "Size": "=13", "Y": "=176"}).rstrip('\n') + "\n            Visible: =varRenameVisible\n"
dialog += block_text("lblRenameCurrent", '"Current address: " & ' + HOST + ' & varRenameTarget.LibraryUrl', {**T, "Color": GREY, "Height": "=40", "Size": "=12", "Y": "=204"}).rstrip('\n') + "\n            Visible: =varRenameVisible\n"
dialog += label("lblRenameNewLbl", {**T, "Color": "=RGBA(30, 30, 45, 1)", "FontWeight": "=FontWeight.Semibold", "Height": "=24", "Size": "=13", "Text": '="New last part of the address"', "Y": "=252"})
dialog += label("lblRenameHelp", {**T, "Color": GREY, "Height": "=52", "Size": "=12",
                                   "Text": '="Only the last part of the address changes. Use letters, numbers, hyphens and underscores, with no spaces. The suggestion keeps the file plan number code at the front and tidies the name after it. Edit it if you like."', "Y": "=276"})
dialog += """      - txtRenameNew:
          Control: ModernTextInput@1.1.2
          Properties:
            BorderColor: =RGBA(200, 202, 214, 1)
            BorderThickness: =1
            Color: =RGBA(30, 30, 45, 1)
            Default: =varRenameSuggestion
            Fill: =RGBA(255, 255, 255, 1)
            Height: =44
            Visible: =varRenameVisible
            Width: =632
            X: =343
            Y: =334
"""
dialog += block_text("lblRenameInline", 'If(IsBlank(' + NEWNAME + '), "", If(!IsMatch(' + NEWNAME + ', "[A-Za-z0-9][A-Za-z0-9_\\-]*"), "Use letters, numbers, hyphens and underscores only, with no spaces.", If(Lower(' + NEWNAME + ') = Lower(' + CURSEG + '), "That is the same as the current name.", "")))',
                     {**T, "Color": "=RGBA(176, 40, 30, 1)", "Height": "=22", "Size": "=12", "Y": "=382"}).rstrip('\n') + "\n            Visible: =varRenameVisible\n"
dialog += block_text("lblRenamePreview", '"New address: " & ' + HOST + ' & ' + PARENT + ' & ' + NEWNAME, {**T, "Color": "=RGBA(21, 62, 53, 1)", "FontWeight": "=FontWeight.Semibold", "Height": "=40", "Size": "=12", "Y": "=406"}).rstrip('\n') + "\n            Visible: =varRenameVisible && " + VALID.replace('\n', ' ') + "\n"
dialog += label("lblRenameWarn", {**T, "Color": "=RGBA(120, 70, 0, 1)", "Fill": "=RGBA(255, 244, 222, 1)", "Height": "=64", "Size": "=12",
                                   "Text": '="Heads up: old links and bookmarks to this library will stop working, and anyone syncing it to their computer will need to set the sync up again. Check with the library owner first."', "Y": "=452"})
dialog += block_text("lblRenameStatus", 'varRenameStatus', {**T, "Color": "=If(varRenameStatusOk, RGBA(21, 62, 53, 1), RGBA(176, 40, 30, 1))", "FontWeight": "=FontWeight.Semibold", "Height": "=52", "Size": "=12", "Y": "=522"}).rstrip('\n') + "\n            Visible: =varRenameVisible && !IsBlank(varRenameStatus)\n"

btn_common = "          Control: ModernButton@1.0.0\n          Properties:\n"
dialog += f"""      - btnRenameCancel:
{btn_common}            Appearance: =ButtonAppearance.Outline
            DisplayMode: =If(varRenameBusy, DisplayMode.Disabled, DisplayMode.Edit)
            Height: =40
            OnSelect: =Set(varRenameVisible, false)
            Text: ="Cancel"
            Visible: =varRenameVisible
            Width: =140
            X: =343
            Y: =580
      - btnRenameCheck:
{btn_common}            DisplayMode: =If(varRenameBusy || !{VALID}, DisplayMode.Disabled, DisplayMode.Edit)
            Height: =40
            OnSelect: |-
              =Set(varRenameBusy, true);
              Set(varRenameStatusOk, false);
              Set(varRenameStatus, "Checking...");
              Set(varRenameError, false);
              Set(varRenameChecked, "");
              IfError(
                  Set(varRenameResp, {FLOW}.Run(varRenameTarget.LibraryUrl, {NEWNAME}, {{Confirm: "CHECK"}})),
                  Set(varRenameError, true)
              );
              Set(varRenameBusy, false);
              If(
                  varRenameError,
                  Set(varRenameStatus, "The check could not run. Make sure the FP-RenameLibrary(App) flow is turned on in Power Automate."),
                  Set(varRenameStatusOk, varRenameResp.Success);
                  Set(varRenameStatus, varRenameResp.Message);
                  If(varRenameResp.Success, Set(varRenameChecked, {NEWNAME}))
              )
            Text: =If(varRenameBusy, "Working...", "1. Check")
            Visible: =varRenameVisible
            Width: =200
            X: =503
            Y: =580
      - btnRenameNow:
{btn_common}            BasePaletteColor: =RGBA(190, 50, 50, 1)
            DisplayMode: =If(varRenameBusy || {NEWNAME} <> varRenameChecked || IsBlank(varRenameChecked), DisplayMode.Disabled, DisplayMode.Edit)
            Height: =40
            OnSelect: |-
              =Set(varRenameBusy, true);
              Set(varRenameStatusOk, false);
              Set(varRenameStatus, "Changing the address... this can take up to a minute.");
              Set(varRenameError, false);
              IfError(
                  Set(varRenameResp, {FLOW}.Run(varRenameTarget.LibraryUrl, {NEWNAME}, {{Confirm: "RENAME"}})),
                  Set(varRenameError, true)
              );
              Set(varRenameBusy, false);
              If(
                  varRenameError,
                  Set(varRenameStatus, "Something went wrong part-way. The library may or may not have been renamed. Open it in SharePoint to check its address, then press Reload saved stats."),
                  Set(varRenameStatusOk, varRenameResp.Success);
                  Set(varRenameStatus, varRenameResp.Message);
                  If(
                      varRenameResp.Success,
                      Set(varRenameChecked, "");
                      Refresh('PermissionIndex');
                      ClearCollect(colPermissionIndex, Filter('PermissionIndex', PermissionLevel <> "Limited Access" && PrincipalType <> "User"));
{indent(reload_body_no_notify, 22)}
                      Notify("Web address changed to " & varRenameResp.NewUrl, NotificationType.Success);
                      Set(varRenameVisible, false)
                  )
              )
            Text: ="2. Rename now"
            Visible: =varRenameVisible
            Width: =200
            X: =775
            Y: =580
"""

text = text.rstrip('\n') + '\n' + dialog

io.open(OUT, 'w', encoding='utf-8', newline='').write(text.replace('\n', nl))
print('wrote', OUT, len(text), 'chars')
