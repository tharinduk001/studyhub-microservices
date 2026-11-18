import json

from django.test import Client, TestCase, override_settings

KEY = {"HTTP_X_INTERNAL_KEY": "internal-dev-key"}


@override_settings(INTERNAL_KEY="internal-dev-key")
class ActivityTests(TestCase):
    def event(self, type_="message_posted", user="alice"):
        return Client().post(
            "/events",
            data=json.dumps({"type": type_, "user_id": 1, "username": user, "detail": "d"}),
            content_type="application/json",
            **KEY,
        )

    def test_health(self):
        self.assertEqual(Client().get("/health").json()["service"], "activity-service")

    def test_record_event_requires_internal_key(self):
        r = Client().post("/events", data="{}", content_type="application/json")
        self.assertEqual(r.status_code, 403)

    def test_feed_newest_first_with_limit(self):
        for t in ("room_created", "message_posted", "message_posted"):
            self.event(t)
        feed = Client().get("/activity").json()
        self.assertEqual([e["id"] for e in feed], sorted([e["id"] for e in feed], reverse=True))
        self.assertEqual(len(Client().get("/activity", {"limit": 1}).json()), 1)

    def test_feed_type_filter(self):
        for t in ("room_created", "message_posted", "message_posted"):
            self.event(t)
        c = Client()
        self.assertEqual(len(c.get("/activity", {"type": "message_posted"}).json()), 2)
        self.assertEqual(len(c.get("/activity", {"type": "nothing"}).json()), 0)
        self.assertEqual(len(c.get("/activity").json()), 3)

    def test_stats(self):
        self.event("room_created", "alice")
        self.event("message_posted", "bob")
        self.event("message_posted", "bob")
        stats = Client().get("/activity/stats").json()
        self.assertEqual(stats["total_events"], 3)
        self.assertEqual(stats["by_type"], {"room_created": 1, "message_posted": 2})
        self.assertEqual(stats["most_active_users"][0]["username"], "bob")
