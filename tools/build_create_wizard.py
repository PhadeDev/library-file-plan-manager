import io, re, sys

VAULT, OUT = sys.argv[1], sys.argv[2]
v = io.open(VAULT, encoding='utf-8', newline='').read().replace('\r\n', '\n')

# ---------------------------------------------------------------- helpers
def get_block(name):
    s = v.index('      - %s:\n' % name)
    m = re.search(r'\n      - ', v[s + 5:])
    e = s + 5 + m.start() + 1 if m else len(v)
    return v[s:e]

def patch(block, **props):
    for k, val in props.items():
        pat = re.compile(r'^(            )%s: .*$' % re.escape(k), re.M)
        line = '            %s: %s' % (k, val)
        if pat.search(block):
            block = pat.sub(lambda m: line, block, count=1)
        else:
            block = block.replace('          Properties:\n', '          Properties:\n' + line + '\n', 1)
    return block

def emit(k, val, ind):
    if '\n' in val or ': ' in val or ' #' in val or val[:1] in '|>&*!%@`':
        lines = val.split('\n')
        return '%s%s: |-\n%s\n' % (ind, k, '\n'.join(ind + '  ' + l for l in lines))
    return '%s%s: %s\n' % (ind, k, val)

def ctl(name, control, props, ind=6, children=None, variant=None):
    p = ' ' * ind
    out = '%s- %s:\n%s    Control: %s\n' % (p, name, p, control)
    if variant:
        out += '%s    Variant: %s\n' % (p, variant)
    out += '%s    Properties:\n' % p
    for k in sorted(props):
        out += emit(k, props[k], p + '      ')
    if children:
        out += '%s    Children:\n' % p + ''.join(children)
    return out

OPEN = "=Font.'Open Sans'"
INK, GREY, MUTED = "RGBA(30, 30, 45, 1)", "RGBA(90, 90, 105, 1)", "RGBA(120, 120, 135, 1)"
PURPLE = "RGBA(83, 42, 69, 1)"
ADMIN = "varIsAdmin"

def label(name, text, x, y, w, h, size=12, color=GREY, weight=None, visible=ADMIN, align=None, fill=None, ind=6):
    p = {'Color': color if color.startswith('=') else '=' + color, 'Font': OPEN, 'Height': '=%s' % h, 'Size': '=%s' % size,
         'Text': text if text.startswith('=') else '=' + text, 'Visible': '=' + visible, 'Width': '=%s' % w, 'X': '=%s' % x, 'Y': '=%s' % y}
    if weight: p['FontWeight'] = '=FontWeight.' + weight
    if align: p['Align'] = '=Align.' + align
    if fill: p['Fill'] = '=' + fill
    return ctl(name, 'Label@2.5.1', p, ind)

def rect(name, x, y, w, h, fill, border='RGBA(220, 222, 232, 1)', visible=ADMIN, radius=12):
    p = {'BorderColor': '=' + border, 'BorderThickness': '=1', 'DisplayMode': '=DisplayMode.View', 'Fill': '=' + fill, 'Height': '=%s' % h,
         'HoverFill': '=Self.Fill', 'PressedFill': '=Self.Fill', 'Text': '=""', 'Visible': '=' + visible, 'Width': '=%s' % w, 'X': '=%s' % x, 'Y': '=%s' % y}
    for c in ('RadiusBottomLeft', 'RadiusBottomRight', 'RadiusTopLeft', 'RadiusTopRight'):
        p[c] = '=%s' % radius
    return ctl(name, 'Classic/Button@2.2.0', p)

def tinput(name, x, y, w, ph, visible, h=44, multiline=False, default=None, onchange=None):
    p = {'BorderColor': '=RGBA(200, 202, 214, 1)', 'BorderThickness': '=1', 'Color': '=' + INK, 'Fill': '=RGBA(255, 255, 255, 1)', 'Height': '=%s' % h,
         'Placeholder': '="%s"' % ph, 'Visible': '=' + visible, 'Width': '=%s' % w, 'X': '=%s' % x, 'Y': '=%s' % y}
    if multiline: p['Type'] = '=TextInputType.Multiline'
    if default: p['Default'] = default
    if onchange: p['OnChange'] = onchange
    return ctl(name, 'ModernTextInput@1.1.2', p)

