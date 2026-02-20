from fastapi import FastAPI, Query, HTTPException
from contextlib import asynccontextmanager
#from subprocess import run
import subprocess
import re
import os
import sqlite3
import requests
import socket
import ipaddress
from urllib.parse import urlparse

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "database.db")

def get_conn():
	conn = sqlite3.connect(DB_PATH)
	conn.row_factory = sqlite3.Row
	return conn

def init_db():
	conn = get_conn()
	cursor = conn.cursor()
	cursor.execute("""
		CREATE TABLE IF NOT EXISTS users (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			username TEXT NOT NULL UNIQUE,
			email TEXT NOT NULL UNIQUE
		)
	""")

	# Pequeño seed de ejemplo
	cursor.execute("SELECT COUNT(*) AS c FROM users")
	if cursor.fetchone()["c"] == 0:
		cursor.executemany(
			"INSERT INTO users (username, email) VALUEs (?, ?)",
			[
				("bautista", "bautista@syper.com"),
				("franco", "franco@syper.com"),
				("josue", "josue@syper.com")
			],
		)
	conn.commit()
	conn.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
	init_db()

	try:
		yield
	finally:
		pass

app = FastAPI(title="SyPeR Semgrep DEMO", lifespan=lifespan)

# ENDPOINTS

@app.get("/")
def saludo():
	return{"saludo":"Hola Semgrep"}

# ==========================
# 1) SQL Injection
# ==========================

@app.get("/users/search")
def search_users(username: str = Query(..., description="Username a buscar")):
	"""
	Endpoint vulnerable a SQLi
	Ejemplo de payload: ' OR '1'='1
	"""
	conn = get_conn()
	cursor = conn.cursor()
 
	#FIX:
	query = "SELECT id, username, email FROM users WHERE username = ?"
	cursor.execute(query, (username,))

	rows = cursor.fetchall()
	conn.close()

	return {"results": [dict(r) for r in rows]}


# ============================================================
# 2) Hardcoded Secret (TODO)
# ============================================================
"""
# TODO: crear un archivo src/config.py con un "API_KEY = '...'"
# y un endpoint /config que lo devuelva.
# FIX: levantarlo de env var (os.environ o pydantic settings).

resuleto 
"""
# ============================================================
# 3) Command Injection (Vulnerable)
# ============================================================

def is_valid_host(host: str) -> bool:
    # Solo permite letras, números, punto y guión
    pattern = r"^[a-zA-Z0-9.-]+$"
    return re.match(pattern, host) is not None


@app.get("/ping")
def ping_host(host: str = Query(..., description="Host a hacer ping")):

    if not is_valid_host(host):
        raise HTTPException(status_code=400, detail="Host inválido")

    try:
        result = subprocess.run(
            ["ping", "-c", "1", host],  # Lista segura
            capture_output=True,
            text=True,
            check=True
        )
        return {"output": result.stdout}

    except subprocess.CalledProcessError:
        raise HTTPException(status_code=500, detail="Error ejecutando ping")
# ============================================================
# 4) SSRF (TODO)
# ============================================================
"""
# TODO (vulnerable): requests.get(url) directo
# Fix: allowlist de dominios / bloquear IPs privadas / timeouts / etc.
"""

def is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)

        # Solo permitir http y https
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Resolver dominio a IP
        ip = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(ip)

        # Bloquear IPs privadas, loopback y reservadas
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_reserved
            or ip_obj.is_link_local
        ):
            return False

        return True

    except Exception:
        return False
    
@app.get("/external-fetch")
def external_fetch(url: str = Query(..., description="URL externa permitida")):

    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="URL no permitida")

    try:
        r = requests.get(url, timeout=3)
        return {
            "url": url,
            "status_code": r.status_code,
            "content": r.text[:300]
        }

    except requests.RequestException:
        raise HTTPException(status_code=500, detail="Error al hacer la petición")

 

# ============================================================
# 5) Path Traversal (Vulnerable)
# ============================================================

@app.get("/readfile")
def read_file(filename: str = Query(..., description="Archivo a leer dentro de /data")):

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
    requested_path = os.path.abspath(os.path.join(base_dir, filename))

    # Verificar que el archivo esté dentro de /data
    if not requested_path.startswith(base_dir):
        raise HTTPException(status_code=400, detail="Acceso no permitido")

    if not os.path.isfile(requested_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    try:
        with open(requested_path, "r") as f:
            content = f.read()
        return {"file": filename, "content": content}

    except Exception:
        raise HTTPException(status_code=500, detail="Error al leer el archivo")


# ============================================================
# 6) SSRF (Vulnerable)
# ============================================================

@app.get("/ssrf")
def ssrf(url: str = Query(..., description="URL a la que hacer la petición")):
    """
    Endpoint vulnerable a SSRF
    Ejemplo de payload: http://alguna-pagina.com
    """
    try:
        r = requests.get(url, timeout=3)
        return {"url": url, "status_code": r.status_code, "content": r.text[:500]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    

"""
@app.get("/entregador-api")
def entregador_api():
    return ULTRA_SECRET_API_KEY
""" 