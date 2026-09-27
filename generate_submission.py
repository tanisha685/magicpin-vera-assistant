"""
Generate canonical submission.jsonl from dataset/test_pairs.json.
Runs the 4-context composition pipeline deterministically over all 30 test pairs.
"""

import sys
import json
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from context_store import ContextStore
from composer import compose

def main():
    root_dir = Path(__file__).parent
    dataset_dir = root_dir / "dataset"
    tp_file = dataset_dir / "test_pairs.json"
    out_file = root_dir / "submission.jsonl"

    if not tp_file.exists():
        print(f"Error: {tp_file} not found")
        return

    context_store = ContextStore(dataset_dir)
    print(f"ContextStore loaded: {context_store.counts()}")

    with open(tp_file, "r", encoding="utf-8") as fp:
        pairs = json.load(fp).get("pairs", [])

    print(f"Composing {len(pairs)} test pairs...")
    results = []

    with open(out_file, "w", encoding="utf-8") as out_fp:
        for pair in pairs:
            test_id = pair.get("test_id")
            t_id = pair.get("trigger_id")
            m_id = pair.get("merchant_id")
            c_id = pair.get("customer_id")

            trigger = context_store.get("trigger", t_id)
            if not trigger:
                trigger = {"id": t_id, "kind": "generic", "scope": "merchant"}

            merchant = context_store.get("merchant", m_id)
            if not merchant:
                merchant = {"merchant_id": m_id, "category_slug": "restaurants", "identity": {"name": m_id}}

            cat_slug = merchant.get("category_slug", "restaurants")
            category = context_store.get("category", cat_slug) or {"slug": cat_slug}
            customer = context_store.get("customer", c_id) if c_id else None

            res = compose(category, merchant, trigger, customer)

            record = {
                "test_id": test_id,
                "trigger_id": t_id,
                "merchant_id": m_id,
                "customer_id": c_id,
                "body": res.get("body"),
                "cta": res.get("cta"),
                "send_as": res.get("send_as"),
                "suppression_key": res.get("suppression_key"),
                "rationale": res.get("rationale")
            }
            results.append(record)
            out_fp.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"  [{test_id}] send_as={record['send_as']:18} cta={record['cta']:12} body=\"{record['body'][:50]}...\"")

    print(f"\nSuccessfully generated {len(results)} lines in {out_file}")

if __name__ == "__main__":
    main()
