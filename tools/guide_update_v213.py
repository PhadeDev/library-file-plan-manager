import io, re

p = 'docs/index.html'
raw = io.open(p, encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in raw else '\n'
t = raw.replace('\r\n', '\n')


def replace_section(sec_id, new_html):
    global t
    s = t.index('      <section id="%s">' % sec_id)
    e = t.index('      </section>', s) + len('      </section>')
    t = t[:s] + new_html + t[e:]


def rep(old, new_, count=1):
    global t
    assert t.count(old) == count, (old[:90], t.count(old))
    t = t.replace(old, new_)

wizard = '''      <section id="create-wizard">
        <h2>Create Library, rebuilt as a three-step wizard (v2.1)</h2>
        <p>The old Create Library screen put every box on one page, so it was hard to see what each one was for. The wizard asks for one thing at a time, with plain-English help text printed under every box (not hidden in tooltips), and a live preview of exactly what will be created.</p>
        <ol>
          <li><strong>Where it belongs:</strong> nothing is selected to start with. You pick <em>Create a new library</em> or <em>Add one that already exists</em>, and only then does the rest of the form appear: the Team, an optional Sub-Team and an optional Extra prefix, each with a short explanation and a line showing how the name and web address will start.</li>
          <li><strong>Name it:</strong> type the library name once. The <strong>web address name</strong> is filled in for you in its own box, for example <code>14_Information_Testing</code>, and you can edit it straight away, for example to <code>14_InfoTest</code>. A preview card shows the name people will see and the full web address.</li>
          <li><strong>Options and review:</strong> the Limited switch and optional category choices, each explained, then a review box before you press <strong>Add to list</strong>.</li>
        </ol>
        <p>The list of libraries waiting to be created is on the right, with <strong>Create</strong> underneath it. Nothing is created until you press Create. At the bottom of that panel, the <strong>Permission Index</strong> button now has a plain explanation: Group Search reads a saved list of who can access each Limited library, the button rebuilds that list from SharePoint (about two minutes, in the background), and you press it after creating a Limited library or after changing who has access to one.</p>
        <div class="callout ok"><strong>Same behaviour underneath:</strong> it uses the same <strong>Create Library (App)</strong> flow as before and sends it the same details, so no flow change or re-import is needed. The name and web address still start with the team number and the optional extra prefix (for example Team 04 with extra prefix 04_03 gives 04_04_03_...).</div>
        <h3>Apply it</h3>
        <ol>
          <li><a href="screens/scrAdminCreateLibrary-v2.1.html?v=2.1"><strong>Open the v2.1 full-screen copy page</strong></a>, copy its YAML, delete <code>scrAdminCreateLibrary</code>, then paste the whole copied YAML as you normally do. No App.OnStart change and nothing to add in the Data pane.</li>
          <li>Open Create Library and try it with a <strong>test library</strong> from start to finish. Check the preview shows the name and web address you expect before pressing Create.</li>
        </ol>
        <div class="callout warn"><strong>Seen working by you on 10/11/2026 (v2.0):</strong> the steps, preview and layout looked right. v2.1 changes only what you asked for: no default choice on step 1, the pre-filled editable web address name, and the Permission Index explanation. Tell me if anything looks off.</div>
      </section>'''
replace_section('create-wizard', wizard)

rename = '''      <section id="rename-url-test">
        <h2>Rename a library's web address from the app (Manage Libraries v2.12)</h2>
        <p>Every library row on Manage Libraries has a <strong>Rename URL</strong> button. It opens a window that shows the library's <strong>name in the file plan</strong> and its <strong>name in SharePoint</strong>, the current address, and a suggested new last part of the address (it keeps the file plan number code at the front and tidies the words after it). Two buttons under the box, <strong>Use the file plan name</strong> and <strong>Use the SharePoint library name</strong>, rebuild the suggestion from whichever name you want the address to match. You can also type your own. Press <strong>1. Check</strong> first, which changes nothing and tells you what it would do, and only then does <strong>2. Rename now</strong> unlock. After a rename the flow updates the file plan row and the Group Search permission rows, and the screen reloads itself.</p>
        <p>Manage Libraries also loads and shows every library as soon as you open it, so you no longer have to press Reload saved stats first. The filters are reset each time you open the screen. Reload saved stats is still there if you want to refresh after running the stats flow.</p>
        <p class="muted"><strong>Seen working by you on 10/11/2026 (v2.11):</strong> the window, the live validation and the Check button. v2.12 adds the second name line and the two suggestion buttons.</p>
        <h3>If you have not set the flow up yet</h3>
        <ol>
          <li>Download <a href="downloads/RenameLibrary_flow_import.zip"><strong>RenameLibrary_flow_import.zip</strong></a>. Power Automate &rarr; My flows &rarr; Import &rarr; <strong>Import Package (Legacy)</strong>, choose <strong>Create as new</strong> (not Update), choose your SharePoint connection, import. It is a new flow called <strong>FP-RenameLibrary(App)</strong>. Make sure it is <strong>turned on</strong>. You can delete the earlier test flow <strong>FP-RenameLibraryUrl(App)</strong>.</li>
          <li>In Power Apps Studio, open <strong>Data</strong> &rarr; <strong>Add data</strong> &rarr; search for <strong>FP-RenameLibrary(App)</strong> and add it <strong>before</strong> pasting the screen.</li>
        </ol>
        <h3>Update the screen</h3>
        <ol>
          <li><a href="screens/scrManageLibraries-v2.12.html?v=2.12"><strong>Open the v2.12 full-screen copy page</strong></a>, copy its YAML, delete <code>scrManageLibraries</code>, then paste the whole copied YAML as you normally do. It already contains the Email CSV button. No App.OnStart change is needed.</li>
          <li>Try <strong>Rename URL</strong> on a test library, and check the suggestion buttons fill the box as you expect.</li>
        </ol>
        <div class="callout danger"><strong>What a real rename breaks, so plan for it:</strong> bookmarks and links that use the old address stop working, anyone syncing the library to their computer will need to set the sync up again, and pages with a web part pointing at the library, or other flows that use the old address, need updating. Group Search may keep showing the old address until you reopen the app.</div>
        <div class="callout ok"><strong>What the flow refuses to do:</strong> change anything that is not a library directly under the main site or the CCF site, use a name with spaces, slashes or other unsafe characters, use a reserved name (such as Forms or Lists), or rename a library to its own current name. It never moves a library to a different site.</div>
      </section>'''
replace_section('rename-url-test', rename)

# links and labels that mention the old versions
t = t.replace('screens/scrManageLibraries-v2.11.html?v=2.11', 'screens/scrManageLibraries-v2.12.html?v=2.12')
rep('<strong>Open the v2.11 full-screen copy page</strong></a> (it already includes this button plus the rename feature below)', '<strong>Open the v2.12 full-screen copy page</strong></a> (it already includes this button plus the rename feature below)')
rep('>Create Library wizard (v2.0)</a>', '>Create Library wizard (v2.1)</a>')
rep('>Rename a library URL (v2.11)</a>', '>Rename a library URL (v2.12)</a>')

# gallery cards
rep('v2.11: loads automatically on open and adds a per-library <strong>Rename URL</strong> button.', 'v2.12: the Rename URL window shows both the file plan name and the SharePoint library name and can suggest an address from either. v2.11: loads automatically on open and adds a per-library <strong>Rename URL</strong> button.')
rep('<span class="ver">v2.11 &mdash; 09 Nov 2026 &mdash; opens with all libraries loaded, adds Rename URL per library, includes Email CSV; draft, not yet pasted (needs the FP-RenameLibrary(App) flow added first)</span>',
    '<span class="ver">v2.12 &mdash; 10 Nov 2026 &mdash; adds both names and suggestion buttons to the Rename URL window (v2.11 confirmed working); draft, not yet pasted</span>')

i = t.index('<a class="link-card" href="screens/scrAdminCreateLibrary-v2.0.html?v=2.0">')
j = t.index('</a>', i) + 4
card = '''<a class="link-card" href="screens/scrAdminCreateLibrary-v2.1.html?v=2.1">
            <div><span class="pill">Screen 2</span><strong style="margin-top:8px;display:block">scrAdminCreateLibrary</strong>
              <p>Restricted to the admin email list. A three-step wizard (Where it belongs, Name it, Options and review) with visible plain-English help text under every box and a live preview. Nothing is selected at the start: you choose between creating a new library and adding an existing one, and the form appears. You type the library name once and the web address name is filled in for you, ready to edit. Libraries wait in a list on the right and are created together with one button. The Permission Index button has a plain explanation of what it does and when to press it. Same Create Library (App) flow underneath, so no flow change.</p>
              <span class="ver">v2.1 &mdash; 10 Nov 2026 &mdash; v2.0 layout seen working by you; v2.1 adds no default choice, pre-filled web address and Permission Index help; draft, not yet pasted</span></div>
            <div class="open">Copy YAML &rarr;</div>
          </a>'''
t = t[:i] + card + t[j:]

rep('<p>v5.12 build guide. Create Library wizard and rename from the app.</p>', '<p>v5.13 build guide. Create Library wizard and rename from the app.</p>')
rep('<span class="pill">v5.12</span>', '<span class="pill">v5.13</span>')

io.open(p, 'w', encoding='utf-8', newline='').write(t.replace('\n', nl))
print('guide ok; sections', t.count('<section'), t.count('</section>'))
