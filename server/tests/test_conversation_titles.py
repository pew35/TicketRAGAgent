"""Tests for generated conversation title cleanup."""

from unittest import TestCase

from server.web.api.conversations.router import (
    _clean_generated_title,
    _fallback_title,
)


class ConversationTitleTests(TestCase):
    def test_sentinel_titles_are_rejected(self) -> None:
        for title in ("None", " null ", "Title: undefined", "N/A"):
            with self.subTest(title=title):
                self.assertEqual(_clean_generated_title(title), "")

    def test_valid_generated_title_is_cleaned(self) -> None:
        self.assertEqual(
            _clean_generated_title("Title: Damaged Coffee Maker"),
            "Damaged Coffee Maker",
        )

    def test_question_provides_a_nonempty_fallback(self) -> None:
        self.assertEqual(
            _fallback_title("My appliance is broken"),
            "My appliance is broken",
        )
