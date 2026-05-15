"""Tests for 5-dimensional Compass scorer (P1)."""
import pytest

from freedom_theory.extensions.compass import CompassScore, score_action
from freedom_theory.kernel.entities import AgentType, Entity, Resource, ResourceType
from freedom_theory.kernel.verifier import Action


@pytest.fixture
def bot():
    return Entity("Bot", AgentType.MACHINE)


def test_compass_score_dataclass_fields():
    """CompassScore has all 5 dimensional fields."""
    s = CompassScore(0.0, 0.0, 0.0, 0.0, 0.0)
    assert hasattr(s, "rights_violations_delta")
    assert hasattr(s, "voluntary_order_delta")
    assert hasattr(s, "coercion_delta")
    assert hasattr(s, "ownership_clarity_delta")
    assert hasattr(s, "sovereignty_delta")


def test_sovereign_safe_false_when_delta_positive():
    """sovereign_safe=False if sovereignty_delta > 0."""
    s = CompassScore(0.0, 0.0, 0.0, 0.0, 1.0)
    assert not s.sovereign_safe


def test_sovereign_safe_true_when_delta_zero():
    """sovereign_safe=True if sovereignty_delta == 0."""
    s = CompassScore(0.0, 0.0, 0.0, 0.0, 0.0)
    assert s.sovereign_safe


def test_score_action_coercive_action(bot):
    """Coercive action has coercion_delta > 0 and negative composite."""
    action = Action("coerce", bot, coerces=True)
    score = score_action(action)
    assert score.coercion_delta > 0
    assert score.composite < 0


def test_score_action_sovereignty_increasing(bot):
    """Sovereignty-increasing action: sovereign_safe=False."""
    action = Action("expand", bot, increases_machine_sovereignty=True)
    score = score_action(action)
    assert not score.sovereign_safe
    assert score.composite < 0


def test_score_action_benign(bot):
    """Benign action: all deltas zero."""
    action = Action("read", bot)
    score = score_action(action)
    assert score.sovereignty_delta == 0.0
    assert score.coercion_delta == 0.0
    assert score.sovereign_safe
