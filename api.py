import os
import sys
import time
import json
import re
import socket
import ssl
import datetime
from urllib.request import urlopen, Request
from urllib.parse import quote, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="0x41 Reverse IP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TIMEOUT = 10
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def _get(url: str) -> str:
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", errors="ignore")

def resolve_target(target: str) -> tuple[str, str]:
    if target.startswith("http://") or target.startswith("https://"):
        host = urlparse(target).hostname or target
    else:
        host = target

    parts = host.split(".")
    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        return host, host

    try:
        ip = socket.gethostbyname(host)
        return ip, host
    except socket.gaierror as e:
        raise ValueError(f"'{host}' çözümlenemedi: {e}")

def ptr_lookup(ip: str) -> set[str]:
    try:
        host = socket.gethostbyaddr(ip)[0]
        return {host} if host else set()
    except Exception:
        return set()

def ssl_cert_domains(ip: str) -> set[str]:
    domains: set[str] = set()
    sni_list = list(ptr_lookup(ip)) + [""]
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    for sni in sni_list:
        try:
            with socket.create_connection((ip, 443), timeout=TIMEOUT) as sock:
                kwargs = {"server_hostname": sni} if sni else {}
                with ctx.wrap_socket(sock, **kwargs) as ssock:
                    der = ssock.getpeercert(binary_form=True)
                    if not der:
                        continue
                    raw = der.decode("latin-1")
                    found = re.findall(
                        r'([a-zA-Z0-9\*][a-zA-Z0-9\-]*(?:\.[a-zA-Z0-9\-]+)+\.[a-zA-Z]{2,})',
                        raw,
                    )
                    for d in found:
                        d = d.lstrip("*.").lower()
                        if "." in d and ".." not in d and len(d) > 4:
                            domains.add(d)
                    if domains:
                        break
        except Exception:
            pass
    return domains

def crtsh_lookup(ip: str) -> set[str]:
    domains: set[str] = set()
    queries = [ip]
    ptr = ptr_lookup(ip)
    queries.extend(ptr)

    for q in queries:
        try:
            url = f"https://crt.sh/?q={quote(q)}&output=json"
            data = json.loads(_get(url))
            for entry in data:
                name = entry.get("name_value", "")
                for d in name.split("\n"):
                    d = d.strip().lstrip("*.")
                    if d:
                        domains.add(d)
        except Exception:
            pass
        time.sleep(0.5)
    return domains

def hackertarget_lookup(ip: str) -> set[str]:
    domains: set[str] = set()
    try:
        url = f"https://api.hackertarget.com/reverseiplookup/?q={ip}"
        body = _get(url)
        if "error" in body.lower() or "API count" in body:
            return domains
        for line in body.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                domains.add(line)
    except Exception:
        pass
    return domains

def viewdns_lookup(ip: str) -> set[str]:
    domains: set[str] = set()
    try:
        url = f"https://viewdns.info/reverseip/?host={ip}&t=1"
        html = _get(url)
        matches = re.findall(r"<td>([a-zA-Z0-9._-]+\.[a-zA-Z]{2,})</td>", html)
        matches += re.findall(r'href=["\']https?://([a-zA-Z0-9._-]+\.[a-zA-Z]{2,})[/"\'?]', html)
        skip = {"viewdns.info", "google.com", "cloudflare.com"}
        for m in matches:
            m = m.strip()
            if m and m not in skip:
                domains.add(m)
    except Exception:
        pass
    return domains

def bing_lookup(ip: str) -> set[str]:
    domains: set[str] = set()
    try:
        url = f"https://www.bing.com/search?q=%22{ip}%22&count=50"
        html = _get(url)
        matches = re.findall(r'<cite[^>]*>https?://([a-zA-Z0-9._-]+\.[a-zA-Z]{2,})(?:[/<]|&)', html)
        if not matches:
            matches = re.findall(r'href="https?://([a-zA-Z0-9._-]+\.[a-zA-Z]{2,})(?:[/"?])', html)
        skip = {"bing.com", "microsoft.com", "msn.com", "live.com", "w3.org", "schema.org"}
        for m in matches:
            if m not in skip:
                domains.add(m)
    except Exception:
        pass
    return domains

def rapiddns_lookup(ip: str) -> set[str]:
    domains: set[str] = set()
    try:
        url = f"https://rapiddns.io/sameip/{ip}?full=1"
        html = _get(url)
        matches = re.findall(r'<td><a[^>]*>([a-zA-Z0-9._-]+\.[a-zA-Z]{2,})</a></td>', html)
        if not matches:
            matches = re.findall(r'<td>([a-zA-Z0-9._-]+\.[a-zA-Z]{2,})</td>', html)
        for m in matches:
            m = m.strip()
            if m:
                domains.add(m)
    except Exception:
        pass
    return domains

SOURCES = {
    "PTR": ptr_lookup,
    "SSL": ssl_cert_domains,
    "crt.sh": crtsh_lookup,
    "HackerTarget": hackertarget_lookup,
    "RapidDNS": rapiddns_lookup,
    "ViewDNS.info": viewdns_lookup,
    "Bing": bing_lookup,
}

@app.get("/api/lookup")
def api_lookup(target: str):
    try:
        ip, original = resolve_target(target)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    start = datetime.datetime.now()
    all_domains: set[str] = set()
    results: dict[str, list[str]] = {}
    
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fn, ip): name for name, fn in SOURCES.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                found = future.result()
            except Exception as e:
                found = set()
            results[name] = sorted(list(found))
            all_domains.update(found)
            
    elapsed = (datetime.datetime.now() - start).total_seconds()
    
    return {
        "target": original,
        "ip": ip,
        "sources": results,
        "all_domains": sorted(list(all_domains)),
        "total": len(all_domains),
        "elapsed_seconds": round(elapsed, 2)
    }

# Serve static files for frontend
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
