"""Session 13 (2026-09-17): rulings R6-43 to R6-46.

  phase 1  the rulings are recorded
  phase 2  R6-43 / Codex B1(a): registration is by section (registry.registered_sections, registered-sections.json)
  phase 3  R6-44 / Codex B1(b): BSR-LU-03 is CONFESSIONAL; the override hook combines several rulings on one row"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sjn_recovery import rulings, store, config  # noqa: E402
from sjn_recovery.registry import Registry, bare_tier  # noqa: E402


@pytest.fixture(scope="module")
def reg():
    try:
        return Registry()
    except Exception as e:
        pytest.skip(f"registry unavailable: {e}")


# ---------------------------------------------------------------- phase 1
def test_r6_43_to_r6_46_are_recorded():
    R = rulings.load()["rulings"]
    for key in ("R6-43_registration_by_section", "R6-44_confessed_catechisms", "R6-45_an04_historical_documents_scope",
                "R6-46_session12_confirmations"):
        assert R[key]["status"] == "RATIFIED" and R[key]["ruled"] == "2026-09-17", key
        assert "session 13" in R[key]["source"], key
    assert R["R6-44_confessed_catechisms"]["rows_moved"] == ["BSR-LU-03"]
    assert set(R["R6-46_session12_confirmations"]["items"]) == {"1_an05_guard", "2_rp05_notes", "3_r6_41_interpretations",
                                                               "4_phase2_seat_effects", "5_in_scope"}
