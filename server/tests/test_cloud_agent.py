"""Tests for the lightweight public-demo RAG implementation."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase, TestCase

from server.services.cloud_agent import CloudTicketAgent
from server.settings import Settings


CSV_CONTENT = """ticket_id,issue_type,description,solution,priority
TCK-1,Damaged Item,Coffee maker arrived with a cracked tank,Replace the damaged unit,High
TCK-2,Order Status,Carrier tracking has not updated,Check the carrier status,Low
TCK-3,Appliance Repair,Customer asks 电器坏了找谁维修,请拨打维修员 4128889799,High
"""


class CloudTicketAgentTests(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "tickets.csv"
        self.csv_path.write_text(CSV_CONTENT, encoding="utf-8")
        self.agent = CloudTicketAgent(
            Settings(
                ticket_data_path=self.csv_path,
                llm_api_key=None,
                agent_mode="internal",
                redis_enabled=False,
            )
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_search_returns_the_relevant_ticket_first(self) -> None:
        sources = self.agent.search("My coffee maker tank is cracked")
        self.assertEqual(sources[0]["ticket_id"], "TCK-1")

    def test_search_supports_chinese_questions(self) -> None:
        sources = self.agent.search("电器坏了找谁维修？")
        self.assertEqual(sources[0]["ticket_id"], "TCK-3")
        self.assertIn("4128889799", sources[0]["solution"])

    async def test_answer_falls_back_when_no_api_key_is_configured(self) -> None:
        response = await self.agent.answer("My coffee maker tank is cracked")
        self.assertEqual(response["code"], 0)
        self.assertIn("Replace the damaged unit", response["answer"])
        self.assertTrue(response["metadata"]["fallback"])


class DatabaseUrlTests(TestCase):
    def test_neon_style_ssl_parameters_are_asyncpg_compatible(self) -> None:
        settings = Settings(
            database_url=(
                "postgresql://user:pass@example.test/db"
                "?sslmode=require&channel_binding=require"
            )
        )
        self.assertEqual(
            str(settings.db_url),
            "postgresql+asyncpg://user:pass@example.test/db?ssl=require",
        )
