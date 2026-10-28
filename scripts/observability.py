"""Apply reviewed PPE observability and remove unused NPU jitter polling."""
import json, re, shutil
from pathlib import Path

def adapt_observability(app, variant):
    runtime = Path(__file__).resolve().parents[1] / 'Runtime'
    rpc = app / 'root/usr/libexec/rpcd/luci.airoha_npu'
    text = rpc.read_text()
    text, n = re.subn(r'^get_ppe_entries\(\) \{.*?^\}', '. /usr/libexec/airoha-ppe-snapshot.sh', text, count=1, flags=re.M|re.S)
    assert n == 1, 'Cannot identify PPE backend'
    if variant == 'naoki':
        # Keep the upstream orphan sweep when replacing its limited PPE reader.
        text = text.replace('. /usr/libexec/airoha-ppe-snapshot.sh', '''. /usr/libexec/airoha-ppe-snapshot.sh
get_ppe_entries() {
	_airoha_tmp_sweep "$(date +%s 2>/dev/null)"
	_ppe_snapshot_json 1024
}''', 1)
    text = text.replace('"getPpeEntries":{}', '"getPpeEntries":{},"getPpeExport":{"snapshot":"str","offset":"int"}', 1)
    marker = '\t\t\tgetPpeEntries)'
    assert text.count(marker) == 1
    text = text.replace(marker, '\t\t\tgetPpeExport)\n\t\t\t\tread -r input\n\t\t\t\tget_ppe_export \"$input\"\n\t\t\t\t;;\n' + marker, 1)
    if variant == 'naoki':
        # No radio on this profile: do not fork iw or scan station data.
        for name, data in [('get_token_info', {'has_wifi':False,'available':False,'reason':'board_has_no_wifi'})]:
            body = "echo '"+json.dumps(data)+"'"
            text, n = re.subn(r'^'+name+r'\(\) \{.*?^\}', name+'() { '+body+'; }', text, count=1, flags=re.M|re.S)
            assert n == 1, name
    if variant == 'naoki':
        # This function normally comes from airoha-common.sh. Override it
        # locally after sourcing that library, without editing shared topology.
        text = text.replace('# 1 while get_dashboard()', "airoha_wifi_stats_json() { echo '{\"has_wifi\":false,\"bands\":[]}'; }\n\n# 1 while get_dashboard()", 1)
    rpc.write_text(text)
    for name in ('airoha-ppe.awk', 'airoha-ppe-snapshot.sh', 'airoha-deadline.sh'):
        dest = app / 'root/usr/libexec' / name
        shutil.copyfile(runtime / name, dest)
        dest.chmod(0o755)
    acl_path = app / 'root/usr/share/rpcd/acl.d/luci-app-airoha-npu.json'
    acl = json.loads(acl_path.read_text())
    methods = acl['luci-app-airoha-npu']['read']['ubus']['luci.airoha_npu']
    if 'getPpeExport' not in methods: methods.append('getPpeExport')
    acl_path.write_text(json.dumps(acl, indent=2)+'\n')
    js = app / 'htdocs/luci-static/resources/view/airoha_npu/status.js'
    s = js.read_text()
    shared = (runtime / 'ppe-view.js').read_text()
    if variant == 'naoki':
        a = s.index('function ppeCountText('); b = s.index('function ppeRows(', a)
        s = s[:a]+shared+'\n'+s[b:]
        s = s.replace("selectFilter(_('All states')", "E('button', {type:'button', 'class':'cbi-button', click:exportFullPpe}, '完整导出 JSON'),\n\t\tselectFilter(_('All states')", 1)
        for key in ('packets', 'bytes'):
            marker = f"e.{key} === null || e.{key} === undefined ? 'N/A' : String(e.{key})"
            assert s.count(marker) == 1, 'PPE counter renderer changed: ' + key
            s = s.replace(marker, f"ppeCounterText(e, '{key}')", 1)
        marker = '\t\tpoll.add(pollFetch, POLL_SECS);'
        assert marker in s
        s = s.replace(marker, marker+"\n\t\tpoll.add(function() { var badge=document.getElementById('ppe-count'); if(badge)badge.textContent=ppeCountText(ppeCurrentEntries); }, 1);", 1)
    else:
        s = s.replace('/* ── PPE Table ── */', 'var ppeCurrentMeta = {}, ppeCurrentEntries = [];\n'+shared+'\n/* ── PPE Table ── */', 1)
        s = s.replace('entries.slice(0,100)', 'entries.slice(0,50)', 1)
        s = s.replace("E('h3',{},_('PPE Flow Offload Entries')),", "E('h3',{},_('PPE Flow Offload Entries')),\n\t\t\t\tE('button',{type:'button', 'class':'cbi-button', click:exportFullPpe},'完整导出 JSON'),\n\t\t\t\tE('p',{'id':'ppe-count'},ppeCountText(entries)+' · 本页显示前50条'),", 1)
        s = re.sub(r'(var entries = Array.isArray\(ppe.entries\)[^;]+;)', r'\1\n                ppeCurrentMeta=ppe; ppeCurrentEntries=entries;', s)
        s = s.replace("var tb=document.getElementById('ppe-entries-table');", "var badge=document.getElementById('ppe-count');if(badge)badge.textContent=ppeCountText(entries)+' · 本页显示前50条';\n\t\t\t\tvar tb=document.getElementById('ppe-entries-table');", 1)
        # PPE snapshots are costly. Keep CPU/FE refresh at 5 s but table at 20 s.
        s = s.replace('var ppeCurrentMeta = {}, ppeCurrentEntries = [];', 'var ppeCurrentMeta = {}, ppeCurrentEntries = [], ppeNextRead = 0;')
        s = s.replace('callNpuStatus(), callPpeEntries(), callFrameEngine()', 'callNpuStatus(), readPpePeriodically(), callFrameEngine()')
        s = s.replace('/* ── Main View ── */', """function readPpePeriodically() {
    if (Date.now() < ppeNextRead) return Promise.resolve(ppeCurrentMeta);
    ppeNextRead = Date.now()+20000;
    return callPpeEntries().catch(function(e) { return {available:false,error:String(e),entries:[]}; }).then(function(ppe) {
        ppeCurrentMeta=ppe; return ppe;
    });
}
/* ── Main View ── */""", 1)
    js.write_text(s)
    for name in ('root/etc/init.d/npu-jitter','root/usr/libexec/npu-jitter-daemon'):
        (app / name).unlink(missing_ok=True)

    if variant == 'naoki':
        make=app/'Makefile'
        text=make.read_text()
        # This upstream variant has an explicit install recipe, so deleting
        # source files alone would leave broken install commands behind.
        text='\n'.join(line for line in text.splitlines()
            if 'npu-jitter' not in line and 'S89airoha-npu' not in line
            and '/etc/init.d/airoha-npu enable' not in line)+'\n'
        marker='\t$(INSTALL_DATA) ./root/usr/libexec/airoha-ppe.awk $(1)/usr/libexec/'
        assert text.count(marker)==1
        text=text.replace(marker,marker+'\n\t$(INSTALL_BIN) ./root/usr/libexec/airoha-ppe-snapshot.sh ./root/usr/libexec/airoha-deadline.sh $(1)/usr/libexec/',1)
        marker='# Clear LuCI cache so the new menu entries are picked up'
        text=text.replace(marker,'# cpufreq is the sole CPU boot owner; this alias remains callable manually.\n/etc/init.d/airoha-npu disable 2>/dev/null\n\n'+marker,1)
        make.write_text(text)
