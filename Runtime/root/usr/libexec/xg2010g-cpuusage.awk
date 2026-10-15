# Pure /proc/stat delta calculation. Guest times overlap user/nice: exclude them.
$1 == "__SECOND__" { part=1; next }
$1 ~ /^cpu[0-9]*$/ {
    k=$1; t=0
    for (i=2;i<=9 && i<=NF;i++) t+=$i
    if (!part) {
        keys[n++]=k; total[k]=t; usr[k]=$2+$3; sys[k]=$4; irq[k]=$7; soft[k]=$8; idle[k]=$5+$6
    } else {
        dt[k]=t-total[k]; du[k]=$2+$3-usr[k]; ds[k]=$4-sys[k]; di[k]=$7-irq[k]; dq[k]=$8-soft[k]; dd[k]=$5+$6-idle[k]
        valid[k]=(dt[k]>0 && du[k]>=0 && ds[k]>=0 && di[k]>=0 && dq[k]>=0 && dd[k]>=0)
    }
}
END {
    if (!valid["cpu"]) exit 2
    count=0; cores=""; label=""
    u=100*du["cpu"]/dt["cpu"]; sy=100*ds["cpu"]/dt["cpu"]; iq=100*di["cpu"]/dt["cpu"]; sq=100*dq["cpu"]/dt["cpu"]
    label=sprintf("USR: %.0f%% SYS(system+IRQ+softirq): %.0f%%",u,sy+iq+sq)
    for(i=0;i<n;i++) {
        k=keys[i]; if(k=="cpu")continue
        if(!valid[k])exit 2
        busy=100*(dt[k]-dd[k])/dt[k]; if(busy<0 || busy>100.01)exit 2
        label=label sprintf(" | %s %.0f%%",toupper(k),busy)
        cores=cores sprintf("%s{\"name\":\"%s\",\"busy\":%.3f}",(count++ ? ",":""),k,busy)
    }
    if (!count)exit 2
    printf "{\"cpuusage\":\"%s\",\"busy\":%.3f,\"user\":%.3f,\"system\":%.3f,\"irq\":%.3f,\"softirq\":%.3f,\"cores\":[%s]}",label,100*(dt["cpu"]-dd["cpu"])/dt["cpu"],u,sy,iq,sq,cores
}
