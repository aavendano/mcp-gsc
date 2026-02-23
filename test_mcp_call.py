
import json
import subprocess
import sys
import os

def main():
    server_cmd = ["/home/alejandro/mcp-gsc/.venv/bin/python", "/home/alejandro/mcp-gsc/gsc_server.py"]
    
    # Aseguramos que no se salte OAuth
    env = os.environ.copy()
    env["GSC_SKIP_OAUTH"] = "false"
    
    process = subprocess.Popen(
        server_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0,
        env=env
    )

    # 1. Initialize
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "gemini-cli", "version": "1.0"}
        }
    }
    process.stdin.write(json.dumps(init_request) + "\n")
    
    # Leer respuestas e imprimir logs de error si aparecen
    while True:
        line = process.stdout.readline()
        if not line: break
        if line.strip().startswith("{"):
            break
    
    # 2. Initialized (Notification)
    process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")

    # 3. Call tool: list_properties
    process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "list_properties", "arguments": {}}}) + "\n")
    
    # Leer respuesta final
    output_found = False
    while True:
        line = process.stdout.readline()
        if not line: break
        if line.strip().startswith('{"jsonrpc":"2.0","id":2'):
            print(line)
            output_found = True
            break
            
    # Capturar stderr para ver por qué falló OAuth
    stderr_output = process.stderr.read()
    if stderr_output:
        print("\n--- SERVER LOGS (STDERR) ---")
        print(stderr_output)

    process.terminate()

if __name__ == "__main__":
    main()