def button(name, text, x, y, w, h, onselect, visible, outline=False, display=None, appearance=None):
    p = {'Height': '=%s' % h, 'OnSelect': onselect, 'Text': text, 'Visible': '=' + visible, 'Width': '=%s' % w, 'X': '=%s' % x, 'Y': '=%s' % y}
    if appearance: p['Appearance'] = appearance
    elif outline: p['Appearance'] = '=ButtonAppearance.Outline'
    if display: p['DisplayMode'] = display
    return ctl(name, 'ModernButton@1.0.0', p)

# ---------------------------------------------------------------- Power Fx pieces
TEAMV = 'drpTeam.Selected.Value'
PFX = 'IfError(Left(%s, Find("_", %s) - 1), "")' % (TEAMV, TEAMV)
EXTRA = 'Trim(txtExtraPrefix.Text)'
CODE = '(%s & If(IsBlank(%s), "", "_" & %s))' % (PFX, EXTRA, EXTRA)
SLUG = 'Concat(MatchAll(Substitute(Substitute(Trim(txtDisplayName.Text), "&", "and"), " ", "_"), "[A-Za-z0-9_\\-]"), FullMatch)'
GEN = 'If(IsBlank(Trim(txtDisplayName.Text)), "", %s & "_" & %s)' % (CODE, SLUG)
WEB = 'Trim(txtWebAddress.Text)'
DISP = '(%s & "_" & Trim(txtDisplayName.Text))' % CODE
WEB_OK = '(IsMatch(%s, "[A-Za-z0-9][A-Za-z0-9_\\-]*") && Len(%s) <= 100)' % (WEB, WEB)
SUBT = 'Trim(txtSubTeam.Text)'
NEWMODE = '!varRegisterOnly'
STEP = lambda n: 'varCreateStep = %d' % n
LIMITED = 'If(tglIsLimited.Checked, "Yes", "No")'
RESETS = ('Reset(drpTeam);\nReset(txtSubTeam);\nReset(txtExtraPrefix);\nReset(txtDisplayName);\nReset(txtWebAddress);\n'
          'Reset(txtExistingLibraryTitle);\nReset(txtExistingDisplayName);\nReset(txtCategories);\nReset(tglIsLimited);\n')

blocks = []

# ---------------------------------------------------------------- screen header
header = ("Screens:\n  scrAdminCreateLibrary:\n    Properties:\n      Fill: =RGBA(245, 246, 250, 1)\n      OnVisible: |-\n"
          "        =Set(varCreateStep, 1);\n        Set(varRegisterOnly, false);\n        Set(varModeChosen, false);\n        Set(varWebDefault, \"\");\n"
          + '\n'.join('        ' + l for l in RESETS.rstrip(';\n').split('\n')) + "\n    Children:\n")

# ---------------------------------------------------------------- title + access denied
blocks.append(label('lblTitle_1', '="Create a library"', 32, 84, 700, 36, size=22, color=INK, weight='Semibold', visible='true'))
blocks.append(label('lblWizardIntro', '="Answer three short steps for each library. Add as many as you like to the list on the right, then create them all at once."', 32, 120, 1100, 24, color=MUTED, visible=ADMIN))
blocks.append(patch(get_block('recAccessDeniedBg'), Y='=150'))
blocks.append(patch(get_block('lblAccessDenied'), Y='=150'))

# ---------------------------------------------------------------- wizard card
CARD_X, CARD_Y, CARD_W, CARD_H = 32, 156, 720, 584
IX, IW = 56, 672
blocks.append(rect('recWizardCard', CARD_X, CARD_Y, CARD_W, CARD_H, 'RGBA(255, 255, 255, 1)'))

