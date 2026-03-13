import hashlib,json,time

LOG="agents/synthesis/logs/traces.json"

def trace(action,data):

 record={
  "action":action,
  "data":data,
  "time":time.time()
 }

 encoded=json.dumps(record).encode()
 record["proof"]=hashlib.sha256(encoded).hexdigest()

 with open(LOG,"a") as f:
  f.write(json.dumps(record)+"\n")

 return record["proof"]
