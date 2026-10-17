from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import shutil
import subprocess
import sys
import threading
import time
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib.error import URLError
from urllib.request import urlopen

from dotenv import load_dotenv

from window import EVIWindow


LOGGER = logging.getLogger("evi.desktop")


def _application_root() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root).resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


ROOT = _application_root()
EXTERNAL_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else ROOT
CONFIG_PATH = ROOT / "desktop" / "config.json"
STARTUP_LOG = EXTERNAL_ROOT / "EVI_startup.log" if getattr(sys, "frozen", False) else ROOT / "desktop" / "EVI_startup.log"


def _redact(value: str) -> str:
    redacted = value
    for key, secret in os.environ.items():
        if secret and (key == "DB_URL" or any(marker in key.upper() for marker in ("KEY", "SECRET", "PASSWORD", "TOKEN"))):
            redacted = redacted.replace(secret, "[REDACTED]")
    redacted = re.sub(r"postgres(?:ql)?://[^\s'\"]+", "[REDACTED_DATABASE_URL]", redacted, flags=re.IGNORECASE)
    return redacted


class _RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return _redact(super().format(record))


def _configure_logging() -> None:
    handlers: List[logging.Handler] = []
    try:
        STARTUP_LOG.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(STARTUP_LOG, encoding="utf-8"))
    except OSError:
        pass
    if getattr(sys, "stdout", None) is not None:
        handlers.append(logging.StreamHandler(sys.stdout))
    formatter = _RedactingFormatter("[%(asctime)s] %(levelname)s %(message)s")
    for handler in handlers:
        handler.setFormatter(formatter)
    logging.basicConfig(
        level=logging.INFO,
        handlers=handlers or None,
        force=True,
    )


