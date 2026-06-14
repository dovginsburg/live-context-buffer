# Google Workspace / Calendar setup for Ezra

Status checked: not authenticated yet. Missing token:
`/Users/Ezra/.hermes/google_token.json`

Goal: enable Calendar first, optionally Gmail/Drive/Docs/Sheets later.

Setup path:

1. Create/select Google Cloud project:
   https://console.cloud.google.com/projectselector2/home/dashboard

2. Enable APIs:
   - Google Calendar API
   - Gmail API if email is desired
   - Google Drive API / Docs API / Sheets API if document access is desired
   - People API if contacts are desired

3. Create OAuth client:
   https://console.cloud.google.com/apis/credentials
   Credentials → Create Credentials → OAuth 2.0 Client ID → Desktop app.

4. If app is in Testing, add Dov's Google account as a test user:
   https://console.cloud.google.com/auth/audience

5. Download the OAuth client JSON.

6. Give Ezra the file path and run:
   `python ~/.hermes/skills/productivity/google-workspace/scripts/setup.py --client-secret /path/to/client_secret.json`

7. Generate auth URL for calendar-only:
   `python ~/.hermes/skills/productivity/google-workspace/scripts/setup.py --auth-url --services calendar --format json`

8. Open auth URL, approve, browser will likely fail at `http://localhost:1` — expected. Copy the full redirected URL back to Ezra.

9. Exchange code:
   `python ~/.hermes/skills/productivity/google-workspace/scripts/setup.py --auth-code "PASTED_URL" --format json`

10. Verify:
   `python ~/.hermes/skills/productivity/google-workspace/scripts/setup.py --check`

After that Ezra can use:
`python ~/.hermes/skills/productivity/google-workspace/scripts/google_api.py calendar list`
