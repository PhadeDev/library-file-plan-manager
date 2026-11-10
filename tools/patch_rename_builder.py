import io

p = 'tools/build_rename_screen.py'
s = io.open(p, encoding='utf-8', newline='').read().replace('\r\n', '\n')

def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:80], s.count(old))
    s = s.replace(old, new)

# 1) suggestion can be driven from either name
rep("def suggestion(rec):\n    return (\n        'With({_seg: Substitute(Last(Split(' + rec + '.LibraryUrl, \"/\")).Value, \"%20\", \" \"), _nm: Trim(' + rec + '.EffectiveName)}, '",
    "def suggestion(rec, name=None):\n    name = name or (rec + '.EffectiveName')\n    return (\n        'With({_seg: Substitute(Last(Split(' + rec + '.LibraryUrl, \"/\")).Value, \"%20\", \" \"), _nm: Trim(' + name + ')}, '")

# 2) dialog geometry
rep("            Height: =520\n", "            Height: =580\n")
rep("            Y: =120\n\"\"\"", "            Y: =100\n\"\"\"")
rep('"Text": \'="Change web address"\', "Y": "=136"', '"Text": \'="Change web address"\', "Y": "=116"')

old_lib = ('dialog += block_text("lblRenameLib", \'"Library: " & varRenameTarget.EffectiveName\', {**T, "Color": "=RGBA(30, 30, 45, 1)", "FontWeight": "=FontWeight.Semibold", "Height": "=24", "Size": "=13", "Y": "=176"}).rstrip(\'\\n\') + "\\n            Visible: =varRenameVisible\\n"\n')
new_lib = ('dialog += block_text("lblRenameLib", \'"Name in the file plan:  " & varRenameTarget.EffectiveName\', {**T, "Color": "=RGBA(30, 30, 45, 1)", "FontWeight": "=FontWeight.Semibold", "Height": "=24", "Size": "=13", "Y": "=156"}).rstrip(\'\\n\') + "\\n            Visible: =varRenameVisible\\n"\n'
           'dialog += block_text("lblRenameLibName", \'"Library name in SharePoint:  " & If(IsBlank(varRenameTarget.Name), "(not recorded)", varRenameTarget.Name)\', {**T, "Color": "=RGBA(30, 30, 45, 1)", "FontWeight": "=FontWeight.Semibold", "Height": "=24", "Size": "=13", "Y": "=180"}).rstrip(\'\\n\') + "\\n            Visible: =varRenameVisible\\n"\n')
rep(old_lib, new_lib)
rep('"Height": "=40", "Size": "=12", "Y": "=204"}', '"Height": "=40", "Size": "=12", "Y": "=206"}')
rep('"Text": \'="New last part of the address"\', "Y": "=252"', '"Text": \'="New last part of the address"\', "Y": "=254"')
rep('Edit it if you like."\', "Y": "=276"', 'Edit it if you like, or press one of the buttons below the box to start from a different name."\', "Y": "=278"')
rep('"Height": "=22", "Size": "=12", "Y": "=382"', '"Height": "=22", "Size": "=12", "Y": "=422"')
rep('"Height": "=40", "Size": "=12", "Y": "=406"', '"Height": "=40", "Size": "=12", "Y": "=446"')
rep('"Size": "=12",\n                                   "Text": \'="Heads up', '"Size": "=12",\n                                   "Text": \'="Heads up')
rep('Check with the library owner first."\', "Y": "=452"', 'Check with the library owner first."\', "Y": "=492"')
rep('"Height": "=52", "Size": "=12", "Y": "=522"', '"Height": "=52", "Size": "=12", "Y": "=562"')
rep("            Y: =580\n", "            Y: =620\n", count=3)

# 3) quick-fill buttons straight after the text box
quick = '''dialog += f"""      - btnRenameUsePlanName:
          Control: ModernButton@1.0.0
          Properties:
            Appearance: =ButtonAppearance.Outline
            DisplayMode: =If(varRenameBusy, DisplayMode.Disabled, DisplayMode.Edit)
            Height: =32
            OnSelect: |-
              =Set(varRenameSuggestion, {suggestion('varRenameTarget', 'varRenameTarget.EffectiveName')});
              Set(varRenameChecked, "");
              Set(varRenameStatus, "");
              Reset(txtRenameNew)
            Text: ="Use the file plan name"
            Visible: =varRenameVisible
            Width: =230
            X: =343
            Y: =384
      - btnRenameUseLibName:
          Control: ModernButton@1.0.0
          Properties:
            Appearance: =ButtonAppearance.Outline
            DisplayMode: =If(varRenameBusy || IsBlank(varRenameTarget.Name), DisplayMode.Disabled, DisplayMode.Edit)
            Height: =32
            OnSelect: |-
              =Set(varRenameSuggestion, {suggestion('varRenameTarget', 'varRenameTarget.Name')});
              Set(varRenameChecked, "");
              Set(varRenameStatus, "");
              Reset(txtRenameNew)
            Text: ="Use the SharePoint library name"
            Visible: =varRenameVisible
            Width: =260
            X: =583
            Y: =384
"""
'''
anchor = 'dialog += block_text("lblRenameInline"'
rep(anchor, quick + anchor)

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('builder patched')
