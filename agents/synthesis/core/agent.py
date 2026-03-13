import subprocess
import time
from tracer import trace

LAST_HASH = None

def get_repo_hash():
    try:
        return subprocess.check_output(
            "git rev-parse HEAD", shell=True
        ).decode().strip()
    except:
        return None

def observe():
    trace("observe","checking repo state")
    return get_repo_hash()

def call_llm():
    # SOLO se ejecuta cuando hay cambios
    trace("llm","analysis requested")
    print("LLM analysis would run here (Groq)")

def improve():
    subprocess.run("git add .", shell=True)
    subprocess.run('git commit -m "agent improvement" || true', shell=True)
    subprocess.run("git push", shell=True)

def loop():

    global LAST_HASH

    while True:

        current = observe()

        if LAST_HASH is None:
            LAST_HASH = current

        elif current != LAST_HASH:

            trace("change_detected","repo updated")

            call_llm()
            improve()

            LAST_HASH = current

        time.sleep(30)

if __name__ == "__main__":
    loop()
