// Shared export and snapshot semantics in the naoki and luanmuc views.
var callPpeExport = rpc.declare({object:'luci.airoha_npu',method:'getPpeExport',params:['snapshot','offset']});
function exportFullPpe(event) {
    var button=event.currentTarget, all=[], first=null, token='', offset=0;
    button.disabled=true;
    function next() {
        return callPpeExport(token,offset).then(function(data) {
            if (!data || data.available !== true || !Array.isArray(data.entries) ||
                !Number.isInteger(data.total) || data.total<0 || data.offset!==offset ||
                data.returned!==data.entries.length || data.next_offset!==offset+data.entries.length ||
                typeof data.has_more!=='boolean' || !/^[a-zA-Z0-9]{6}$/.test(data.export_id))
                throw new Error(data && data.error || '导出分页校验失败');
            if (!first) { first=data; token=data.export_id; }
            if (data.export_id!==token || data.total!==first.total || data.captured_at!==first.captured_at)
                throw new Error('导出快照发生变化');
            all=all.concat(data.entries); offset=data.next_offset;
            if (data.has_more) {
                if (!data.entries.length || all.length>=data.total) throw new Error('无效分页进度');
                return next();
            }
            if (all.length!==data.total) throw new Error('完整性校验失败，未导出');
            var complete=Object.assign({},first,{entries:all,returned:all.length,offset:0,
                next_offset:all.length,has_more:false,truncated:false,list_limit:0,export_page_size:128});
            var url=URL.createObjectURL(new Blob([JSON.stringify(complete,null,2)],{type:'application/json'}));
            var link=document.createElement('a');link.href=url;
            link.download='xg2010g-ppe-full-'+first.captured_at+'.json';
            document.body.appendChild(link);link.click();link.remove();
            setTimeout(function(){URL.revokeObjectURL(url);},10000);
        });
    }
    return next().catch(function(error) {
        ui.addNotification(null,E('p',{},'PPE 完整导出失败：'+String(error)));
    }).finally(function(){button.disabled=false;});
}
function ppeCountText(entries) {
    var m = ppeCurrentMeta || {}; entries = entries || [];
    if (m.available === false) return 'PPE 读取失败：'+(m.error || 'unknown');
    var total = m.total === undefined ? entries.length : m.total;
    var text = total+' flows · BND '+(m.bound||0)+' / UNB '+(m.unbound||0)+
        ' · IPv4 '+(m.ipv4||0)+' / IPv6 '+(m.ipv6||0);
    if (m.captured_at) text += ' · 快照 '+new Date(m.captured_at*1000).toLocaleTimeString()+
        ' / '+Math.max(0,Math.floor(Date.now()/1000-m.captured_at))+' 秒前';
    else text += ' · 快照时间未知';
    if (m.truncated) text += ' · 后端已截断：加载 '+entries.length+'/'+total+
        '；筛选只覆盖已加载条目，请用完整导出读取全部记录';
    if (m.flow_stats_available !== true) text += ' · 硬件计数'+
        (m.flow_stats_available === false ? '不可用' : '支持情况未知')+'，0不代表无卸载';
    return text+' · 表格按页显示，完整导出包含全部记录 · 逐行读取，非原子快照';
}
