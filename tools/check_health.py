# -*- coding: utf-8 -*-
"""
Health check probe for RASD AI (رَصْد AI) services.
Verifies Backend (port 8001) and Frontend (port 4000) readiness.
"""

import sys
import os
import time
import urllib.request

def check_url(url, timeout=2.0):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'RASD-AI-Probe/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.getcode() == 200
    except Exception:
        return False

def wait_for_services(backend_url="http://localhost:8001/", frontend_url="http://localhost:4000/", max_seconds=20):
    backend_ok = False
    frontend_ok = False
    active_frontend_port = 4000
    
    start = time.time()
    while time.time() - start < max_seconds:
        if not backend_ok:
            backend_ok = check_url(backend_url)
        if not frontend_ok:
            if check_url("http://localhost:4000/"):
                frontend_ok = True
                active_frontend_port = 4000
            elif check_url("http://localhost:4001/"):
                frontend_ok = True
                active_frontend_port = 4001
            
        if backend_ok and frontend_ok:
            break
            
        time.sleep(1.0)
        
    print(f"   [+] Backend API:        {'ONLINE (Port 8001)' if backend_ok else 'TIMEOUT / STILL INITIALIZING'}")
    print(f"   [+] Frontend Dashboard: {f'ONLINE (Port {active_frontend_port})' if frontend_ok else 'TIMEOUT / STILL INITIALIZING'}")
    
    try:
        port_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "active_port.txt")
        with open(port_file, "w") as f:
            f.write(str(active_frontend_port))
    except Exception:
        pass

    return backend_ok and frontend_ok

if __name__ == "__main__":
    b_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001/"
    f_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:4000/"
    max_sec = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    ok = wait_for_services(b_url, f_url, max_seconds=max_sec)
    sys.exit(0 if ok else 1)
