import subprocess,time
from tracer import trace

def observe():
 trace("observe","repo scan")

def plan():
 trace("plan","analysis")

def improve():

 subprocess.run("git add .",shell=True)
 subprocess.run('git commit -m "agent improvement" || true',shell=True)
 subprocess.run("git push",shell=True)

def loop():

 while True:

  observe()
  plan()
  improve()

  time.sleep(30)

if __name__=="__main__":
 loop()
