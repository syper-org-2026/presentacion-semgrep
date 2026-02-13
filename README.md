# presentacion-semgrep
Syper 2025


HOLA :)

Saludos cordiales

```bash
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

## To Do

- [x] Vulnerabilidad SQL Injection
- [ ] Uso inseguro de `eval` o Command Injection
- [ ] Secret hardcodeado
- [ ] SSRF (endpoint que hace request GET con una URL que viene del usuario)