class LocalRuntime:
    def __init__(self, config: Dict[str, Any], mode: str) -> None:
        self.config = config
        self.mode = mode
        self.processes: List[tuple[str, subprocess.Popen]] = []
        self.stopping = False

    def start(self) -> None:
        backend = self.config["backend"]
        frontend = self.config["frontend"]
        self._load_runtime_environment(backend)
        self._validate_runtime_prerequisites(backend, frontend)
        if self.mode == "packaged":
            self._validate_production_frontend(frontend)
        backend_url = f"http://{backend['host']}:{backend['port']}/"
        frontend_url = f"http://{frontend['host']}:{frontend['port']}/"

        _status("Starting backend...")
        self._start_backend(backend)
        self._wait_for_url("backend", backend_url)
        _status(f"Backend ready: {backend_url}")

        _status("Starting frontend...")
        if self.mode == "packaged":
            self._start_frontend(frontend, preview=True)
        else:
            self._start_frontend(frontend, preview=False)
        self._wait_for_url("frontend", frontend_url)
        _status(f"Frontend ready: {frontend_url}")

        _status("EVI is ready.")

    def run_until_stopped(self) -> None:
        while not self.stopping:
            for name, process in self.processes:
                exit_code = process.poll()
                if exit_code is not None:
                    raise RuntimeError(f"{name} process exited with code {exit_code}.")
            time.sleep(0.5)

    def stop(self) -> None:
        if self.stopping:
            return
        self.stopping = True
        _status("Shutting down...")
        for name, process in reversed(self.processes):
            self._stop_process(name, process)
        self.processes.clear()

    def _stop_process(self, name: str, process: subprocess.Popen) -> None:
        if process.poll() is not None:
            _status(f"{name.capitalize()} stopped.")
            return
        LOGGER.info("Stopping %s process", name)
        shutdown_timeout = float(self.config.get("shutdown_timeout_seconds", 10))
        try:
            if os.name == "nt":
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                process.terminate()
            process.wait(timeout=shutdown_timeout)
            _status(f"{name.capitalize()} stopped.")
            return
        except (OSError, subprocess.TimeoutExpired):
            pass

        if os.name == "nt":
            LOGGER.warning("Force stopping %s process tree", name)
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            LOGGER.warning("Force stopping %s process", name)
            process.kill()
            process.wait()
        _status(f"{name.capitalize()} stopped.")

    def _start_backend(self, backend: Dict[str, Any]) -> None:
        if getattr(sys, "frozen", False):
            command = [
                sys.executable,
                "--evi-backend-child",
                "--app",
                backend["app"],
                "--host",
                backend["host"],
                "--port",
                str(backend["port"]),
            ]
        else:
            python = os.environ.get("EVI_PYTHON") or _python_executable()
            command = [
                python,
                "-m",
                "uvicorn",
                backend["app"],
                "--host",
                backend["host"],
                "--port",
                str(backend["port"]),
            ]
        self._start_process(
            "backend",
            command,
            self._backend_directory(backend),
            env=self._backend_environment(backend),
        )

    def _validate_runtime_prerequisites(self, backend: Dict[str, Any], frontend: Dict[str, Any]) -> None:
        backend_directory = self._backend_directory(backend)
        frontend_directory = self._frontend_directory(frontend)
        if not backend_directory.is_dir() and not getattr(sys, "frozen", False):
            raise RuntimeError(f"Backend directory is missing: {backend_directory}")
        if not frontend_directory.is_dir():
            raise RuntimeError(f"Frontend directory is missing: {frontend_directory}")
        if not _database_url_available(backend_directory):
            raise RuntimeError("PostgreSQL configuration is missing: set DB_URL or add DB_URL to backend/.env")

    def _start_frontend(self, frontend: Dict[str, Any], preview: bool) -> None:
        if preview and getattr(sys, "frozen", False):
            command = [
                sys.executable,
                "--evi-frontend-child",
                "--directory",
                str(self._frontend_dist_directory(frontend)),
                "--host",
                frontend["host"],
                "--port",
                str(frontend["port"]),
            ]
            cwd = EXTERNAL_ROOT
            environment = os.environ.copy()
        else:
            command = _npm_command() + ["run", "preview" if preview else "dev", "--", "--host", frontend["host"]]
            if preview:
                command.extend(["--port", str(frontend["port"])])
            cwd = self._frontend_directory(frontend)
            environment = self._frontend_environment(frontend, self.config["backend"])
        self._start_process(
            "frontend",
            command,
            cwd,
            env=environment,
        )

    @staticmethod
    def _validate_production_frontend(frontend: Dict[str, Any]) -> None:
        dist_directory = LocalRuntime._frontend_dist_directory(frontend)
        index_file = dist_directory / "index.html"
        if not index_file.is_file():
            raise RuntimeError(
                f"Production frontend is missing: {index_file}. Run 'cd frontend; npm run build' first."
            )

    @staticmethod
    def _frontend_dist_directory(frontend: Dict[str, Any]) -> Path:
        dist_directory = Path(frontend["dist_directory"])
        return dist_directory if dist_directory.is_absolute() else ROOT / dist_directory

    def _start_process(self, name: str, command: List[str], cwd: Path, env: Dict[str, str] | None = None) -> None:
        LOGGER.info("Starting %s: %s", name, " ".join(command))
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
        except OSError as error:
            raise RuntimeError(f"Unable to start the {name} process: {error}") from error
        self.processes.append((name, process))

    @staticmethod
    def _frontend_directory(frontend: Dict[str, Any]) -> Path:
        directory = Path(frontend["directory"])
        return directory if directory.is_absolute() else ROOT / directory

    @staticmethod
    def _backend_directory(backend: Dict[str, Any]) -> Path:
        directory = Path(backend["directory"])
        resolved = directory if directory.is_absolute() else (EXTERNAL_ROOT if getattr(sys, "frozen", False) else ROOT) / directory
        if getattr(sys, "frozen", False) and not resolved.is_dir():
            return EXTERNAL_ROOT
        return resolved

    @staticmethod
    def _backend_environment(backend: Dict[str, Any]) -> Dict[str, str]:
        environment = os.environ.copy()
        return environment

    @staticmethod
    def _load_runtime_environment(backend: Dict[str, Any]) -> None:
        if getattr(sys, "frozen", False):
            env_path = EXTERNAL_ROOT / ".env"
        else:
            env_path = LocalRuntime._backend_directory(backend) / ".env"
        if env_path.is_file():
            load_dotenv(dotenv_path=env_path, override=False)

    def _wait_for_url(self, name: str, url: str) -> None:
        timeout = float(self.config.get("startup_timeout_seconds", 30))
        interval = float(self.config.get("poll_interval_seconds", 0.5))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            process = next(process for process_name, process in self.processes if process_name == name)
            if process.poll() is not None:
                raise RuntimeError(f"{name} process exited with code {process.returncode}.")
            try:
                with urlopen(url, timeout=2) as response:
                    if response.status < 500:
                        return
            except (OSError, URLError):
                time.sleep(interval)
        raise TimeoutError(f"{name.capitalize()} was unavailable after {timeout:g} seconds: {url}")

    def _frontend_environment(self, frontend: Dict[str, Any], backend: Dict[str, Any]) -> Dict[str, str]:
        environment = os.environ.copy()
        backend_url = f"http://{backend['host']}:{backend['port']}"
        environment["VITE_API_URL"] = environment.get("VITE_API_URL", backend_url)
        return environment


