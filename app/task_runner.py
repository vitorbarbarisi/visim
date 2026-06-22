"""Run blocking work off the Tk main thread; deliver results on it via a polled queue.

Tkinter is not thread-safe: worker threads must never touch widgets. They push
result callbacks onto a queue that the main thread drains on a timer, so all UI
mutations happen on the main loop while blocking I/O runs in the background.
"""
import queue
import threading
from typing import Any, Callable, Optional


class TaskRunner:
    def __init__(self, widget, poll_ms: int = 30):
        self._widget = widget
        self._queue: "queue.Queue" = queue.Queue()
        self._poll_ms = poll_ms
        self._widget.after(self._poll_ms, self._drain)

    def submit(self, work: Callable[[], Any],
               on_done: Optional[Callable[[Any], None]] = None,
               on_error: Optional[Callable[[Exception], None]] = None) -> None:
        """Run `work()` in a daemon thread; deliver its result to `on_done` on the
        main thread (or the exception to `on_error`)."""
        def runner():
            try:
                result = work()
            except Exception as exc:  # noqa: BLE001
                self._queue.put(("error", on_error, exc))
            else:
                self._queue.put(("done", on_done, result))

        threading.Thread(target=runner, daemon=True).start()

    def _drain(self) -> None:
        try:
            while True:
                _kind, callback, payload = self._queue.get_nowait()
                if callback is None:
                    continue
                try:
                    callback(payload)
                except Exception as e:  # noqa: BLE001
                    print(f"TaskRunner callback error: {e}")
        except queue.Empty:
            pass
        finally:
            try:
                self._widget.after(self._poll_ms, self._drain)
            except Exception:
                pass
