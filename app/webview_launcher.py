"""Launch external windows for stroke-order visualization."""
import os
import subprocess
import sys
import threading
import webbrowser
from typing import Dict


class WebviewLauncher:
    def __init__(self):
        self.opened: Dict[str, subprocess.Popen] = {}

    def open_webview(self, character: str, url: str) -> None:
        key = f"webview_{character}"
        if key in self.opened:
            print(f"Window for character {character} is already open")
            return
        helper_script = os.path.join(os.path.dirname(__file__), "webview_helper.py")
        print(f"Attempting to launch webview for {character}")
        print(f"Helper script path: {helper_script}")
        print(f"URL: {url}")
        try:
            process = subprocess.Popen(
                [sys.executable, helper_script, f"Caractere: {character}", url],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            self.opened[key] = process
            threading.Thread(
                target=self._monitor,
                args=(key, character, process, url),
                daemon=True,
            ).start()
        except Exception as e:
            print(f"Error creating webview subprocess: {e}")
            webbrowser.open(url)

    def _monitor(self, key: str, character: str,
                 process: subprocess.Popen, url: str) -> None:
        try:
            stdout, stderr = process.communicate(timeout=2)
            if process.returncode != 0:
                print(f"Webview process failed for {character}")
                print(f"Return code: {process.returncode}")
                if stderr:
                    print(f"Error output: {stderr}")
                webbrowser.open(url)
            else:
                print(f"Webview window opened successfully for character {character}")
        except subprocess.TimeoutExpired:
            print(f"Webview window for {character} is running")
            process.wait()
        except Exception as e:
            print(f"Error monitoring webview process: {e}")
        finally:
            self.opened.pop(key, None)

    def open_safari(self, url: str) -> None:
        try:
            applescript = f'''
            tell application "Safari"
                activate
                make new document with properties {{URL:"{url}"}}
                set bounds of front window to {{100, 100, 900, 700}}
            end tell
            '''
            subprocess.run(['osascript', '-e', applescript], check=True)
            print(f"Opened Safari window: {url}")
        except Exception as e:
            print(f"Error opening Safari window: {e}")
            webbrowser.open(url)
