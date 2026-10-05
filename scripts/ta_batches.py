#!/usr/bin/env python3
"""Build stage-2 (title/abstract) batches for the AI stand-ins from the stage-1 result.
Usage: python3 scripts/ta_batches.py --merged <ti_ai_merged.csv> --master <records_master.csv> --out-dir /tmp/ta_screen/batches --size 40
Takes every record whose ai_final (or ai_merged when no Opus pass) is ADVANCE_TO_ABSTRACT, plus human ADVANCE decisions if a
--human-advances CSV (record_id column) is given. Batch CSVs carry record_id,title,journal,year,abstract (abstracts are copyright
text: keep the batches in /tmp, never in the repository)."""
import argparse, csv, os
ap=argparse.ArgumentParser(); ap.add_argument("--merged",required=True); ap.add_argument("--master",required=True)
ap.add_argument("--out-dir",required=True); ap.add_argument("--size",type=int,default=40); ap.add_argument("--human-advances",default=None)
a=ap.parse_args(); os.makedirs(a.out_dir,exist_ok=True)
m={r["record_id"]:r for r in csv.DictReader(open(a.master,encoding="utf-8"))}
adv=[]
for r in csv.DictReader(open(a.merged,encoding="utf-8")):
    fin=r.get("ai_final") or r.get("ai_merged")
    if fin=="ADVANCE_TO_ABSTRACT": adv.append(r["record_id"])
if a.human_advances:
    for r in csv.DictReader(open(a.human_advances,encoding="utf-8")): adv.append(r["record_id"])
adv=sorted(set(adv)); n=0; noabs=0
for i in range(0,len(adv),a.size):
    n+=1
    with open(os.path.join(a.out_dir,f"batch_{n:03d}.csv"),"w",encoding="utf-8",newline="") as f:
        w=csv.writer(f); w.writerow(["record_id","title","journal","year","abstract"])
        for rid in adv[i:i+a.size]:
            x=m[rid]; ab=x.get("abstract","") or ""
            if not ab.strip(): noabs+=1
            w.writerow([rid,x["title"],x["journal"],x["year"],ab])
print("advanced",len(adv),"batches",n,"without abstract",noabs)