def pill(n, text, x):
    fill = 'If(varCreateStep = %d, %s, If(varCreateStep > %d, RGBA(225, 240, 232, 1), RGBA(236, 238, 244, 1)))' % (n, PURPLE, n)
    color = 'If(varCreateStep = %d, RGBA(255, 255, 255, 1), If(varCreateStep > %d, RGBA(21, 62, 53, 1), RGBA(90, 90, 105, 1)))' % (n, n)
    txt = '=If(varCreateStep > %d, "✓  ", "%d   ") & "%s"' % (n, n, text)
    return label('lblPill%d' % n, txt, x, 172, 212, 34, size=12, color='=' + color, weight='Semibold', align='Center', fill=fill)

blocks += [pill(1, 'Where it belongs', IX), pill(2, 'Name it', IX + 230), pill(3, 'Options', IX + 460)]

blocks.append(label('lblStepTitle', '=Switch(varCreateStep, 1, "Where does it belong?", 2, If(varRegisterOnly, "Which library already exists?", "What is it called?"), "Options and review")',
                    IX, 222, IW, 30, size=18, color=INK, weight='Semibold'))
blocks.append(label('lblStepIntro', '=Switch(varCreateStep, 1, "Choose whether you are creating a new library or adding one that already exists. The rest of the form appears once you choose.", 2, If(varRegisterOnly, "Tell the app which existing library to add to the file plan.", "Type the name people will see. The web address is filled in for you, and you can change it."), "Last checks. Then add it to the list on the right.")',
                    IX, 254, IW, 40, color=GREY))

# ----- step 1: nothing is selected until the user picks one
S1 = ADMIN + ' && ' + STEP(1)
S1F = S1 + ' && varModeChosen'
blocks.append(button('btnModeNew', '="Create a new library"', IX, 302, 328, 44, '=Set(varRegisterOnly, false); Set(varModeChosen, true)', S1,
                     appearance='=If(varModeChosen && !varRegisterOnly, ButtonAppearance.Primary, ButtonAppearance.Outline)'))
blocks.append(button('btnModeExisting', '="Add one that already exists"', IX + 344, 302, 328, 44, '=Set(varRegisterOnly, true); Set(varModeChosen, true)', S1,
                     appearance='=If(varModeChosen && varRegisterOnly, ButtonAppearance.Primary, ButtonAppearance.Outline)'))
blocks.append(label('lblModeHint', '="Pick one of the two options above to continue."', IX, 362, IW, 24, size=13, color=PURPLE, weight='Semibold', visible=S1 + ' && !varModeChosen'))
blocks.append(label('lblTeamLbl', '="Team"', IX, 362, IW, 22, size=13, color=INK, weight='Semibold', visible=S1F))
blocks.append(label('lblTeamHelp', '="Which team owns this library? The team number, for example 04, becomes the start of the library name and web address."', IX, 384, IW, 36, visible=S1F))
blocks.append(ctl('drpTeam', 'ModernDropdown@1.0.3', {'BorderColor': '=RGBA(200, 202, 214, 1)', 'BorderThickness': '=1', 'Color': '=' + INK, 'Fill': '=RGBA(255, 255, 255, 1)',
                  'Height': '=44', 'ItemDisplayText': '=ThisItem.Value', 'Items': '=Choices(LibraryFilePlan.Team)', 'Visible': '=' + S1F, 'Width': '=%d' % IW, 'X': '=%d' % IX, 'Y': '=422'}))
blocks.append(label('lblSubTeamLbl', '="Sub-Team (optional)"', IX, 482, 328, 22, size=13, color=INK, weight='Semibold', visible=S1F))
blocks.append(label('lblSubTeamHelp', '="A grouping inside the team, such as Training Wing, used only to keep the File Plan tidy. It does not change the web address. Leave blank if unsure."', IX, 504, 328, 56, visible=S1F))
blocks.append(tinput('txtSubTeam', IX, 564, 328, 'e.g. Training Wing (optional)', S1F))
blocks.append(label('lblExtraPrefixLbl', '="Extra prefix (optional)"', IX + 344, 482, 328, 22, size=13, color=INK, weight='Semibold', visible=S1F + ' && ' + NEWMODE))
blocks.append(label('lblExtraPrefixHelp', '="The rest of the file plan code after the team number. Under Team 04, typing 04_03 makes the name start 04_04_03. Leave blank if unsure."', IX + 344, 504, 328, 56, visible=S1F + ' && ' + NEWMODE))
blocks.append(tinput('txtExtraPrefix', IX + 344, 564, 328, 'e.g. 04_03 (optional)', S1F + ' && ' + NEWMODE))
blocks.append(label('lblPrefixPreview', '=If(IsBlank(%s), "", "Name and web address will start with:  " & %s & "_")' % (TEAMV, CODE), IX, 616, IW, 24, size=12, color='RGBA(21, 62, 53, 1)', weight='Semibold', visible=S1F + ' && ' + NEWMODE))

