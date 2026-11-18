"""Walk two fictional workspaces through the API using loopback HTTP."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from .api import create_app, new_sessions
from .local_http import local_server


CAIRN_CONTACT = {
    "name": "Aster Vell",
    "research_group": "Glass Orchard Lab",
    "research_topic": "Mapping frost patterns on imaginary glass leaves",
}
RILL_CONTACT = {
    "name": "Fen Quill",
    "research_group": "Paper Delta Studio",
    "research_topic": "Modelling water flow through folded paper canals",
}


def request(base_url, method, path, token=None, body=None):
    headers = {}
    data = None
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    message = Request(base_url + path, data=data, headers=headers, method=method)
    local = build_opener(ProxyHandler({}))
    try:
        response = local.open(message, timeout=5)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.load(response)


def expect(result, status_code):
    code, body = result
    if code != status_code:
        raise RuntimeError(f"Expected HTTP {status_code}, received {code}")
    return body


def run():
    with TemporaryDirectory() as directory:
        database = Path(directory) / "contacts.sqlite3"
        sessions = new_sessions()
        with local_server(create_app(database, sessions)) as url:
            first = expect(request(url, "POST", "/contacts", sessions["cairn"], CAIRN_CONTACT), 201)
            expect(request(url, "POST", "/contacts", sessions["rill"], RILL_CONTACT), 201)
            for workspace, expected in (("cairn", CAIRN_CONTACT), ("rill", RILL_CONTACT)):
                rows = expect(request(url, "GET", "/contacts", sessions[workspace]), 200)
                if len(rows) != 1 or rows[0]["name"] != expected["name"]:
                    raise RuntimeError(f"Unexpected contact list in {workspace}")
                print(f"{workspace} sees {rows[0]['name']} at {rows[0]['research_group']}")

            path = f"/contacts/{first['id']}"
            updated = expect(request(url, "PATCH", path, sessions["cairn"], {"stage": "contacted"}), 200)
            print(f"cairn moved {updated['name']} to {updated['stage']}")
            expect(request(url, "GET", path, sessions["rill"]), 404)
            expect(request(url, "PATCH", path, sessions["rill"], {"stage": "saved"}), 404)
            print("rill received HTTP 404 for lookup and update of cairn's contact")

        sessions = new_sessions()
        with local_server(create_app(database, sessions)) as url:
            saved = expect(request(url, "GET", path, sessions["cairn"]), 200)
            if saved["stage"] != "contacted":
                raise RuntimeError("The owner's change did not persist")
            print(f"reopened SQLite and recovered {saved['name']} at stage {saved['stage']}")
