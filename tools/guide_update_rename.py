import io

p = 'docs/index.html'
raw = io.open(p, encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in raw else '\n'
t = raw.replace('\r\n', '\n')

s = t.index('      <section id="rename-url-test">')
e = t.index('      </section>', s) + len('      </section>')
new = '''      <section id="rename-url-test">
        <h2>Rename a library's web address from the app (Manage Libraries v2.11)</h2>
        <p>The rename was proven on a test library on 09/11/2026, so it is now built into Manage Libraries. Every library row has a <strong>Rename URL</strong> button. It opens a small window that shows the current address, suggests a new last part (it keeps the file plan number code at the front and tidies the words after it), and lets you edit it. You press <strong>1. Check</strong> first, which changes nothing and tells you what it would do, and only then does <strong>2. Rename now</strong> unlock. It works for libraries tracked in the file plan and, if one is not tracked, it still renames it. After a rename the flow updates the file plan row and the Group Search permission rows, and the screen reloads itself.</p>
        <p><strong>Also fixed in v2.11:</strong> Manage Libraries now loads and shows every library as soon as you open it, so you no longer have to press Reload saved stats first. The filters are reset each time you open the screen. Reload saved stats is still there if you want to refresh after running the stats flow.</p>
        <h3>Apply these steps in order</h3>
        <ol>
          <li>Download <a href="downloads/RenameLibrary_flow_import.zip"><strong>RenameLibrary_flow_import.zip</strong></a>. Power Automate &rarr; My flows &rarr; Import &rarr; <strong>Import Package (Legacy)</strong>, leave it on <strong>Create as new</strong>, choose your SharePoint connection, import. It is a new flow called <strong>FP-RenameLibrary(App)</strong>. Make sure it is <strong>turned on</strong>. You can delete the earlier test flow <strong>FP-RenameLibraryUrl(App)</strong>, nothing uses it.</li>
          <li>In Power Apps Studio, open <strong>Data</strong> &rarr; <strong>Add data</strong> &rarr; search for <strong>FP-RenameLibrary(App)</strong> and add it <strong>before</strong> pasting the screen.</li>
          <li><a href="screens/scrManageLibraries-v2.11.html?v=2.11"><strong>Open the v2.11 full-screen copy page</strong></a>, copy its YAML, delete <code>scrManageLibraries</code>, then paste the whole copied YAML as you normally do. v2.11 already contains the Email CSV button, so you do not need to paste v2.10 as well. No App.OnStart change is needed.</li>
          <li>Open Manage Libraries. The list should fill by itself. Find a <strong>test library</strong> first, press <strong>Rename URL</strong>, check the suggestion, press <strong>1. Check</strong>, read the message, then <strong>2. Rename now</strong>.</li>
        </ol>
        <div class="callout warn"><strong>Not yet run in your tenant:</strong> the flow's new checks and its updating of the Group Search rows, the dialog, and the open-and-load fix. The screen passes the real Microsoft parser and the formula checks, and the underlying rename is the one you proved. Tell me the exact message if anything errors.</div>
        <div class="callout danger"><strong>What a real rename breaks, so plan for it:</strong> bookmarks and links that use the old address stop working, anyone syncing the library to their computer will need to set the sync up again, and pages with a web part pointing at the library, or other flows that use the old address, need updating. Group Search may keep showing the old address until you reopen the app.</div>
        <div class="callout ok"><strong>What the flow refuses to do:</strong> change anything that is not a library directly under the main site or the CCF site, use a name with spaces, slashes or other unsafe characters, use a reserved name (such as Forms or Lists), or rename a library to its own current name. It never moves a library to a different site.</div>
      </section>'''
t = t[:s] + new + t[e:]


def rep(old, new_):
    global t
    assert t.count(old) == 1, old[:80]
    t = t.replace(old, new_)

rep('<a href="screens/scrManageLibraries-v2.10.html?v=2.10"><strong>Open the v2.10 full-screen copy page</strong></a>, copy its YAML, delete <code>scrManageLibraries</code>, then paste the whole copied YAML as you normally do. No App.OnStart change is needed.',
    '<a href="screens/scrManageLibraries-v2.11.html?v=2.11"><strong>Open the v2.11 full-screen copy page</strong></a> (it already includes this button plus the rename feature below), copy its YAML, delete <code>scrManageLibraries</code>, then paste the whole copied YAML as you normally do. No App.OnStart change is needed.')
rep('<a class="link-card" href="screens/scrManageLibraries-v2.10.html?v=2.10">', '<a class="link-card" href="screens/scrManageLibraries-v2.11.html?v=2.11">')
rep('<span class="ver">v2.10 &mdash; 21 Oct 2026 &mdash; adds the Email CSV button to your live v2.9; draft, not yet pasted (needs the new flow first, see Email CSV section above)</span>',
    '<span class="ver">v2.11 &mdash; 09 Nov 2026 &mdash; opens with all libraries loaded, adds Rename URL per library, includes Email CSV; draft, not yet pasted (needs the FP-RenameLibrary(App) flow added first)</span>')
rep('v2.10: an <strong>Email CSV (current view)</strong> button', 'v2.11: loads automatically on open and adds a per-library <strong>Rename URL</strong> button. v2.10: an <strong>Email CSV (current view)</strong> button')
rep('<p>v5.10 build guide. Rename-a-library-URL test added.</p>', '<p>v5.11 build guide. Rename a library URL from the app.</p>')
rep('<span class="pill">v5.10</span>', '<span class="pill">v5.11</span>')
rep('>Rename a library URL (test)</a>', '>Rename a library URL (v2.11)</a>')

io.open(p, 'w', encoding='utf-8', newline='').write(t.replace('\n', nl))
print('guide ok; sections', t.count('<section'), t.count('</section>'))
