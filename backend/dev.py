from watchfiles import run_process
import subprocess

def start():
    subprocess.run(["python", "backend/main.py"])

if __name__ == "__main__":
    run_process('.', target=start)
