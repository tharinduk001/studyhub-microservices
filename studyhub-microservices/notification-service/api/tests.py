from django.test import Client, TestCase, override_settings

from .models import Notification

KEY = {"HTTP_X_INTERNAL_KEY": "internal-dev-key"}


def logged_in(user_id=1, username="alice"):
    c = Client()
    s = c.session
    s["user_id"], s["username"] = user_id, username
    s.save()
    return c


@override_settings(INTERNAL_KEY="internal-dev-key")
class NotificationTests(TestCase):
    def create(self, user_id=1, message="bob posted"):
        return Client().post("/notifications", data={"user_id": user_id, "message": message},
                             content_type="application/json", **KEY)

    def test_health(self):
        self.assertEqual(Client().get("/health").json()["service"], "notification-service")

    def test_create_requires_internal_key(self):
        r = Client().post("/notifications", data={"user_id": 1, "message": "x"}, content_type="application/json")
        self.assertEqual(r.status_code, 403)

    def test_create_validation(self):
        r = Client().post("/notifications", data={"user_id": 1}, content_type="application/json", **KEY)
        self.assertEqual(r.status_code, 422)

    def test_list_requires_login(self):
        self.assertEqual(Client().get("/notifications").status_code, 401)

    def test_user_only_sees_own_notifications(self):
        self.create(1, "for alice")
        self.create(2, "for bob")
        items = logged_in(1).get("/notifications").json()
        self.assertEqual([n["message"] for n in items], ["for alice"])

    def test_unread_count_and_mark_all_read(self):
        self.create(1, "a")
        self.create(1, "b")
        c = logged_in(1)
        self.assertEqual(c.get("/notifications/count").json()["unread"], 2)
        self.assertEqual(c.post("/notifications/read-all").json()["updated"], 2)
        self.assertEqual(c.get("/notifications/count").json()["unread"], 0)
        self.assertEqual(c.get("/notifications", {"unread_only": "1"}).json(), [])

    def test_mark_single_read_only_for_owner(self):
        nid = self.create(1).json()["id"]
        self.assertEqual(logged_in(2, "bob").post(f"/notifications/{nid}/read").status_code, 404)
        self.assertEqual(logged_in(1).post(f"/notifications/{nid}/read").status_code, 200)
        self.assertTrue(Notification.objects.get(id=nid).is_read)
