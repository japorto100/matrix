"""Vendored MemPalace Chroma backend."""

from __future__ import annotations

import logging
import os
import sqlite3

import chromadb

from memory_fusion.mempalace.backends.base import BaseCollection

logger = logging.getLogger(__name__)


def _fix_blob_seq_ids(palace_path: str) -> None:
    """Fix legacy Chroma seq_id storage before PersistentClient init."""
    db_path = os.path.join(palace_path, "chroma.sqlite3")
    if not os.path.isfile(db_path):
        return
    try:
        with sqlite3.connect(db_path) as conn:
            for table in ("embeddings", "max_seq_id"):
                try:
                    rows = conn.execute(
                        f"SELECT rowid, seq_id FROM {table} WHERE typeof(seq_id) = 'blob'"
                    ).fetchall()
                except sqlite3.OperationalError:
                    continue
                if not rows:
                    continue
                updates = [
                    (int.from_bytes(blob, byteorder="big"), rowid)
                    for rowid, blob in rows
                ]
                conn.executemany(
                    f"UPDATE {table} SET seq_id = ? WHERE rowid = ?",
                    updates,
                )
            conn.commit()
    except Exception:  # noqa: BLE001
        logger.exception("Could not fix BLOB seq_ids in %s", db_path)


class ChromaCollection(BaseCollection):
    """Thin adapter over a Chroma collection."""

    def __init__(self, collection):
        self._collection = collection

    def add(self, *, documents, ids, metadatas=None):
        self._collection.add(documents=documents, ids=ids, metadatas=metadatas)

    def upsert(self, *, documents, ids, metadatas=None):
        self._collection.upsert(documents=documents, ids=ids, metadatas=metadatas)

    def query(self, **kwargs):
        return self._collection.query(**kwargs)

    def get(self, **kwargs):
        return self._collection.get(**kwargs)

    def delete(self, **kwargs):
        self._collection.delete(**kwargs)

    def count(self):
        return self._collection.count()


class ChromaBackend:
    """Factory for the local Chroma-backed verbatim store."""

    def get_collection(
        self,
        palace_path: str,
        collection_name: str,
        create: bool = False,
    ):
        if not create and not os.path.isdir(palace_path):
            raise FileNotFoundError(palace_path)

        if create:
            os.makedirs(palace_path, exist_ok=True)
            try:
                os.chmod(palace_path, 0o700)
            except (OSError, NotImplementedError):
                pass

        _fix_blob_seq_ids(palace_path)
        client = chromadb.PersistentClient(path=palace_path)
        if create:
            collection = client.get_or_create_collection(collection_name)
        else:
            collection = client.get_collection(collection_name)
        return ChromaCollection(collection)
