import subprocess
import time
import requests
import signal
import sys
import json

# ==============================
# CONFIG
# ==============================

LLAMA_SERVER_PATH = r"T:/Code/Repos/llama.cpp/build/bin/Release/llama-server.exe"
MODELS_PATH = r"T:/Models"
MODEL_CONFIG = r"T:/Code/Apps/Tars/model-configs.ini"
PORT = 8080

BASE_URL = f"http://127.0.0.1:{PORT}"

# ==============================
# GLOBAL STATE
# ==============================

MODEL_INDEX = {}        # {0: "Qwen3-4B-Instruct-2507-Q6_K", ...}
CURRENT_MODEL = None

# ==============================
# SERVER CONTROL
# ==============================

def start_llama_server():
    cmd = [
        LLAMA_SERVER_PATH,
        "--models-dir", MODELS_PATH,
        "--models-preset", MODEL_CONFIG,
        "--models-max", "2",
        "--no-models-autoload",
        "--port", str(PORT),
    ]

    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

def kill_process_tree(proc):
    subprocess.run(
        ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_server(timeout=30):
    url = f"{BASE_URL}/health"
    start = time.time()

    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                return
        except requests.exceptions.RequestException:
            time.sleep(0.5)

    raise RuntimeError("❌ llama-server did not start in time")

# ==============================
# MODEL MANAGEMENT
# ==============================

def get_models():
    global MODEL_INDEX

    r = requests.get(f"{BASE_URL}/models", timeout=5)
    r.raise_for_status()

    data = r.json()["data"]
    MODEL_INDEX = {}

    print("\n📦 Available models:")
    for i, m in enumerate(data):
        model_id = m["id"]
        status = m["status"]["value"]
        MODEL_INDEX[i] = model_id
        print(f"  [{i}] {model_id} ({status})")

    return MODEL_INDEX


def load_model(model_name):
    global CURRENT_MODEL

    print(f"🚀 Loading model: {model_name}")
    start = time.time()

    r = requests.post(
        f"{BASE_URL}/models/load",
        json={"model": model_name},
        timeout=300,
    )
    print(r.json())
    r.raise_for_status()
    CURRENT_MODEL = model_name
    print(f"✅ Model {CURRENT_MODEL} loaded in {time.time() - start:.2f}s")


def unload_model(model_name):
    global CURRENT_MODEL

    print(f"🧹 Unloading model: {model_name}")
    start = time.time()

    r = requests.post(
        f"{BASE_URL}/models/unload",
        json={"model": model_name},
        timeout=300,
    )
    r.raise_for_status()

    if CURRENT_MODEL == model_name:
        CURRENT_MODEL = None

    print(f"✅ Model unloaded in {time.time() - start:.2f}s")

def wait_for_model_to_load():
    url = f"{BASE_URL}/models"
    start = time.time()

    is_current_model_loaded = False

    while not is_current_model_loaded:
        r = requests.get(url, timeout=5)
        r.raise_for_status()

        data = r.json()["data"]

        model_data = data[20]
        status = model_data["status"]["value"]

        if status == "loaded":
            break
        print(f"{CURRENT_MODEL} is in {status} state")
        time.sleep(3)




# ==============================
# STREAMED CHAT
# ==============================


def stream_chat(messages):
    if not CURRENT_MODEL:
        print("⚠️  No model loaded")
        return ""

    wait_for_model_to_load()

    assistant_text = ""
    completion_tokens = 0
    start = time.time()

    with requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json={
            "model": CURRENT_MODEL,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1024,
            "stream": True,
        },
        stream=True,
        timeout=300,
    ) as r:
        r.raise_for_status()
        print("\nAssistant:", end=" ", flush=True)

        for raw_line in r.iter_lines(decode_unicode=True):
            if not raw_line:
                continue

            if not raw_line.startswith("data:"):
                continue

            data = raw_line[5:].strip()

            if data == "[DONE]":
                break

            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue

            delta = chunk["choices"][0]["delta"].get("content")
            if delta:
                assistant_text += delta
                completion_tokens += 1
                print(delta, end="", flush=True)

    elapsed = time.time() - start
    tps = completion_tokens / elapsed if elapsed > 0 else 0

    print(
        f"\n\n⏱️  {completion_tokens} tokens in {elapsed:.2f}s "
        f"(≈ {tps:.2f} tok/s)"
    )

    return assistant_text

# ==============================
# CHAT LOOP
# ==============================

def chat_loop():
    messages = []

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() in {"exit", "quit"}:
            break

        if user_input.lower() == "models":
            get_models()
            continue

        if user_input.lower().startswith(("load model", "switch model")):
            try:
                idx = int(user_input.split()[-1])
                load_model(MODEL_INDEX[idx])
            except Exception:
                print("❌ Invalid model index")
            continue

        if user_input.lower().startswith("unload model"):
            try:
                idx = int(user_input.split()[-1])
                unload_model(MODEL_INDEX[idx])
            except Exception:
                print("❌ Invalid model index")
            continue

        messages.append({"role": "user", "content": user_input})
        assistant = stream_chat(messages)
        messages.append({"role": "assistant", "content": assistant})

# ==============================
# MAIN
# ==============================

def main():
    print("🚀 Starting llama-server...")
    proc = start_llama_server()

    try:
        wait_for_server()
        get_models()

        # auto-load first model
        load_model(MODEL_INDEX[20])

        print("\n💬 Chat ready")
        print("Commands: models | load model N | unload model N | exit")
        chat_loop()

    finally:
        print("\n🛑 Shutting down llama-server...")
        kill_process_tree(proc)

if __name__ == "__main__":
    main()
