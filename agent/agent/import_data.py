"""Service ticket data import and vectorization module."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import ollama
import pandas as pd
import weaviate
from tqdm import tqdm
from weaviate.classes.config import DataType, Property

from agent.config import config


REQUIRED_COLUMNS = [
    "ticket_id",
    "customer_name",
    "issue_type",
    "description",
    "solution",
    "status",
    "priority",
    "created_date",
    "resolved_date",
    "agent",
    "satisfaction_rating",
]


class TicketImportData:
    """Load service tickets, build embedding text, and import them into Weaviate."""

    def __init__(self, csv_path: Path | str | None = None) -> None:
        self.csv_path = Path(csv_path) if csv_path else config.data_path
        self.embed_model = config.ollama.embed_model
        self.ollama_client = ollama.Client(host=config.ollama.host)

    def close(self) -> None:
        """Close network resources owned by the importer."""
        self.ollama_client.close()

    def load_and_prepare(self) -> list[dict[str, Any]]:
        """Load CSV data and prepare ticket text plus metadata for vector search."""
        print(f"Loading service ticket data from {self.csv_path}...")
        df = pd.read_csv(self.csv_path, encoding="utf-8")
        print(f"Loaded {len(df)} ticket records")

        self._validate_columns(df)
        df = self._clean_data(df)

        tickets = []
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Preparing tickets"):
            text = self._build_text_description(row)
            tickets.append(
                {
                    "id": str(row["ticket_id"]),
                    "text": text,
                    "metadata": {
                        "ticket_id": str(row["ticket_id"]),
                        "customer_name": str(row["customer_name"]),
                        "issue_type": str(row["issue_type"]),
                        "description": str(row["description"]),
                        "solution": str(row["solution"]),
                        "status": str(row["status"]),
                        "priority": str(row["priority"]),
                        "created_date": str(row["created_date"]),
                        "resolved_date": str(row["resolved_date"]),
                        "agent": str(row["agent"]),
                        "satisfaction_rating": int(row["satisfaction_rating"]),
                    },
                }
            )

        print(f"Prepared {len(tickets)} ticket records")
        return tickets

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """Check that the CSV contains every column this importer expects."""
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required CSV columns: {missing_columns}")

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove bad rows and fill optional fields with readable defaults."""
        df = df.drop_duplicates(subset=["ticket_id"])
        df = df.dropna(subset=["ticket_id", "issue_type", "description", "solution"])

        df = df.copy()
        df["customer_name"] = df["customer_name"].fillna("Unknown Customer")
        df["status"] = df["status"].fillna("Resolved")
        df["priority"] = df["priority"].fillna("Medium")
        df["created_date"] = df["created_date"].fillna("")
        df["resolved_date"] = df["resolved_date"].fillna("")
        df["agent"] = df["agent"].fillna("Unknown Agent")
        df["satisfaction_rating"] = pd.to_numeric(
            df["satisfaction_rating"], errors="coerce"
        ).fillna(0)

        return df

    def _build_text_description(self, row: pd.Series) -> str:
        """Build the readable text that Ollama turns into an embedding vector."""
        return f"""
Ticket ID: {row['ticket_id']}
Issue Type: {row['issue_type']}
Priority: {row['priority']}
Status: {row['status']}

Customer Problem:
{row['description']}

Solution:
{row['solution']}

Handled By: {row['agent']}
Satisfaction Rating: {int(row['satisfaction_rating'])}
        """.strip()

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for prepared ticket texts."""
        print(f"Generating embeddings for {len(texts)} ticket records...")
        embeddings = []

        for index, text in enumerate(
            tqdm(texts, desc="Generating embeddings"), start=1
        ):
            try:
                response = self.ollama_client.embed(model=self.embed_model, input=text)
                vectors = response.get("embeddings", [])
                if not vectors:
                    raise RuntimeError("Ollama returned no embedding vectors")
                embeddings.append(vectors[0])
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to generate embedding for ticket text #{index}"
                ) from exc

        print("Embedding generation finished")
        return embeddings

    def import_tickets(self) -> int:
        """Prepare tickets, generate embeddings, and save them into Weaviate."""
        tickets = self.load_and_prepare()
        texts = [ticket["text"] for ticket in tickets]
        embeddings = self.generate_embeddings(texts)

        weaviate_client = connect_weaviate()
        try:
            collection = recreate_collection(weaviate_client)
            for ticket, vector in tqdm(
                zip(tickets, embeddings), total=len(tickets), desc="Saving tickets"
            ):
                properties = dict(ticket["metadata"])
                properties["text"] = ticket["text"]
                collection.data.insert(properties=properties, vector=vector)
        finally:
            weaviate_client.close()

        return len(tickets)


def connect_weaviate() -> weaviate.WeaviateClient:
    """Connect to local Weaviate using values from config.py."""
    parsed = urlparse(config.weaviate.host)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8080
    return weaviate.connect_to_local(
        host=host,
        port=port,
        grpc_port=config.weaviate.grpc_port,
    )


def recreate_collection(client: weaviate.WeaviateClient):
    """Recreate the ServiceTicket collection so each import starts clean."""
    collection_name = config.weaviate.collection_name
    if client.collections.exists(collection_name):
        client.collections.delete(collection_name)

    return client.collections.create(
        collection_name,
        vectorizer_config=None,
        properties=[
            Property(name="ticket_id", data_type=DataType.TEXT),
            Property(name="customer_name", data_type=DataType.TEXT),
            Property(name="issue_type", data_type=DataType.TEXT),
            Property(name="description", data_type=DataType.TEXT),
            Property(name="solution", data_type=DataType.TEXT),
            Property(name="status", data_type=DataType.TEXT),
            Property(name="priority", data_type=DataType.TEXT),
            Property(name="created_date", data_type=DataType.TEXT),
            Property(name="resolved_date", data_type=DataType.TEXT),
            Property(name="agent", data_type=DataType.TEXT),
            Property(name="satisfaction_rating", data_type=DataType.INT),
            Property(name="text", data_type=DataType.TEXT),
        ],
    )


def main() -> None:
    importer = TicketImportData()
    try:
        imported_count = importer.import_tickets()
        print(
            f"Imported {imported_count} tickets into "
            f"{config.weaviate.collection_name} from {importer.csv_path}"
        )
    finally:
        importer.close()


if __name__ == "__main__":
    main()

