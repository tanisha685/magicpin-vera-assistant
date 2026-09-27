"""
Context Store for magicpin AI Challenge (Vera).
Manages in-memory storage of Category, Merchant, Customer, and Trigger contexts.
Guarantees version tracking, idempotency, atomic updates, and fast lookup.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, Any, List
from datetime import datetime

logger = logging.getLogger("vera.context_store")


class ContextStore:
    def __init__(self, data_dir: Optional[Path] = None):
        # Key: (scope, context_id) -> {"version": int, "payload": dict, "stored_at": str}
        self.store: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.data_dir = data_dir or Path(__file__).parent / "dataset"
        self._preload_dataset()

    def _preload_dataset(self):
        """Preload base/expanded dataset if present on disk."""
        if not self.data_dir.exists():
            logger.info("Dataset dir %s does not exist, starting empty", self.data_dir)
            return

        loaded_counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}

        # 1. Load Categories
        cat_dir = self.data_dir / "categories"
        if cat_dir.exists():
            for f in cat_dir.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        slug = data.get("slug", f.stem)
                        self.set("category", slug, 1, data)
                        loaded_counts["category"] += 1
                except Exception as e:
                    logger.warning("Failed loading category %s: %s", f, e)

        # 2. Load Seed / Consolidated files
        for name, scope, key in [
            ("merchants_seed.json", "merchant", "merchant_id"),
            ("customers_seed.json", "customer", "customer_id"),
            ("triggers_seed.json", "trigger", "id"),
        ]:
            path = self.data_dir / name
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        items = data.get(scope + "s", data.get(scope, []))
                        for item in items:
                            cid = item.get(key)
                            if cid:
                                self.set(scope, cid, 1, item)
                                loaded_counts[scope] += 1
                except Exception as e:
                    logger.warning("Failed loading seed %s: %s", name, e)

        # 3. Load Expanded directories if present
        for scope, folder, key in [
            ("merchant", "merchants", "merchant_id"),
            ("customer", "customers", "customer_id"),
            ("trigger", "triggers", "id"),
        ]:
            sub_dir = self.data_dir / folder
            if sub_dir.exists():
                for f in sub_dir.glob("*.json"):
                    try:
                        with open(f, "r", encoding="utf-8") as fp:
                            item = json.load(fp)
                            cid = item.get(key, f.stem)
                            if cid and (scope, cid) not in self.store:
                                self.set(scope, cid, 1, item)
                                loaded_counts[scope] += 1
                    except Exception as e:
                        logger.warning("Failed loading %s/%s: %s", folder, f, e)

        logger.info("ContextStore preloaded: %s", loaded_counts)

    def set(self, scope: str, context_id: str, version: int, payload: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Store a context with versioning.
        Idempotent: re-posting same version is accepted as a 200 no-op.
        Returns (accepted, reason_or_ack, current_version).
        """
        key = (scope, context_id)
        current = self.store.get(key)
        if current:
            cur_ver = current.get("version", 1)
            if version < cur_ver:
                return False, "stale_version", cur_ver

        self.store[key] = {
            "version": version,
            "payload": payload,
            "stored_at": datetime.utcnow().isoformat() + "Z"
        }
        ack_id = f"ack_{context_id}_v{version}"
        return True, ack_id, version

    def get(self, scope: str, context_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve payload for a given scope and context_id."""
        item = self.store.get((scope, context_id))
        return item["payload"] if item else None

    def get_version(self, scope: str, context_id: str) -> int:
        item = self.store.get((scope, context_id))
        return item["version"] if item else 0

    def get_all(self, scope: str) -> Dict[str, Dict[str, Any]]:
        """Return dict of {context_id: payload} for all items in scope."""
        results = {}
        for (sc, cid), item in self.store.items():
            if sc == scope:
                results[cid] = item["payload"]
        return results

    def counts(self) -> Dict[str, int]:
        counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
        for (scope, _), _ in self.store.items():
            counts[scope] = counts.get(scope, 0) + 1
        return counts

    def clear(self):
        """Wipe state (for teardown)."""
        self.store.clear()
