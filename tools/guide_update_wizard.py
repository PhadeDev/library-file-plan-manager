import io

p = 'docs/index.html'
raw = io.open(p, encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in raw else '\n'
t = raw.replace('\r\n', '\n')


def rep(old, new_):
    global t
    assert t.count(old) == 1, old[:90]
    t = t.replace(old, new_)

section = '''      <section id="create-wizard">
        <h2>Create Library, rebuilt as a three-step wizard (v2.0)</h2>
        <p>The old Create Library screen put every box on one page, so it was hard to see what each one was for. v2.0 asks for one thing at a time, with plain-English help text printed under every box (not hidden in tooltips), and a live preview of exactly what will be created.</p>
        <ol>
          <li><strong>Where it belongs:</strong> choose <em>Create a new library</em> or <em>Add one that already exists</em>, then the Team, an optional Sub-Team and an optional Extra prefix. Each has a short explanation, and a line shows how the name and web address will start.</li>
          <li><strong>Name it:</strong> type the library name once. The web address is made from it automatically (spaces become underscores, symbols are dropped, &amp; becomes &ldquo;and&rdquo;), so the name and address now match. A preview card shows both. There is an optional box to type a different web address name if you want something shorter.</li>
          <li><strong>Options and review:</strong> the Limited switch and optional category choices, each explained, then a review box before you press <strong>Add to list</strong>.</li>
        </ol>
        <p>The list of libraries waiting to be created is on the right, with <strong>Create</strong> underneath it, and the Permission Index refresh sits at the bottom of that panel. Nothing is created until you press Create. The Register toggle that used to sit in the top bar is now the first choice on step 1.</p>
        <div class="callout ok"><strong>Same behaviour underneath:</strong> it uses the same <strong>Create Library (App)</strong> flow as before and sends it the same details, so no flow change or re-import is needed. The name and web address still start with the team number and the optional extra prefix (for example Team 04 with extra prefix 04_03 gives 04_04_03_...).</div>
        <h3>Apply it</h3>
        <ol>
          <li><a href="screens/scrAdminCreateLibrary-v2.0.html?v=2.0"><strong>Open the v2.0 full-screen copy page</strong></a>, copy its YAML, delete <code>scrAdminCreateLibrary</code>, then paste the whole copied YAML as you normally do. No App.OnStart change and nothing to add in the Data pane.</li>
          <li>Open Create Library and try it with a <strong>test library</strong> from start to finish. Check the preview shows the name and web address you expect before pressing Create.</li>
        </ol>
        <div class="callout warn"><strong>Not yet seen on screen.</strong> I cannot see the layout in Power Apps Studio. The YAML passes the real Microsoft parser and the formula checks, and I checked by arithmetic that no controls overlap and everything fits inside the card. If anything looks cramped, cut off or misaligned, send me a screenshot of each step and I will adjust. The Back and Next buttons should disable correctly when something required is missing. Tell me if they do not.</div>
      </section>

'''
rep('      <section id="report-controls">', section + '      <section id="report-controls">')
rep('<a href="#report-controls" style="font-weight:800;color:var(--green);">', '<a href="#create-wizard" style="font-weight:800;color:var(--green);">Create Library wizard (v2.0)</a>\n        <a href="#report-controls" style="font-weight:800;color:var(--green);">')

rep('<h3>2. Paste <a href="screens/scrAdminCreateLibrary.html?v=1.13">scrAdminCreateLibrary v1.13</a></h3>',
    '<h3>2. scrAdminCreateLibrary <span style="font-weight:400;color:var(--muted);font-size:.85rem">&mdash; superseded: see &ldquo;Create Library, rebuilt as a three-step wizard (v2.0)&rdquo; at the top of this guide</span></h3>')

old_card_start = '<a class="link-card" href="screens/scrAdminCreateLibrary.html?v=1.13">'
i = t.index(old_card_start)
j = t.index('</a>', i) + 4
new_card = '''<a class="link-card" href="screens/scrAdminCreateLibrary-v2.0.html?v=2.0">
            <div><span class="pill">Screen 2</span><strong style="margin-top:8px;display:block">scrAdminCreateLibrary</strong>
              <p>Restricted to the admin email list. v2.0 is a three-step wizard (Where it belongs, Name it, Options and review) with visible plain-English help text under every box and a live preview. You type the library name once and the web address is made from it (with an optional override). Libraries wait in a list on the right and are created together with one button. A choice on step 1 switches between creating a new library and adding one that already exists. The Permission Index refresh sits at the bottom of the list panel. Same Create Library (App) flow underneath, so no flow change.</p>
              <span class="ver">v2.0 &mdash; 09 Nov 2026 &mdash; draft, not yet pasted (not yet seen on screen, send a screenshot if anything looks off)</span></div>
            <div class="open">Copy YAML &rarr;</div>
          </a>'''
t = t[:i] + new_card + t[j:]

rep('<p>v5.11 build guide. Rename a library URL from the app.</p>', '<p>v5.12 build guide. Create Library wizard and rename from the app.</p>')
rep('<span class="pill">v5.11</span>', '<span class="pill">v5.12</span>')

io.open(p, 'w', encoding='utf-8', newline='').write(t.replace('\n', nl))
print('guide ok; sections', t.count('<section'), t.count('</section>'))
