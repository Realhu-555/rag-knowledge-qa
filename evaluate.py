"""评测脚本"""
import json
import time
from src.core.rag_engine import RAGEngine


def load_test_cases(path: str = "evaluation/test_cases.json") -> list[dict]:
    """加载评测用例"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_answer(answer: str, expected_keywords: list[str]) -> dict:
    """评估回答质量"""
    answer_lower = answer.lower()

    hits = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    keyword_score = hits / len(expected_keywords) if expected_keywords else 0

    length_score = min(len(answer) / 100, 1.0)

    has_citation = "[" in answer and "]" in answer
    citation_score = 1.0 if has_citation else 0.5

    total_score = keyword_score * 0.5 + length_score * 0.2 + citation_score * 0.3

    return {
        "keyword_score": round(keyword_score, 2),
        "length_score": round(length_score, 2),
        "citation_score": round(citation_score, 2),
        "total_score": round(total_score, 2),
        "hits": hits,
        "total_keywords": len(expected_keywords)
    }


def run_evaluation():
    """运行评测"""
    print("=" * 60)
    print("RAG 智能问答系统评测")
    print("=" * 60)

    test_cases = load_test_cases()
    print(f"\n加载 {len(test_cases)} 个测试用例\n")

    try:
        engine = RAGEngine()
    except Exception:
        print("无法初始化引擎，跳过评测\n")
        return

    results = []

    for case in test_cases:
        print(f"测试 [{case['id']}] {case['question']}")

        start_time = time.time()
        try:
            result = engine.query(case["question"])
            answer = result.get("answer", "")
            elapsed_ms = int((time.time() - start_time) * 1000)

            evaluation = evaluate_answer(answer, case["expected_keywords"])
            evaluation["question"] = case["question"]
            evaluation["answer"] = answer[:200]
            evaluation["elapsed_ms"] = elapsed_ms
            evaluation["status"] = "success"

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            evaluation = {
                "question": case["question"],
                "status": "error",
                "error": str(e),
                "elapsed_ms": elapsed_ms,
                "total_score": 0
            }

        results.append(evaluation)
        print(f"  得分: {evaluation.get('total_score', 0)} | 耗时: {evaluation.get('elapsed_ms', 0)}ms\n")

    success_results = [r for r in results if r["status"] == "success"]
    if success_results:
        avg_score = sum(r["total_score"] for r in success_results) / len(success_results)
        avg_time = sum(r["elapsed_ms"] for r in success_results) / len(success_results)
        print(f"成功率: {len(success_results)}/{len(results)}")
        print(f"平均得分: {avg_score:.2f}")
        print(f"平均耗时: {avg_time:.0f}ms")

    output_path = "evaluation/results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到 {output_path}")


if __name__ == "__main__":
    run_evaluation()
