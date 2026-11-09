from app.evaluation.retrieval_eval import evaluate_cases, load_cases


def test_hybrid_retrieval_meets_development_evaluation_gates(db_session):
    cases = load_cases()
    report = evaluate_cases(db_session, cases, "hybrid")

    assert report["case_count"] >= 20
    assert report["answerable_recall_at_5"] >= 0.90, report
    assert report["abstention_accuracy"] >= 0.95, [item for item in report["details"] if not item["passed"]]
    assert report["access_control_accuracy"] == 1.0, report


def test_evaluation_corpus_covers_answerable_unanswerable_and_access_cases():
    cases = load_cases()
    assert any(case["expected_answerable"] for case in cases)
    assert any(not case["expected_answerable"] for case in cases)
    assert any(case.get("forbidden_document_title") for case in cases)
