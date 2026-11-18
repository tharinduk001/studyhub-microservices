import json
from unittest import mock

import requests
from django.test import Client, TestCase, override_settings

from .models import Message

KEY = {"HTTP_X_INTERNAL_KEY": "internal-dev-key"}
ROOM = {"id": 1, "name": "Python Help", "host_id": 99, "host_name": "host"}


def logged_in(user_id=1, username="alice"):
    c = Client()
    s = c.session
    s["user_id"], s["username"] = user_id, username
    s.save()
    return c


def room_response(status=200):
    return mock.Mock(status_code=status, json=lambda: ROOM)


def post(client, room_id=1, body="hello"):
    return client.post("/messages", data=json.dumps({"room_id": room_id, "body": body}), content_type="application/json")


@override_settings(INTERNAL_KEY="internal-dev-key")
@mock.patch("api.views.fire_and_forget")
@mock.patch("api.views.requests.get", return_value=room_response())
class MessageTests(TestCase):
    def test_health(self, *_):
        self.assertEqual(Client().get("/health").json()["service"], "message-service")

    def test_post_requires_login(self, *_):
        self.assertEqual(post(Client()).status_code, 401)

    def test_post_validation(self, *_):
        self.assertEqual(post(logged_in(), body="").status_code, 422)

    def test_post_ok_notifies_host_and_logs_activity(self, _get, fire):
        r = post(logged_in(1, "alice"))
        self.assertEqual(r.status_code, 201)
        urls = [c.args[0] for c in fire.call_args_list]
        self.assertTrue(any(u.endswith("/notifications") for u in urls))
        self.assertTrue(any(u.endswith("/events") for u in urls))

    def test_host_posting_in_own_room_is_not_notified(self, _get, fire):
        post(logged_in(99, "host"))
        self.assertFalse(any(c.args[0].endswith("/notifications") for c in fire.call_args_list))

    def test_post_to_missing_room_404(self, get, _fire):
        get.return_value = room_response(404)
        self.assertEqual(post(logged_in()).status_code, 404)

    def test_post_when_room_service_down_503(self, get, _fire):
        get.side_effect = requests.ConnectionError
        self.assertEqual(post(logged_in()).status_code, 503)

    def test_list_filters_by_room_and_paginates(self, *_):
        c = logged_in()
        for i in range(5):
            post(c, room_id=1, body=f"m{i}")
        post(c, room_id=2, body="other room")
        page1 = Client().get("/messages", {"room_id": 1, "limit": 2}).json()
        page2 = Client().get("/messages", {"room_id": 1, "limit": 2, "offset": 2}).json()
        self.assertEqual([m["body"] for m in page1], ["m4", "m3"])  # newest first
        self.assertEqual([m["body"] for m in page2], ["m2", "m1"])
        self.assertEqual(Client().get("/messages", {"limit": "abc"}).status_code, 422)

    def test_edit_own_message_only(self, *_):
        mid = post(logged_in(1, "alice")).json()["id"]
        r = logged_in(1, "alice").put(f"/messages/{mid}", data=json.dumps({"body": "edited"}), content_type="application/json")
        self.assertEqual((r.status_code, r.json()["body"]), (200, "edited"))
        other = logged_in(2, "bob").put(f"/messages/{mid}", data=json.dumps({"body": "hack"}), content_type="application/json")
        self.assertEqual(other.status_code, 403)
        bad = logged_in(1, "alice").put(f"/messages/{mid}", data=json.dumps({"body": ""}), content_type="application/json")
        self.assertEqual(bad.status_code, 422)
        self.assertEqual(Message.objects.get(id=mid).body, "edited")

    def test_edit_missing_message_404(self, *_):
        self.assertEqual(logged_in().put("/messages/999", data="{}", content_type="application/json").status_code, 404)

    def test_delete_own_message_only(self, *_):
        mid = post(logged_in(1, "alice")).json()["id"]
        self.assertEqual(logged_in(2, "bob").delete(f"/messages/{mid}").status_code, 403)
        self.assertEqual(logged_in(1, "alice").delete(f"/messages/{mid}").status_code, 204)

    def test_internal_cleanup_requires_key(self, *_):
        post(logged_in(), room_id=1)
        self.assertEqual(Client().delete("/messages?room_id=1").status_code, 403)
        self.assertEqual(Message.objects.count(), 1)

    def test_internal_cleanup_deletes_only_that_room(self, *_):
        c = logged_in()
        post(c, room_id=1)
        post(c, room_id=1)
        post(c, room_id=2)
        r = Client().delete("/messages?room_id=1", **KEY)
        self.assertEqual((r.status_code, r.json()["deleted"]), (200, 2))
        self.assertEqual(list(Message.objects.values_list("room_id", flat=True)), [2])
        self.assertEqual(Client().delete("/messages", **KEY).status_code, 422)
