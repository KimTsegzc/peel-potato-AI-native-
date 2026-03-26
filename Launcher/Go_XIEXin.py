from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


DEFAULT_PORT = 8501
DEFAULT_HOST = "127.0.0.1"
START_TIMEOUT_SECONDS = 45
PID_TEMPLATE = "frontend-{port}.pid"
STDOUT_TEMPLATE = "frontend-{port}.out.log"
STDERR_TEMPLATE = "frontend-{port}.err.log"
LAUNCHER_LOG_NAME = "go_xiexin.log"
RUNTIME_DIR_NAME = ".streamlit"
APP_RELATIVE_PATH = Path("Gateway") / "Front" / "app.py"
CREATE_NO_WINDOW = 0x08000000


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resolve_repo_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def runtime_paths(repo_root: Path, port: int) -> dict[str, Path]:
    runtime_dir = repo_root / RUNTIME_DIR_NAME
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return {
        "runtime_dir": runtime_dir,
        "pid_file": runtime_dir / PID_TEMPLATE.format(port=port),
        "stdout_log": runtime_dir / STDOUT_TEMPLATE.format(port=port),
        "stderr_log": runtime_dir / STDERR_TEMPLATE.format(port=port),
        "launcher_log": runtime_dir / LAUNCHER_LOG_NAME,
    }


def configure_logging(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("go_xiexin")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def show_messagebox(title: str, message: str, error: bool = False) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        if error:
            messagebox.showerror(title, message, parent=root)
        else:
            messagebox.showinfo(title, message, parent=root)
        root.destroy()
    except Exception:
        return


def resolve_python(repo_root: Path, override: str = "") -> Path | None:
    if override:
        candidate = Path(override).expanduser().resolve()
        if candidate.exists():
            return candidate

    if not is_frozen():
        executable = Path(sys.executable)
        if executable.exists() and executable.name.lower() == "python.exe":
            return executable

    for env_name in (".venv311", ".venv", "venv", ".venv312", ".venv310"):
        candidate = repo_root / env_name / "Scripts" / "python.exe"
        if candidate.exists():
            return candidate

    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        candidate = Path(conda_prefix) / "python.exe"
        if candidate.exists():
            return candidate

    which_python = shutil.which("python")
    if which_python:
        return Path(which_python).resolve()

    return None


def write_pid(pid_file: Path, pid: int) -> None:
    pid_file.write_text(str(pid), encoding="ascii")


def read_pid(pid_file: Path) -> int | None:
    if not pid_file.exists():
        return None
    raw = pid_file.read_text(encoding="ascii", errors="ignore").strip()
    if raw.isdigit():
        return int(raw)
    return None


def taskkill_pid(pid: int, logger: logging.Logger) -> bool:
    result = subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        check=False,
    )
    success = result.returncode == 0
    logger.info("taskkill pid=%s success=%s stdout=%s stderr=%s", pid, success, result.stdout.strip(), result.stderr.strip())
    return success


def find_listening_pids(port: int) -> list[int]:
    result = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []

    pids: set[int] = set()
    port_suffix = f":{port}"
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        proto, local_address, _, state, pid_text = parts[:5]
        if proto.upper() != "TCP":
            continue
        if not local_address.endswith(port_suffix):
            continue
        if state.upper() != "LISTENING":
            continue
        if pid_text.isdigit():
            pids.add(int(pid_text))
    return sorted(pids)


def stop_existing_frontend(port: int, pid_file: Path, logger: logging.Logger) -> None:
    killed_any = False
    pid_from_file = read_pid(pid_file)
    if pid_from_file:
        killed_any = taskkill_pid(pid_from_file, logger) or killed_any

    for pid in find_listening_pids(port):
        killed_any = taskkill_pid(pid, logger) or killed_any

    if pid_file.exists():
        pid_file.unlink(missing_ok=True)

    if killed_any:
        time.sleep(1.0)