def _python_executable() -> str:
    candidates = [
        ROOT / ".venv" / "Scripts" / "python.exe",
        ROOT / "venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    if sys.executable:
        return sys.executable
    raise RuntimeError("No Python interpreter was found. Set EVI_PYTHON to a valid Python executable.")


def _npm_command() -> List[str]:
    command = "npm.cmd" if os.name == "nt" else "npm"
    if shutil.which(command) is None:
        raise RuntimeError(f"Required frontend command was not found: {command}")
    return [command]


def _load_config() -> Dict[str, Any]:
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except FileNotFoundError as error:
        raise RuntimeError(f"Required configuration file is missing: {CONFIG_PATH}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Configuration file is invalid JSON: {CONFIG_PATH}") from error
    _validate_config(config)
    return config


def _validate_config(config: Dict[str, Any]) -> None:
    if config.get("mode", "development") not in {"development", "packaged"}:
        raise RuntimeError("Configuration mode must be 'development' or 'packaged'.")
    for section_name in ("backend", "frontend"):
        section = config.get(section_name)
        if not isinstance(section, dict):
            raise RuntimeError(f"Configuration section is missing: {section_name}")
        for key in ("host", "port"):
            if key not in section:
                raise RuntimeError(f"Configuration value is missing: {section_name}.{key}")
    if "directory" not in config["backend"]:
        raise RuntimeError("Configuration value is missing: backend.directory")
    if "app" not in config["backend"]:
        raise RuntimeError("Configuration value is missing: backend.app")
    if "directory" not in config["frontend"]:
        raise RuntimeError("Configuration value is missing: frontend.directory")
    if "dist_directory" not in config["frontend"]:
        raise RuntimeError("Configuration value is missing: frontend.dist_directory")


def _status(message: str) -> None:
    message = _redact(message)
    output = getattr(sys, "stdout", None)
    if output is not None:
        print(f"[EVI] {message}", flush=True)
    else:
        LOGGER.info("[EVI] %s", message)


def _database_url_available(backend_directory: Path) -> bool:
    return bool(os.environ.get("DB_URL"))


def _run_backend_child(app: str, host: str, port: int) -> int:
    if getattr(sys, "frozen", False):
        load_dotenv(dotenv_path=EXTERNAL_ROOT / ".env", override=False)
    import uvicorn

    uvicorn.run(app, host=host, port=port)
    return 0


class _FrontendHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, directory: str, **kwargs: Any) -> None:
        super().__init__(*args, directory=directory, **kwargs)

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        if code == 404:
            self.path = "/index.html"
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open(Path(self.directory) / "index.html", "rb") as index_file:
                self.wfile.write(index_file.read())
            return
        super().send_error(code, message, explain)


def _run_frontend_child(directory: str, host: str, port: int) -> int:
    handler = lambda *args, **kwargs: _FrontendHandler(*args, directory=directory, **kwargs)
    server = ThreadingHTTPServer((host, port), handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Start and supervise the local EVI runtime.")
    parser.add_argument("--mode", choices=("development", "packaged"), help="Override the mode in desktop/config.json.")
    parser.add_argument("--evi-backend-child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--app", default="app.main:app", help=argparse.SUPPRESS)
    parser.add_argument("--host", default="127.0.0.1", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=8000, help=argparse.SUPPRESS)
    parser.add_argument("--evi-frontend-child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--directory", default="", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.evi_backend_child:
        return _run_backend_child(args.app, args.host, args.port)
    if args.evi_frontend_child:
        return _run_frontend_child(args.directory, args.host, args.port)
    runtime: LocalRuntime | None = None
    window: EVIWindow | None = None

    try:
        config = _load_config()
        default_mode = "packaged" if getattr(sys, "frozen", False) else config.get("mode", "development")
        mode = args.mode or default_mode
        runtime = LocalRuntime(config, mode)

        def request_stop(signum: int, _frame: Any) -> None:
            LOGGER.info("Received signal %s", signum)
            runtime.stop()
            if window is not None:
                window.close()

        signal.signal(signal.SIGINT, request_stop)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, request_stop)

        runtime.start()
        frontend = config["frontend"]
        frontend_url = f"http://{frontend['host']}:{frontend['port']}/"
        _status("Starting desktop window...")
        window = EVIWindow(frontend_url, config)
        monitor_error: List[Exception] = []

        def monitor_runtime() -> None:
            try:
                runtime.run_until_stopped()
            except Exception as error:
                monitor_error.append(error)
                _status(f"Runtime stopped: {error}")
                try:
                    window.close()
                except Exception:
                    LOGGER.exception("Unable to close the EVI window after a child process failure")

        monitor = threading.Thread(target=monitor_runtime, name="evi-runtime-monitor", daemon=True)
        monitor.start()
        _status("EVI is ready.")
        window.run()
        if monitor_error:
            raise monitor_error[0]
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as error:
        LOGGER.exception("EVI startup/runtime failure")
        _status(f"Startup failed: {error}")
        return 1
    finally:
        if runtime is not None:
            runtime.stop()


if __name__ == "__main__":
    _configure_logging()
    raise SystemExit(main())
