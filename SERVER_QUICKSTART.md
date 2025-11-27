# Quick Server Start

Choose your preferred method:

## Windows (Easiest)
**Double-click:** `run-server.bat`

Or from PowerShell:
```powershell
.\run-server.ps1
```

## Mac/Linux
```bash
bash run-server.sh
```

## From Anywhere (Using Make)
```bash
make server
```

## Manual Command
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## After Starting

- **Server**: http://localhost:8000
- **Web UI**: http://localhost:8000/ui
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Stop Server
Press `Ctrl+C` in the terminal where the server is running.
