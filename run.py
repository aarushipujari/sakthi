import os
import socket
import sys
import threading
import time
import webbrowser
import uvicorn

# Candidate ports to try in sequence
PORTS_TO_TRY = [8000, 8080, 8050, 8888, 5000, 3000]

def find_available_port():
    for p in PORTS_TO_TRY:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", p))
            s.close()
            return p
        except Exception:
            s.close()
            continue
    return 8000

def open_browser(url):
    time.sleep(1.2)
    try:
        webbrowser.open(url)
    except Exception:
        pass

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    port = find_available_port()
    url = f"http://127.0.0.1:{port}"
    
    print("\n" + "=" * 65)
    print("  ALLOY ADDITION CALCULATOR — SAKTHI HACKATHON 2.0")
    print(f"  Serving at: {url}")
    print("  Opening browser automatically...")
    print("  Press Ctrl+C in this terminal to stop.")
    print("=" * 65 + "\n")

    threading.Thread(target=open_browser, args=(url,), daemon=True).start()
    uvicorn.run("backend.main:app", host="127.0.0.1", port=port, log_level="info")
