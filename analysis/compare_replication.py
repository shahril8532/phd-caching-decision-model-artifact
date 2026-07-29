# compare_replication.py -- reproduces the v1.3.0 replication agreement figures.
# Usage: python3 compare_replication.py   (expects data/ and data/rerun/ beside it)
# -*- coding: utf-8 -*-
import csv, glob, os, numpy as np, openpyxl
from scipy import stats
BASE="/sessions/vibrant-sleepy-cannon/mnt/PhD 2027/"
A=0.05
def classify(sp):
    sp=np.array(sp,float); n=len(sp); M=sp.mean(); SD=sp.std(ddof=1)
    if SD==0: return ('CACHE' if M>0 else 'DO_NOT_CACHE'),M,SD,np.inf,0.0
    t=M/(SD/np.sqrt(n)); p=stats.t.sf(abs(t),n-1)
    d='CACHE' if (p<A and M>0) else ('DO_NOT_CACHE' if (p<A and M<0) else 'BORDERLINE')
    return d,M,SD,t,p

def load_rerun(sysdir):
    runs={}
    for f in sorted(glob.glob(BASE+sysdir+"/rerun/benchmark_run??.csv")):
        for r in csv.DictReader(open(f,encoding='utf-8-sig')):
            k=f"{r['model']}.{r['method']}"
            runs.setdefault(k,{'sp':[],'cold':[],'type':r['type']})
            runs[k]['sp'].append(float(r['speedup_pct']))
            runs[k]['cold'].append(float(r['avg_cold_ms']))
    return runs

def load_orig(xl):
    ws=openpyxl.load_workbook(BASE+xl,data_only=True)['Raw 10-Run Data']; out={}
    for r in ws.iter_rows(min_row=2,values_only=True):
        if r[0] is None: continue
        sp=[v for v in r[14:24] if v is not None]; cold=[v for v in r[4:14] if v is not None]
        if len(sp)<3: continue
        out[f"{r[1]}.{r[2]}"]={'sp':list(map(float,sp)),'cold':list(map(float,cold)),'type':r[3]}
    return out

SYS=[('iTeams','fasa_1_benchmark_iteams','iTeams_Phase2_Aggregated_Analysis.xlsx','8.4 -> 8.2'),
     ('Khairat','fasa_1_benchmark_khairat','Khairat_Phase2_Aggregated_Analysis.xlsx','8.4 -> 8.3'),
     ('VBS','fasa_1_benchmark_vbs','VBS_Phase2_Aggregated_Analysis.xlsx','8.4 -> 8.1')]

print("="*82)
print("CLASSIFICATION STABILITY UNDER A CHANGED PHP INTERPRETER")
print("="*82)
grand_agree=grand_n=0
for name,d,xl,ver in SYS:
    nu=load_rerun(d); og=load_orig(xl)
    common=[k for k in og if k in nu and len(nu[k]['sp'])>=3]
    agree=0; diffs=[]
    for k in common:
        do_,Mo,_,_,_=classify(og[k]['sp'])
        dn_,Mn,_,tn,pn=classify(nu[k]['sp'])
        if do_==dn_: agree+=1
        else: diffs.append((k,do_,dn_,Mo,Mn,pn))
    grand_agree+=agree; grand_n+=len(common)
    co=np.array([np.mean(og[k]['cold']) for k in common])
    cn=np.array([np.mean(nu[k]['cold']) for k in common])
    print(f"\n{name}  (PHP {ver})   n = {len(common)} relationships in both datasets")
    print(f"  classification agreement : {agree}/{len(common)} = {agree/len(common)*100:.1f}%")
    print(f"  mean cold access time    : {co.mean():.3f} ms  ->  {cn.mean():.3f} ms   ({(cn.mean()/co.mean()-1)*100:+.1f}%)")
    print(f"  mean speedup             : {np.mean([np.mean(og[k]['sp']) for k in common]):.1f}%  ->  "
          f"{np.mean([np.mean(nu[k]['sp']) for k in common]):.1f}%")
    from collections import Counter
    print("  new classification counts:", dict(Counter(classify(nu[k]['sp'])[0] for k in common)))
    for k,a,b,Mo,Mn,pn in diffs:
        print(f"    CHANGED  {k:28s} {a} -> {b}   mean {Mo:+.2f}% -> {Mn:+.2f}%  (p={pn:.4f})")
print("\n"+"="*82)
print(f"OVERALL AGREEMENT: {grand_agree}/{grand_n} = {grand_agree/grand_n*100:.1f}%")
print("="*82)
