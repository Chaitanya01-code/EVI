from __future__ import annotations

import logging
import queue
import threading
from typing import Callable, Optional


logger = logging.getLogger(__name__)


class ControlIndicator:
    def __init__(self, on_stop: Callable[[], object], startup_timeout: float = 5.0) -> None:
        self._on_stop = on_stop
        self._startup_timeout = startup_timeout
        self._commands: queue.Queue[tuple[str, threading.Event, list[str]]] = queue.Queue()
        self._ready = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._startup_error: Optional[str] = None
        self._lock = threading.Lock()

    def show(self) -> None:
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._ready.clear()
                self._startup_error = None
                self._thread = threading.Thread(
                    target=self._run,
                    name="evi-computer-control-indicator",
                    daemon=True,
                )
                self._thread.start()
            thread = self._thread
        if not self._ready.wait(self._startup_timeout):
            raise RuntimeError("The computer control indicator did not start in time.")
        if self._startup_error:
            raise RuntimeError(self._startup_error)
        if thread is None or not thread.is_alive():
            raise RuntimeError("The computer control indicator is not running.")
        self._send("show")

    def hide(self) -> None:
        thread = self._thread
        if thread is None or not thread.is_alive() or not self._ready.is_set() or self._startup_error:
            return
        self._send("hide", wait=False)

    def _send(self, command: str, wait: bool = True) -> None:
        completed = threading.Event()
        errors: list[str] = []
        self._commands.put((command, completed, errors))
        if wait and not completed.wait(self._startup_timeout):
            raise RuntimeError(f"The computer control indicator did not {command} in time.")
        if wait and errors:
            raise RuntimeError(f"The computer control indicator could not {command}: {errors[0]}")

    def _run(self) -> None:
        try:
            import tkinter as tk

            root = tk.Tk()
            root.title("EVI Computer Control")
            root.geometry("270x78")
            root.resizable(False, False)
            root.attributes("-topmost", True)
            root.protocol("WM_DELETE_WINDOW", self._on_stop)
            container = tk.Frame(root, padx=10, pady=8)
            container.pack(fill="both", expand=True)
            label = tk.Label(container, text="EVI is controlling your computer", anchor="w")
            label.pack(fill="x", pady=(0, 6))
            stop_button = tk.Button(container, text="Stop", command=self._on_stop)
            stop_button.pack(anchor="e")
            root.withdraw()
            self._ready.set()

            def process_commands() -> None:
                while True:
                    try:
                        command, completed, errors = self._commands.get_nowait()
                    except queue.Empty:
                        break
                    try:
                        if command == "show":
                            root.deiconify()
                            root.lift()
                            root.attributes("-topmost", True)
                            if root.state() == "withdrawn":
                                raise RuntimeError("The indicator window remained hidden.")
                        elif command == "hide":
                            root.withdraw()
                    except Exception as error:
                        errors.append(str(error))
                        logger.exception("Unable to %s the EVI computer control indicator", command)
                    finally:
                        completed.set()
                    if errors and command == "show":
                        self._on_stop()
                root.after(40, process_commands)

            root.after(40, process_commands)
            root.mainloop()
        except Exception as error:
            self._startup_error = str(error)
            self._ready.set()
            logger.exception("EVI computer control indicator failed")
            self._on_stop()