# ----- step 2 (new library): one name, web address pre-filled and editable
S2N = ADMIN + ' && ' + STEP(2) + ' && ' + NEWMODE
S2E = ADMIN + ' && ' + STEP(2) + ' && varRegisterOnly'
blocks.append(label('lblNameLbl', '="Library name"', IX, 302, IW, 22, size=13, color=INK, weight='Semibold', visible=S2N))
blocks.append(label('lblNameHelp', '="The name people will see, for example Standard Operating Procedures. Do not type the team number or prefix, the app adds those for you."', IX, 324, IW, 36, visible=S2N))
blocks.append(tinput('txtDisplayName', IX, 362, IW, 'e.g. Standard Operating Procedures', S2N,
                     onchange='=Set(varWebDefault, %s);\nReset(txtWebAddress)' % GEN))
blocks.append(label('lblWebLbl', '="Web address name"', IX, 418, IW, 22, size=13, color=INK, weight='Semibold', visible=S2N))
blocks.append(label('lblWebHelp', '="The last part of the library\'s web address, for example 14_Information_Testing. It is filled in for you from the library name. Change it if you want something shorter, such as 14_InfoTest. Letters, numbers, hyphens and underscores only, no spaces."', IX, 440, IW, 54, visible=S2N))
blocks.append(tinput('txtWebAddress', IX, 498, IW, 'Filled in from the library name', S2N, default='=varWebDefault'))
blocks.append(rect('recPreviewCard', IX, 556, IW, 92, 'RGBA(243, 237, 250, 1)', border='RGBA(215, 200, 235, 1)', visible=S2N, radius=8))
blocks.append(label('lblPreviewHead', '="How it will look"', IX + 16, 561, 300, 22, size=12, color=PURPLE, weight='Semibold', visible=S2N))
blocks.append(label('lblPreviewName', '="Name people see:   " & If(IsBlank(Trim(txtDisplayName.Text)), "(type a name above)", %s)' % DISP, IX + 16, 583, IW - 32, 24, size=13, color=INK, visible=S2N))
blocks.append(label('lblPreviewUrl', '="Full web address:   " & varTenantHost & "/teams/1598/" & If(IsBlank(%s), "(filled in from the name)", %s)' % (WEB, WEB), IX + 16, 610, IW - 32, 24, size=13, color=INK, visible=S2N))
blocks.append(label('lblWebError', '=If(IsBlank(Trim(txtDisplayName.Text)), "", If(%s, If(Lower(Left(%s, Len(%s) + 1)) <> Lower(%s & "_"), "Tip: web addresses normally start with " & %s & "_ so the library sorts into the file plan.", ""), "The web address name must use only letters, numbers, hyphens and underscores, and be between 1 and 100 characters."))' % (WEB_OK, WEB, CODE, CODE, CODE),
                    IX, 652, IW, 32, size=12, color='=If(%s, RGBA(150, 90, 0, 1), RGBA(176, 40, 30, 1))' % WEB_OK, visible=S2N))

