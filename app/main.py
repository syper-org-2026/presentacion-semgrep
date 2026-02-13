from fastapi import FastAPI, Query, HTTPException
from contextlib import asynccontextmanager
from subprocess import run
import os
import sqlite3
import requests

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "database.db")
ULTRA_SECRET_API_KEY = "sk-proj-Nz3BIzijIqwZehGsXnDGiXqFyUQj1KBORzH5ewhSXxVX4ggBYWVRAd7AelBsxzSlU-1aWtyznXT5BlNkFJfWXFkveZ7bBzZXyuJd172QZ_xlmF8qFkAAvTumBu9Gs9VKTEOtjIC8iCPOuAs0IICo14q4oOkA"

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

	# Concatenacion directa
	query = f"SELECT id, username, email FROM users WHERE username = '{username}'"
	cursor.execute(query)

	# FIX:
	# query = "SELECT id, username, email FROM users WHERE username = ?"
	# cursor.execute(query, (username,))

	rows = cursor.fetchall()
	conn.close()

	return {"query": query, "results": [dict(r) for r in rows]}

# ============================================================
# 2) Hardcoded Secret (TODO)
# ============================================================

# TODO: crear un archivo src/config.py con un "API_KEY = '...'"
# y un endpoint /config que lo devuelva.
# FIX: levantarlo de env var (os.environ o pydantic settings).


# ============================================================
# 3) Command Injection (Vulnerable)
# ============================================================

@app.get("/ping")
def ping_host(host: str = Query(..., description="Host a hacer ping")):
    """
    Endpoint vulnerable a Command Injection
    Ejemplo de payload: 8.8.8.8; cat /etc/passwd
    """
    command = f"ping -c 1 {host}"
    result = run(command, shell=True, capture_output=True, text=True)
    return {"command": command, "output": result.stdout}

# ============================================================
# 4) SSRF (TODO)
# ============================================================

# TODO (vulnerable): requests.get(url) directo
# Fix: allowlist de dominios / bloquear IPs privadas / timeouts / etc.

# ============================================================
# 5) Path Traversal (Vulnerable)
# ============================================================

@app.get("/readfile")
def read_file(filename: str = Query(..., description="Archivo a leer dentro de /data")):
    """
    Endpoint vulnerable a Path Traversal
    Ejemplo de payload: ../../.env
    """
    file_path = os.path.join(os.path.dirname(__file__), "data", filename)
    try:
        with open(file_path, "r") as f:
            content = f.read()
        return {"file": filename, "content": content}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

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
