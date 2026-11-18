from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from contactbook.api import create_app, new_sessions
from contactbook.demo import CAIRN_CONTACT, RILL_CONTACT, request
from contactbook.local_http import local_server


class WorkspaceRequests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.path = Path(directory) / "contacts.sqlite3"
        self.sessions = new_sessions()
        self.url = self.enterContext(local_server(create_app(self.path, self.sessions)))

    def call(self, owner, method, path="/contacts", body=None):
        return request(self.url, method, path, self.sessions[owner], body)

    def create(self, owner, draft):
        code, row = self.call(owner, "POST", body=draft)
        self.assertEqual(code, 201)
        self.assertEqual(row["stage"], "saved")
        return row

    def test_each_owner_sees_and_updates_only_its_contacts(self):
        records = {
            "cairn": self.create("cairn", CAIRN_CONTACT),
            "rill": self.create("rill", RILL_CONTACT),
        }
        for owner, other in (("cairn", "rill"), ("rill", "cairn")):
            with self.subTest(owner=owner):
                own = records[owner]
                own_path = f"/contacts/{own['id']}"
                foreign_path = f"/contacts/{records[other]['id']}"
                missing = f"/contacts/{uuid4()}"
                self.assertEqual(self.call(owner, "GET"), (200, [own]))
                self.assertEqual(self.call(owner, "GET", own_path), (200, own))
                for method, body in (("GET", None), ("PATCH", {"stage": "following_up"})):
                    foreign = self.call(owner, method, foreign_path, body)
                    self.assertEqual(foreign, self.call(owner, method, missing, body))
                    self.assertEqual(foreign, (404, {"detail": "Contact not found"}))
                records[owner] = dict(own, stage="contacted")
                updated = self.call(owner, "PATCH", own_path, {"stage": "contacted"})
                self.assertEqual(updated, (200, records[owner]))
                self.assertEqual(self.call(other, "GET", foreign_path), (200, records[other]))

    def test_rejects_missing_and_unknown_sessions(self):
        for bad in (None, "unknown-demo-token"):
            for method, path, body in (
                ("GET", "/contacts", None),
                ("POST", "/contacts", CAIRN_CONTACT),
                ("GET", f"/contacts/{uuid4()}", None),
                ("PATCH", f"/contacts/{uuid4()}", {"stage": "contacted"}),
            ):
                with self.subTest(token=bad, method=method, path=path):
                    code, _ = request(self.url, method, path, bad, body)
                    self.assertEqual(code, 401)

    def test_owner_is_derived_from_session_and_invalid_input_is_rejected(self):
        for draft in (
            dict(CAIRN_CONTACT, workspace="rill"),
            dict(CAIRN_CONTACT, name="   "),
            dict(CAIRN_CONTACT, research_topic=""),
        ):
            code, _ = self.call("cairn", "POST", body=draft)
            self.assertEqual(code, 422)
        row = self.create("cairn", CAIRN_CONTACT)
        path = f"/contacts/{row['id']}"
        for change in ({"stage": "contacted", "workspace": "rill"}, {"stage": "unknown"}):
            code, _ = self.call("cairn", "PATCH", path, change)
            self.assertEqual(code, 422)
        self.assertEqual(self.call("cairn", "GET", path), (200, row))
        self.assertEqual(self.call("rill", "GET"), (200, []))

    def test_new_session_book_reopens_existing_rows(self):
        row = self.create("rill", RILL_CONTACT)
        fresh = new_sessions()
        with local_server(create_app(self.path, fresh)) as url:
            self.assertEqual(request(url, "GET", "/contacts", fresh["rill"]), (200, [row]))
            self.assertEqual(request(url, "GET", "/contacts", fresh["cairn"]), (200, []))
            code, _ = request(url, "GET", "/contacts", self.sessions["rill"])
            self.assertEqual(code, 401)
