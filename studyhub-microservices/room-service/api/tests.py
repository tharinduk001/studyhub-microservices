from unittest import mock

from django.test import Client, TestCase


def logged_in(user_id=1, username="alice"):
    c = Client()
    s = c.session
    s["user_id"], s["username"] = user_id, username
    s.save()
    return c


def make_room(client, name="Python Help", topic="python"):
    return client.post("/rooms", data={"name": name, "topic": topic, "description": "d"}, content_type="application/json")


@mock.patch("api.views.publish_event", lambda *a, **k: None)  # no network to activity-service in unit tests
class RoomTests(TestCase):
    def test_health(self):
        self.assertEqual(Client().get("/health").json()["service"], "room-service")

    def test_create_requires_login(self):
        self.assertEqual(make_room(Client()).status_code, 401)

    def test_create_and_get(self):
        r = make_room(logged_in())
        self.assertEqual(r.status_code, 201)
        room = r.json()
        self.assertEqual((room["host_id"], room["host_name"]), (1, "alice"))
        self.assertEqual(Client().get(f"/rooms/{room['id']}").json()["name"], "Python Help")

    def test_missing_room_404(self):
        self.assertEqual(Client().get("/rooms/99999").status_code, 404)

    def test_validation(self):
        self.assertEqual(make_room(logged_in(), name="").status_code, 422)

    def test_search_and_topics(self):
        make_room(logged_in(), "Algebra Club", "maths")
        names = [r["name"] for r in Client().get("/rooms", {"q": "Algebra"}).json()]
        self.assertIn("Algebra Club", names)
        self.assertTrue(any(t["name"] == "maths" for t in Client().get("/topics").json()))

    def test_host_can_update_and_delete(self):
        host = logged_in()
        rid = make_room(host).json()["id"]
        r = host.put(f"/rooms/{rid}", data={"name": "Edited", "topic": "python"}, content_type="application/json")
        self.assertEqual((r.status_code, r.json()["name"]), (200, "Edited"))
        self.assertEqual(host.delete(f"/rooms/{rid}").status_code, 204)
        self.assertEqual(Client().get(f"/rooms/{rid}").status_code, 404)

    def test_non_host_forbidden(self):
        rid = make_room(logged_in()).json()["id"]
        other = logged_in(2, "bob")
        self.assertEqual(other.put(f"/rooms/{rid}", data={"name": "Hack", "topic": "t"}, content_type="application/json").status_code, 403)
        self.assertEqual(other.delete(f"/rooms/{rid}").status_code, 403)
