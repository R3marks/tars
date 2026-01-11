import subprocess
import time
import requests
import atexit
import logging

logger = logging.getLogger("uvicorn.error")

class LlamaServerProcess:
    def __init__(
        self,
        llama_server_path: str,
        models_dir: str,
        models_config: str,
        port: int = 8080,
    ):
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}"
        self.proc: subprocess.Popen | None = None

        self.cmd = [
            llama_server_path,
            "--models-dir", models_dir,
            "--models-preset", models_config,
            "--no-models-autoload",
            "--models-max", "1",
            "--port", str(port),
        ]

        atexit.register(self.shutdown)

    def start(self):
        if self.proc:
            return

        logger.info("🚀 Starting llama-server")
        self.proc = subprocess.Popen(
            self.cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        self._wait_for_health()

    def _wait_for_health(self, timeout: int = 30):
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = requests.get(f"{self.base_url}/health", timeout=1)
                if r.status_code == 200:
                    logger.info("✅ llama-server healthy")
                    return
            except Exception:
                time.sleep(0.5)

        raise RuntimeError("❌ llama-server failed to start")

    def shutdown(self):
        if not self.proc:
            return

        logger.info("🛑 Shutting down llama-server")
        try:
            subprocess.run(
                ["taskkill", "/PID", str(self.proc.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        finally:
            self.proc = None
