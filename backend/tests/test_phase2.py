from phase2.decision.engine import DecisionOutcome, evaluate_decision
from phase2.information.resolver import InformationResolution, InformationStatus, resolve_information


def test_resolve_information_knows_when_information_is_already_present():
    result = resolve_information(
        "What is the current project branch?",
        state={"branch": "feature/work-state"},
        context={"current_work_state": {"branch": "feature/work-state"}},
    )

    assert result.status == InformationStatus.ALREADY_KNOWN
    assert result.needs_research is False
    assert result.provenance


def test_resolve_information_requires_user_decision_for_high_impact_action():
    result = resolve_information(
        "Should I deploy this app to production now?",
        state={"current_problem": "Release is blocked"},
    )

    assert result.status == InformationStatus.USER_DECISION_REQUIRED
    assert result.needs_research is True
    assert result.approval_required is True


def test_resolve_information_uses_discoverable_for_missing_fact():
    result = resolve_information(
        "What is the current default port for this FastAPI app?",
        state={"project": "evi"},
    )

    assert result.status == InformationStatus.DISCOVERABLE
    assert result.needs_research is True
    assert result.research_plan


def test_phase2_proactive_intelligence_detects_research_need_and_high_impact_actions():
    intelligence = InformationResolution()
    opportunities = intelligence.detect_proactive_opportunities({
        "current_problem": "The login flow is failing after deployment",
        "pending_decisions": ["deploy to prod", "approve release"],
        "recent_actions": ["deploy", "rollback"],
    })

    assert any(item["type"] == "research_needed" for item in opportunities)
    assert any(item["requires_user_decision"] for item in opportunities)


def test_evaluate_decision_requires_user_approval_for_release_workflow():
    result = evaluate_decision(
        "Should I deploy this release to production?",
        state={"pending_decisions": ["release to prod"], "current_problem": "Login is failing"},
    )

    assert result.outcome == DecisionOutcome.USER_APPROVAL_REQUIRED
    assert result.approval_required is True
    assert result.needs_research is True