# ----- step 2 (existing library)
blocks.append(label('lblExistingLbl', '="Existing library title"', IX, 302, IW, 22, size=13, color=INK, weight='Semibold', visible=S2E))
blocks.append(label('lblExistingHelp', '="Type the title exactly as it appears in SharePoint (Site contents). It is added to the file plan only. Nothing is created or changed in SharePoint."', IX, 324, IW, 36, visible=S2E))
blocks.append(tinput('txtExistingLibraryTitle', IX, 362, IW, 'e.g. 07 PolicyANDPersonnel Pers Forms', S2E))
blocks.append(label('lblExistingNameLbl', '="Name to show in the file plan (optional)"', IX, 430, IW, 22, size=13, color=INK, weight='Semibold', visible=S2E))
blocks.append(label('lblExistingNameHelp', '="Leave blank to use the library title as it is. Fill this in if you want a tidier name to appear in the File Plan."', IX, 452, IW, 36, visible=S2E))
blocks.append(tinput('txtExistingDisplayName', IX, 490, IW, 'e.g. Personnel Forms (optional)', S2E))

# ----- step 3
S3 = ADMIN + ' && ' + STEP(3)
S3N = S3 + ' && ' + NEWMODE
blocks.append(ctl('tglIsLimited', 'ModernToggle@1.0.1', {'Height': '=32', 'Label': '="Limited library"', 'LabelPosition': '="After"', 'Visible': '=' + S3, 'Width': '=%d' % IW, 'X': '=%d' % IX, 'Y': '=302'}))
blocks.append(label('lblLimitedHelp', '=If(varRegisterOnly, "Switch on if this existing library is a Limited one. This only records it in the file plan. It does not change the library permissions.", "Switch on for a library that only a small group should see. Permissions are locked down so only SG_Cadets-Admin-Ltd_MEM and SG_IHUB get access. Leave off for a normal library.")',
                    IX, 336, IW, 52, visible=S3))
blocks.append(label('lblCategoriesLbl', '="Category (CAT) choices (optional)"', IX, 396, IW, 22, size=13, color=INK, weight='Semibold', visible=S3N))
blocks.append(label('lblCategoriesHelp', '="One choice per line, for example Policy, Guidance, Forms. People pick from these in the CAT column. Leave blank to add choices later."', IX, 418, IW, 36, visible=S3N))
blocks.append(tinput('txtCategories', IX, 456, IW, 'Optional: one category per line', S3N, h=72, multiline=True))
review_new = ('"Team:  " & %s & If(IsBlank(%s), "", " / " & %s) & Char(10) & "Name people see:  " & %s & Char(10) & "Web address name:  " & %s & Char(10) & "Limited:  " & %s'
              % (TEAMV, SUBT, SUBT, DISP, WEB, LIMITED))
review_ex = ('"Adds existing library:  " & Trim(txtExistingLibraryTitle.Text) & Char(10) & "Team:  " & %s & If(IsBlank(%s), "", " / " & %s) & Char(10) & "Limited:  " & %s & Char(10) & "Nothing in SharePoint is changed."'
             % (TEAMV, SUBT, SUBT, LIMITED))
blocks.append(rect('recReviewCard', IX, 540, IW, 112, 'RGBA(243, 237, 250, 1)', border='RGBA(215, 200, 235, 1)', visible=S3, radius=8))
blocks.append(label('lblReviewHead', '="Review"', IX + 16, 546, 300, 22, size=12, color=PURPLE, weight='Semibold', visible=S3))
blocks.append(label('lblReview', '=If(varRegisterOnly, %s, %s)' % (review_ex, review_new), IX + 16, 568, IW - 32, 80, size=13, color=INK, visible=S3))

# ----- footer
blocks.append(button('btnBack', '="Back"', IX, 690, 140, 44, '=Set(varCreateStep, varCreateStep - 1)', ADMIN + ' && varCreateStep > 1', outline=True))
step1_ok = '(varModeChosen && !IsBlank(%s))' % TEAMV
step2_ok = 'If(varRegisterOnly, !IsBlank(Trim(txtExistingLibraryTitle.Text)), !IsBlank(Trim(txtDisplayName.Text)) && %s)' % WEB_OK
next_on = ('=If(varCreateStep = 1 && !varRegisterOnly, Set(varWebDefault, %s); Reset(txtWebAddress));\nSet(varCreateStep, varCreateStep + 1)' % GEN)
blocks.append(button('btnNext', '="Next"', IX + IW - 140, 690, 140, 44, next_on, ADMIN + ' && varCreateStep < 3',
                     display='=If(If(varCreateStep = 1, %s, %s), DisplayMode.Edit, DisplayMode.Disabled)' % (step1_ok, step2_ok)))
