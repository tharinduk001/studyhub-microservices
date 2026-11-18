import json

from django.test import Client, TestCase


def post(client, path, data):
    return client.post(path, data=json.dumps(data), content_type="application/json")


def register(client, name="alice", password="secret123"):
    return post(client, "/auth/register", {"username": name, "email": f"{name}@x.com", "password": password})


class UserTests(TestCase):
    def test_health(self):
        self.assertEqual(Client().get("/health").json()["service"], "user-service")

    def test_register_logs_in_and_returns_public_user(self):
        c = Client()
        r = register(c, "reg1")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["user"]["username"], "reg1")
        self.assertNotIn("password", json.dumps(r.json()))
        self.assertEqual(c.get("/users/me").json()["username"], "reg1")  # session cookie now set

    def test_duplicate_username_is_case_insensitive(self):
        register(Client(), "dup")
        self.assertEqual(register(Client(), "DUP").status_code, 409)

    def test_register_validation(self):
        self.assertEqual(register(Client(), "ab").status_code, 422)
        self.assertEqual(register(Client(), "shortpw", password="123").status_code, 422)

    def test_login_and_wrong_password(self):
        register(Client(), "bob")
        c = Client()
        self.assertEqual(post(c, "/auth/login", {"username": "bob", "password": "secret123"}).status_code, 200)
        self.assertEqual(c.get("/users/me").status_code, 200)
        self.assertEqual(post(Client(), "/auth/login", {"username": "bob", "password": "bad"}).status_code, 401)
        self.assertEqual(post(Client(), "/auth/login", {"username": "nobody", "password": "secret123"}).status_code, 401)

    def test_me_requires_login_and_logout_clears_session(self):
        self.assertEqual(Client().get("/users/me").status_code, 401)
        c = Client()
        register(c, "carol")
        self.assertEqual(c.post("/auth/logout").status_code, 200)
        self.assertEqual(c.get("/users/me").status_code, 401)

    def test_update_profile_and_get_user(self):
        c = Client()
        uid = register(c, "dave").json()["user"]["id"]
        r = c.put("/users/me", data=json.dumps({"bio": "Hello"}), content_type="application/json")
        self.assertEqual(r.json()["bio"], "Hello")
        self.assertEqual(Client().get(f"/users/{uid}").json()["username"], "dave")
        self.assertEqual(Client().get("/users/99999").status_code, 404)
