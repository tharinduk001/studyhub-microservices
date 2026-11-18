from unittest import mock

import requests
from django.test import Client, SimpleTestCase, override_settings

from . import views


class GatewayTests(SimpleTestCase):
    def setUp(self):
        views._hits.clear()

    def test_unknown_resource_404(self):
        self.assertEqual(Client().get("/api/nope").status_code, 404)

    def test_internal_events_endpoint_blocked(self):
        self.assertEqual(Client().post("/api/activity/events", data="{}", content_type="application/json").status_code, 404)

    @mock.patch("api.views.requests.request", side_effect=requests.ConnectionError)
    def test_service_down_returns_503(self, _):
        r = Client().get("/api/rooms")
        self.assertEqual(r.status_code, 503)
        self.assertIn("room-service", r.json()["detail"])

    @mock.patch("api.views.requests.request")
    def test_routes_to_owning_service(self, req):
        req.return_value = mock.Mock(content=b"[]", status_code=200, headers={"content-type": "application/json"},
                                     raw=mock.Mock(headers=mock.Mock(getlist=lambda k: [])))
        Client().get("/api/topics")
        self.assertTrue(req.call_args.args[1].endswith("/topics"))
        self.assertIn(":8002", req.call_args.args[1])  # topics belong to room-service

    @override_settings(RATE_LIMIT_PER_MINUTE=3)
    @mock.patch("api.views.requests.request", side_effect=requests.ConnectionError)
    def test_rate_limit(self, _):
        codes = [Client().get("/api/rooms").status_code for _ in range(5)]
        self.assertEqual(codes[:3], [503] * 3)
        self.assertEqual(codes[3:], [429, 429])

    def test_web_ui_served(self):
        r = Client().get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"StudyHub", b"".join(r.streaming_content))