def is_http_ready(url: str, timeout_seconds: float = 2.0) -> bool:
    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            return 200 <= getattr(response, "status", 0) < 500
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def wait_for_frontend(url: str, process: subprocess.Popen[bytes], timeout_seconds: int, logger: logging.Logger) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if process.poll() is not None:
            logger.error("frontend process exited early with code %s", process.returncode)
            return False
        if is_http_ready(url):
            logger.info("frontend ready at %s", url)
            return True
        time.sleep(0.5)
    logger.error("frontend did not become ready within %s seconds", timeout_seconds)
    return False


def open_browser(url: str, logger: logging.Logger) -> None:
    opened = webbrowser.open(url, new=2)
    logger.info("browser open requested url=%s opened=%s", url, opened)


def read_log_tail(log_path: Path, max_chars: int = 2000) -> str:
    if not log_path.exists():
        return ""
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def start_frontend(repo_root: Path, port: int, python_override: str, launch_browser: bool) -> int:
    paths = runtime_paths(repo_root, port)
    logger = configure_logging(paths["launcher_log"])
    app_path = repo_root / APP_RELATIVE_PATH

    logger.info("launcher start requested port=%s repo_root=%s frozen=%s", port, repo_root, is_frozen())

    if not app_path.exists():
        message = f"Frontend app not found: {app_path}"
        logger.error(message)
        show_messagebox("Go_XIEXin", message, error=True)
        return 1

    python_path = resolve_python(repo_root, override=python_override)
    if python_path is None:
        message = "No Python interpreter was found. Create the project venv or pass --python."
        logger.error(message)
        show_messagebox("Go_XIEXin", message, error=True)
        return 1

    frontend_url = f"http://{DEFAULT_HOST}:{port}"
    if is_http_ready(frontend_url):
        logger.info("frontend already healthy, reusing existing instance")
        if launch_browser:
            open_browser(frontend_url, logger)
        return 0

    stop_existing_frontend(port, paths["pid_file"], logger)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    logger.info("starting streamlit with python=%s app=%s", python_path, app_path)
    with paths["stdout_log"].open("ab") as stdout_handle, paths["stderr_log"].open("ab") as stderr_handle:
        process = subprocess.Popen(
            [
                str(python_path),
                "-m",
                "streamlit",
                "run",
                str(app_path),
                "--server.headless",
                "true",
                "--server.port",
                str(port),
            ],
            cwd=repo_root,
            env=env,
            stdout=stdout_handle,
            stderr=stderr_handle,
            creationflags=CREATE_NO_WINDOW,
        )

    write_pid(paths["pid_file"], process.pid)
    logger.info("frontend process started pid=%s", process.pid)

    if not wait_for_frontend(frontend_url, process, START_TIMEOUT_SECONDS, logger):
        stderr_tail = read_log_tail(paths["stderr_log"])
        stdout_tail = read_log_tail(paths["stdout_log"])
        details = stderr_tail or stdout_tail or "No startup logs were captured."
        message = (
            "Go_XIEXin could not start the frontend.\n\n"
            f"Logs: {paths['stderr_log']}\n\n"
            f"Recent output:\n{details}"
        )
        show_messagebox("Go_XIEXin", message, error=True)
        return 1

    if launch_browser:
        open_browser(frontend_url, logger)

    return 0


def stop_frontend(repo_root: Path, port: int) -> int:
    paths = runtime_paths(repo_root, port)
    logger = configure_logging(paths["launcher_log"])
    logger.info("launcher stop requested port=%s", port)
    stop_existing_frontend(port, paths["pid_file"], logger)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start or stop xiexin-da-agent.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--python", default="", help="Optional python.exe override.")
    parser.add_argument("--stop", action="store_true", help="Stop the running frontend for the selected port.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser after startup.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = resolve_repo_root()
    if args.stop:
        return stop_frontend(repo_root, args.port)
    return start_frontend(
        repo_root=repo_root,
        port=args.port,
        python_override=args.python,
        launch_browser=not args.no_browser,
    )


if __name__ == "__main__":
    raise SystemExit(main())