"""Tests for demo-friendly user request validation."""

from unittest import TestCase

from server.web.api.users.schema import UserCreate


class UserCreateTests(TestCase):
    def test_short_nonempty_password_is_allowed(self) -> None:
        user = UserCreate(email="demo@example.com", password="x")
        self.assertEqual(user.password, "x")
