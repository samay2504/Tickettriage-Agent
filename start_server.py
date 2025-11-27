#!/usr/bin/env python3
"""
Ticket Triage Agent - Backend Server Launcher
Simple script to start the backend server without remembering long commands.
"""

import subprocess
import sys
import os

def main():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 60)
    print("🎯 Ticket Triage Agent - Backend Server")
    print("=" * 60)
    print()
    print("Starting server...")
    print()
    print("📍 Server: http://localhost:8000")
    print("🎨 Web UI: http://localhost:8000/ui")
    print("📚 API Docs: http://localhost:8000/docs")
    print("❤️  Health: http://localhost:8000/health")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    try:
        # Change to the script directory and run uvicorn
        os.chdir(script_dir)
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", "8000"
        ])
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("✅ Server stopped gracefully")
        print("=" * 60)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
