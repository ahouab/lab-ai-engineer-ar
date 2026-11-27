import argparse
import json
import math
import re
import unicodedata
from pathlib import Path
from statistics import median
from time import perf_counter

from rag import ServiceError, request_json


ARABIC_TRANSLATION = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹أإآٱ", "01234567890123456789اااا")
ARABIC_MARKS = re.compile(r"[\u0610-\u061a\u0640\u064b-\u065f\u0670\u200e\u200f\u2066-\u2069]")


def normalize(text):
    # نقارن الإجابات مع تجاهل التشكيل واختلاف أشكال الألف والأرقام.
    canonical = unicodedata.normalize("NFKC", text).casefold().translate(ARABIC_TRANSLATION)
    return " ".join(ARABIC_MARKS.sub("", canonical).split())


def matches(text, groups):
    normalized = normalize(text)
    return all(
        any(re.search(rf"(?<!\d){re.escape(normalize(term))}(?!\d)", normalized) for term in group)
        for group in groups
    )


def run_eval(url, cases):
    rows = []
    for case in cases:
        start = perf_counter()
        result = request_json(f"{url}/ask", "POST", {"question": case["question"]}, timeout=510)
        sources = [item["source"] for item in result["sources"]]
        expected_source = case.get("source")
        if expected_source:
            retrieved_sources = [item["source"] for item in result["candidates"]]
            hit = expected_source in retrieved_sources
            first_hit = retrieved_sources[:1] == [expected_source]
            passed = (
                result["verdict"] == "ok"
                and expected_source in sources
                and matches(result["answer"], case["expected_groups"])
            )
        else:
            hit = None
            first_hit = None
            passed = result["verdict"] == "abstain" and "issue" not in result
        rows.append({
            "id": case["id"],
            "model": result["model"],
            "passed": passed,
            "hit_at_1": first_hit,
            "hit_at_3": hit,
            "answer": result["answer"],
            "sources": sources,
            "issue": result.get("issue"),
            "latency_ms": round((perf_counter() - start) * 1_000),
            "retrieval_ms": result["retrieval_ms"],
            "generation_ms": result["generation_ms"],
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description="تقييم الإجابات عن مجموعة الأسئلة التجريبية عبر واجهة RAG.")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="العنوان الأساسي لواجهة RAG")
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("evaluation.json"),
                        help="مسار ملف أسئلة التقييم")
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if not cases:
        parser.error("ملف أسئلة التقييم فارغ.")
    try:
        request_json(f"{args.url}/readyz", timeout=10)
        rows = run_eval(args.url, cases)
    except ServiceError as error:
        parser.exit(1, f"توقف التقييم. {error}\n")
    latencies = sorted(row["latency_ms"] for row in rows)
    known = [row for row in rows if row["hit_at_3"] is not None]
    summary = {
        "n": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "hit_at_1": sum(row["hit_at_1"] for row in known),
        "hit_at_3": sum(row["hit_at_3"] for row in known),
        "known_questions": len(known),
        "p50_ms": median(latencies),
        "p95_ms": latencies[math.ceil(0.95 * len(rows)) - 1],
    }
    print(json.dumps({"summary": summary, "cases": rows}, ensure_ascii=False, indent=2))
    return 0 if summary["passed"] == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