add_head = ('=If(\n'
    '    varRegisterOnly,\n'
    '    Collect(colQueue, {TechnicalName: "", DisplayName: Trim(txtExistingDisplayName.Text), Team: %s, SubTeam: %s, IsLimited: tglIsLimited.Checked, Categories: "", RegisterOnly: true, ExistingLibraryTitle: Trim(txtExistingLibraryTitle.Text)}),\n'
    '    Collect(colQueue, {TechnicalName: %s, DisplayName: %s, Team: %s, SubTeam: %s, IsLimited: tglIsLimited.Checked, Categories: Trim(txtCategories.Text), RegisterOnly: false, ExistingLibraryTitle: ""})\n'
    ');\n') % (TEAMV, SUBT, WEB, DISP, TEAMV, SUBT)
add_onselect = (add_head + RESETS +
    'Set(varCreateStep, 1);\nSet(varRegisterOnly, false);\nSet(varModeChosen, false);\nSet(varWebDefault, "");\n'
    'Notify("Added to the list. Add another, or press Create on the right.", NotificationType.Success)')
blocks.append(button('btnAddToQueue', '="Add to list"', IX + IW - 220, 690, 220, 44, add_onselect, S3))

# ---------------------------------------------------------------- queue card
QX, QW = 780, 554
blocks.append(rect('recQueueCard', QX, CARD_Y, QW, CARD_H, 'RGBA(255, 255, 255, 1)'))
blocks.append(label('lblQueueHeading', '="Ready to create (" & CountRows(colQueue) & ")"', QX + 24, 172, 400, 28, size=16, color=INK, weight='Semibold'))
blocks.append(label('lblQueueHelp', '=If(CountRows(colQueue) = 0, "Nothing here yet. Finish the steps on the left and press Add to list.", "Nothing is created until you press the Create button below.")', QX + 24, 202, QW - 48, 36, color=MUTED))

def qc(name, control, props):
    return ctl(name, control, props, ind=12)

row_children = [
    qc('recQueueRowBg', 'Classic/Button@2.2.0', {'BorderColor': '=RGBA(238, 239, 245, 1)', 'BorderThickness': '=1', 'DisplayMode': '=DisplayMode.View', 'Fill': '=RGBA(250, 250, 252, 1)',
        'Height': '=68', 'HoverFill': '=Self.Fill', 'PressedFill': '=Self.Fill', 'RadiusBottomLeft': '=6', 'RadiusBottomRight': '=6', 'RadiusTopLeft': '=6', 'RadiusTopRight': '=6',
        'Text': '=""', 'Width': '=%d' % (QW - 56)}),
    qc('lblQueueDisplayName', 'Label@2.5.1', {'Color': '=' + INK, 'Font': OPEN, 'FontWeight': '=FontWeight.Semibold', 'Height': '=24', 'Size': '=13',
        'Text': '=If(IsBlank(ThisItem.DisplayName) || ThisItem.DisplayName = "", ThisItem.ExistingLibraryTitle, ThisItem.DisplayName)', 'Width': '=300', 'X': '=14', 'Y': '=4'}),
    qc('lblQueueTeam', 'Label@2.5.1', {'Color': '=' + MUTED, 'Font': OPEN, 'Height': '=20', 'Size': '=11',
        'Text': '=ThisItem.Team & If(IsBlank(ThisItem.SubTeam) || ThisItem.SubTeam = "", "", " / " & ThisItem.SubTeam)', 'Width': '=360', 'X': '=14', 'Y': '=28'}),
    qc('lblQueueUrl', 'Label@2.5.1', {'Color': '=' + MUTED, 'Font': OPEN, 'Height': '=20', 'Size': '=11',
        'Text': '=If(ThisItem.RegisterOnly, "Adds existing library: " & ThisItem.ExistingLibraryTitle, "Web address ends: " & ThisItem.TechnicalName)', 'Width': '=372', 'X': '=14', 'Y': '=46'}),
    qc('lblQueueRegisterBadge', 'Label@2.5.1', {'Align': '=Align.Center', 'Color': '=RGBA(60, 90, 155, 1)', 'Fill': '=RGBA(225, 233, 250, 1)', 'Font': OPEN, 'FontWeight': '=FontWeight.Bold',
        'Height': '=22', 'Size': '=10', 'Text': '="EXISTING"', 'Visible': '=ThisItem.RegisterOnly', 'Width': '=74', 'X': '=330', 'Y': '=6'}),
    qc('lblQueueLtdBadge', 'Label@2.5.1', {'Align': '=Align.Center', 'Color': '=RGBA(155, 45, 25, 1)', 'Fill': '=RGBA(250, 225, 218, 1)', 'Font': OPEN, 'FontWeight': '=FontWeight.Bold',
        'Height': '=22', 'Size': '=10', 'Text': '="LTD"', 'Visible': '=ThisItem.IsLimited', 'Width': '=44', 'X': '=410', 'Y': '=6'}),
    qc('btnRemoveFromQueue', 'ModernButton@1.0.0', {'Appearance': '=ButtonAppearance.Outline', 'Height': '=32', 'OnSelect': '=Remove(colQueue, ThisItem)', 'Text': '="Remove"', 'Width': '=84', 'X': '=%d' % (QW - 56 - 96), 'Y': '=34'}),
]
blocks.append(ctl('galQueue', 'Gallery@2.15.0', {'Height': '=250', 'Items': '=colQueue', 'LoadingSpinner': '=LoadingSpinner.None', 'TemplatePadding': '=4', 'TemplateSize': '=72',
                  'Visible': '=' + ADMIN, 'Width': '=%d' % (QW - 48), 'X': '=%d' % (QX + 24), 'Y': '=244'}, children=row_children, variant='Vertical'))

