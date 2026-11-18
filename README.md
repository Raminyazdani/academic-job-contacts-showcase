# Academic Job Contacts

A small research-contact tracker for two fictional academic job seekers. Save a researcher, record the topic that caught your attention, and track whether you have contacted them. Each workspace sees its own contact book.

## Run the example

Use Python 3.11 or newer with SQLite 3.35 or newer. From the repository root on Linux or macOS, run the following commands. Installing the Python dependencies requires access to a package index or a local wheel cache.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m contactbook demo
python -m unittest discover -s tests -v
```

The demo starts a loopback HTTP server and makes real requests through FastAPI. It creates a temporary database, updates a contact, shuts down the server, and reopens the database with fresh sessions. The demo and tests run offline after installation.

```text
cairn sees Aster Vell at Glass Orchard Lab
rill sees Fen Quill at Paper Delta Studio
cairn moved Aster Vell to contacted
rill received HTTP 404 for lookup and update of cairn's contact
reopened SQLite and recovered Aster Vell at stage contacted
```

## Use a persistent contact book

Start the server in one terminal. It creates the database in the current directory and prints two temporary bearer tokens, one for each fictional workspace. Keep it running while you try the requests below. Restarting the service rotates both tokens and retains contacts in the same database file.

```sh
python -m contactbook serve --database contacts.sqlite3 --port 8000
```

In another terminal, paste the printed token for the `cairn` workspace when prompted. These three requests create a contact, list the workspace, and change the new contact's stage.

```sh
printf 'Cairn token: '
read -r TOKEN
BASE=http://127.0.0.1:8000
CONTACT=$(curl -fsS "$BASE/contacts" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Aster Vell","research_group":"Glass Orchard Lab","research_topic":"Frost on glass leaves"}')
curl -fsS "$BASE/contacts" -H "Authorization: Bearer $TOKEN"
ID=$(printf '%s' "$CONTACT" | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')
curl -fsS -X PATCH "$BASE/contacts/$ID" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"stage":"following_up"}'
```

The stage can be `saved`, `contacted`, or `following_up`. The service binds to `127.0.0.1`. Anyone with access to the server terminal can use either sample account, so run the example in a private local shell. All personal names, research groups and topics in the examples are fictional.

## How scope reaches storage

1. The client supplies a bearer token. FastAPI resolves it through an in-memory session table and injects its workspace into the handler. Missing or unknown credentials receive HTTP 401.
2. A create request supplies the researcher's name, group and topic. The handler sets the workspace from the resolved session. The request models reject extra input fields.
3. SQLite stores each record under a composite `(workspace, id)` primary key. The list, lookup and stage-update queries all include the workspace in their predicates. A cross-workspace identifier and a missing identifier each receive the same HTTP 404 response.
4. The four HTTP integration tests use local temporary databases. They cover isolation in both directions, changes by the owner, missing and invalid bearer sessions, invalid input, and reopening stored rows after issuing fresh sessions.

The API schema is available at `/openapi.json` while the local server is running.
