#!/usr/bin/env python3
"""Write the stage-1 conflict records (two AI stand-ins disagreed) into blind batches for a third read.
Usage: python3 scripts/ti_conflict_batches.py --merged /tmp/ti_screen/merge/ti_ai_merged.csv --out-dir /tmp/ti_screen/conflicts --size 100
Each batch CSV has record_id,title,journal,year,source_database only (no AI columns)."""
import argparse, csv, os
ap=argparse.ArgumentParser(); ap.add_argument("--merged",required=True); ap.add_argument("--out-dir",required=True); ap.add_argument("--size",type=int,default=100); ap.add_argument("--exclude-done",default=None,help="dir of batch_*.json already adjudicated; skip those record_ids"); ap.add_argument("--start",type=int,default=1,help="first batch number to write")
a=ap.parse_args(); os.makedirs(a.out_dir,exist_ok=True)
done=set()
if a.exclude_done:
    import glob,json,re
    for f in glob.glob(os.path.join(a.exclude_done,"batch_*.json")):
        if re.fullmatch(r"batch_\d{3}\.json",os.path.basename(f)):
            for o in json.load(open(f)): done.add(o["record_id"])
rows=[r for r in csv.DictReader(open(a.merged,encoding="utf-8")) if r["ai_conflict"]=="TRUE" and r["ai_B_disposition"] and r["ai_C_disposition"] and r["record_id"] not in done]
rows.sort(key=lambda r:r["record_id"])
n=a.start-1
for i in range(0,len(rows),a.size):
    n+=1
    with open(os.path.join(a.out_dir,f"batch_{n:03d}.csv"),"w",encoding="utf-8",newline="") as f:
        w=csv.writer(f); w.writerow(["record_id","title","journal","year","source_database"])
        for r in rows[i:i+a.size]: w.writerow([r["record_id"],r["title"],r["journal"],r["year"],r["source_database"]])
print("conflicts",len(rows),"batches",n)
