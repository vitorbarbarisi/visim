#!/usr/bin/env python3
"""
Helper script to open webview windows in separate processes
This solves the threading issue with pywebview
"""

import webview
import sys

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python webview_helper.py <title> <url>")
        sys.exit(1)
    
    title = sys.argv[1]
    url = sys.argv[2]
    
    try:
        webview.create_window(
            title=title,
            url=url,
            width=800,
            height=600,
            resizable=True,
            minimizable=True,
            maximizable=True
        )
        webview.start()
    except Exception as e:
        print(f"Error creating webview window: {e}")
        sys.exit(1)
