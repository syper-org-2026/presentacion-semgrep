from fastapi import FastAPI, Query, HTTPException
from contextlib import asynccontextmanager
from subprocess import run
from pathlib import Path
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

ALLOWED_DOMAINS = {
    "example.com",
    "api.github.com",
    "jsonplaceholder.typicode.com"
}
    
@app.get("/external-fetch")
def external_fetch(path: str = Query(..., description="Path del recurso externo")):
    """
    Solo permite requests a dominios en allowlist.
    El usuario NO controla la URL completa.
    """

    base_url = "https://jsonplaceholder.typicode.com"

    # El usuario solo controla el path
    full_url = f"{base_url}/{path.lstrip('/')}"

    parsed = urlparse(full_url)

    if parsed.hostname not in ALLOWED_DOMAINS:
        raise HTTPException(status_code=400, detail="Dominio no permitido")

    try:
        r = requests.get(full_url, timeout=3)
        return {
            "url": full_url,
            "status_code": r.status_code,
            "content": r.text[:300]
        }
    except requests.RequestException:
        raise HTTPException(status_code=500, detail="Error al hacer la petición")
 

# ============================================================
# 5) Path Traversal (Vulnerable)
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

@app.get("/readfile/{filename:path}")
def read_file(filename: str):

    try:
        requested_path = (DATA_DIR / filename).resolve()

        # Verificar que esté dentro del directorio permitido
        if not requested_path.is_relative_to(DATA_DIR.resolve()):
            raise HTTPException(status_code=400, detail="Acceso no permitido")

        if not requested_path.is_file():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")

        return {
            "file": filename,
            "content": requested_path.read_text()
        }

    except Exception:
        raise HTTPException(status_code=500, detail="Error leyendo archivo")

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