run = get_block('btnRunQueue')
run = patch(run, Height='=48', Width='=%d' % (QW - 48), X='=%d' % (QX + 24), Y='=506',
            Text='=If(varQueueRunning, "Creating...", "Create " & CountRows(colQueue) & " librar" & If(CountRows(colQueue) = 1, "y", "ies"))')
blocks.append(run)

# permission index maintenance, with a plain-English explanation
blocks.append(rect('recIndexDivider', QX + 24, 566, QW - 48, 1, 'RGBA(225, 226, 235, 1)', border='RGBA(225, 226, 235, 1)', radius=0))
blocks.append(patch(get_block('lblMaintenanceHeading'), Size='=14', X='=%d' % (QX + 24), Y='=578', Width='=270', Height='=24'))
blocks.append(patch(get_block('btnRebuildIndex'), Appearance='=ButtonAppearance.Outline', Height='=36', X='=%d' % (QX + QW - 24 - 210), Y='=574', Width='=210'))
blocks.append(label('lblIndexHelp', '="Group Search reads a saved list of who can access each Limited library. This button rebuilds that list from SharePoint. It takes about two minutes, runs in the background, and you can keep working. Press it after creating a Limited library, or after changing who has access to a library, so Group Search shows the latest."',
                    QX + 24, 612, QW - 48, 74, size=12, color=GREY))
blocks.append(patch(get_block('lblIndexStatus'), Size='=12', X='=%d' % (QX + 24), Y='=690', Width='=%d' % (QW - 48), Height='=22'))
blocks.append(patch(get_block('lblIndexStaleness'), X='=%d' % (QX + 24), Y='=712', Width='=%d' % (QW - 48), Height='=22'))

# ---------------------------------------------------------------- overlay and nav bar (unchanged)
for n in ['recOverlayBg', 'recOverlayCard', 'icoOverlaySpinner', 'lblOverlayText', 'lblOverlaySub',
          'recNavBarBg_1', 'btnNavFilePlan_1', 'btnNavGroupSearch_1', 'btnNavCreateLibrary_1', 'btnNavManageLibraries_1']:
    blocks.append(get_block(n))

out = header + ''.join(blocks)
io.open(OUT, 'w', encoding='utf-8', newline='').write(out)
print('wrote', OUT, len(out), 'chars,', out.count('\n      - '), 'top-level controls')
