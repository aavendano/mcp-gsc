from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/webmasters"]
flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)

creds = flow.run_local_server(
    host="127.0.0.1",
    port=8765,
    open_browser=False
)

Path("token.json").write_text(creds.to_json(), encoding="utf-8")
print("Token creado en:", Path("token.json").resolve())
