"""Unit tests for tools/readiness.py. Stdlib unittest, tempfile-backed."""

from __future__ import annotations

import sys
import tempfile
import shutil
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import pipeline  # noqa: E402
import readiness  # noqa: E402

TODAY = date(2026, 6, 28)


def row(**kw) -> dict:
    base = {k: "" for k in pipeline.CANONICAL_HEADER}
    base.update(kw)
    return base


# Capabilities matching current reality (configs/capabilities.json).
CAPS = readiness.DEFAULT_CAPS


class RequirementsAndBlockersTests(unittest.TestCase):
    def test_federal_with_sam_inactive_is_blocker(self) -> None:
        r = row(title="Bed mattress", source="SAM.gov", buyer="Dept of Defense Army")
        self.assertIn("SAM Active (federal)", readiness.requirements_for(r))
        self.assertIn("SAM not Active", readiness.blockers_for(r, CAPS))

    def test_federal_with_sam_active_is_met(self) -> None:
        caps = dict(CAPS, sam_active=True)
        r = row(title="Bed mattress", source="SAM.gov", buyer="Dept of Defense Army")
        self.assertEqual(readiness.blockers_for(r, caps), [])

    def test_brand_norix_unauthorized_is_blocker(self) -> None:
        r = row(title="Norix BN Furniture - Statewide", trigger_terms="furniture; Norix")
        reqs = readiness.requirements_for(r)
        self.assertIn("brand authorization: Norix", reqs)
        self.assertIn("brand: Norix not authorized", readiness.blockers_for(r, CAPS))

    def test_authorized_brand_is_met(self) -> None:
        caps = dict(CAPS, brand_authorizations=["Norix", "Restonic"])
        r = row(title="Norix BN Furniture")
        self.assertEqual(readiness.blockers_for(r, caps), [])

    def test_in_region_correctional_mattress_no_blocker(self) -> None:
        # No federal source, no brand restriction, no GPO, no bonding.
        r = row(title="Correctional mattresses for county jail",
                buyer="Harris County, TX", primary_products="mattresses")
        self.assertEqual(readiness.requirements_for(r), [])
        self.assertEqual(readiness.blockers_for(r, CAPS), [])

    def test_gpo_vizient_not_eligible_is_blocker(self) -> None:
        r = row(title="Mattresses via Vizient contract", buyer="Hospital System")
        self.assertIn("GPO eligibility: Vizient", readiness.requirements_for(r))
        self.assertIn("GPO: Vizient not eligible", readiness.blockers_for(r, CAPS))

    def test_gpo_eandi_eligible_is_met(self) -> None:
        r = row(title="Residence hall mattresses", notes="awarded via E&I cooperative")
        self.assertIn("GPO eligibility: E&I", readiness.requirements_for(r))
        self.assertNotIn("GPO: E&I not eligible", readiness.blockers_for(r, CAPS))

    def test_bonding_required_is_blocker(self) -> None:
        r = row(title="Mattresses statewide", notes="A payment bond is required.")
        self.assertIn("bonding", readiness.requirements_for(r))
        self.assertIn("bonding required (not bonded)", readiness.blockers_for(r, CAPS))

    def test_fire_retardant_cert_is_met_not_blocker(self) -> None:
        r = row(title="Correctional mattresses",
                notes="must meet 16 CFR 1633 and FR fluid-proof covers")
        self.assertIn("16 CFR 1633 (fire-retardant)", readiness.requirements_for(r))
        # cfr_1633 is true in our capabilities -> satisfied -> not a blocker.
        self.assertEqual(
            [b for b in readiness.blockers_for(r, CAPS) if "1633" in b], [])

    def test_tb117_detected_and_met(self) -> None:
        r = row(title="Mattresses", notes="meets California TB 117 flammability")
        self.assertIn("CAL TB 117 (flammability)", readiness.requirements_for(r))
        self.assertEqual(
            [b for b in readiness.blockers_for(r, CAPS) if "TB 117" in b], [])


class LoadCapabilitiesTests(unittest.TestCase):
    def test_loads_real_file(self) -> None:
        caps = readiness.load_capabilities()
        # SAM registration Active since 2026-07-17.
        self.assertTrue(caps["sam_active"])
        self.assertTrue(caps["cfr_1633"])
        self.assertIn("Restonic", caps["brand_authorizations"])

    def test_missing_file_falls_back_to_default(self) -> None:
        caps = readiness.load_capabilities(ROOT / "configs" / "does_not_exist.json")
        self.assertEqual(caps, readiness.DEFAULT_CAPS)


class AnnotateTests(unittest.TestCase):
    def test_annotate_sets_gate_columns(self) -> None:
        blocked = row(opportunity_id="fed-1", status="watching",
                      title="Mattresses", source="SAM.gov", buyer="US Army")
        clean = row(opportunity_id="clean-1", status="watching",
                    title="Correctional mattresses", buyer="Harris County, TX")
        rows = [blocked, clean]
        updates = readiness.annotate(rows, CAPS, TODAY)

        self.assertEqual(blocked["gate_status"], "blocked")
        self.assertEqual(blocked["procurement_risk"], "blocker")
        self.assertEqual(blocked["compliance_blocker"], "SAM not Active")
        self.assertEqual(clean["gate_status"], "bid_ready")
        self.assertEqual(clean["procurement_risk"], "")
        self.assertEqual(clean["compliance_blocker"], "")
        self.assertEqual(len(updates), 2)
        # last_reviewed stamped on changed rows.
        self.assertEqual(blocked["last_reviewed"], "2026-06-28")

    def test_annotate_clears_stale_blocker(self) -> None:
        r = row(opportunity_id="x", title="Mattresses", buyer="Harris County, TX",
                procurement_risk="blocker", gate_status="blocked",
                compliance_blocker="SAM not Active")
        readiness.annotate([r], CAPS, TODAY)
        self.assertEqual(r["procurement_risk"], "")
        self.assertEqual(r["gate_status"], "bid_ready")
        self.assertEqual(r["compliance_blocker"], "")

    def test_annotate_preserves_operator_risk(self) -> None:
        r = row(opportunity_id="x", title="Mattresses", buyer="Harris County, TX",
                procurement_risk="medium")
        readiness.annotate([r], CAPS, TODAY)
        self.assertEqual(r["procurement_risk"], "medium")

    def test_round_trip_via_read_write(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(tmp), True)
        active = tmp / "_pipeline.csv"
        seed = [row(opportunity_id="fed-1", status="watching", title="Mattresses",
                    source="SAM.gov", buyer="US Army")]
        pipeline.write_rows_atomic(active, seed)

        _, rows = pipeline.read_rows(active)
        readiness.annotate(rows, CAPS, TODAY)
        pipeline.write_rows_atomic(active, rows)

        _, reread = pipeline.read_rows(active)
        self.assertEqual(reread[0]["gate_status"], "blocked")
        self.assertEqual(reread[0]["compliance_blocker"], "SAM not Active")


class BacklogTests(unittest.TestCase):
    def test_sam_ranks_first_when_federal_channels_carry_win_score(self) -> None:
        # Three recurring federal channels gated by SAM, each carrying win_score.
        fed = [
            row(opportunity_id=f"fed-{i}", status="watching", title="Mattresses",
                source="SAM.gov", buyer="US Army", win_score=str(ws))
            for i, ws in enumerate((40, 35, 30), 1)
        ]
        # A Norix brand row with smaller gated win_score.
        norix = row(opportunity_id="norix-1", status="watching",
                    title="Norix BN Furniture", win_score="20")
        ranked = readiness.backlog(fed + [norix], [], CAPS)

        self.assertEqual(ranked[0][0], "SAM not Active")
        self.assertEqual(ranked[0][1], 105)   # 40 + 35 + 30
        self.assertEqual(ranked[0][2], 3)
        self.assertEqual(ranked[1][0], "brand: Norix not authorized")

    def test_blank_win_score_counts_as_zero(self) -> None:
        rows = [row(opportunity_id="fed-1", status="watching", title="Mattresses",
                    source="SAM.gov", buyer="US Army")]
        ranked = readiness.backlog(rows, [], CAPS)
        self.assertEqual(ranked[0], ("SAM not Active", 0, 1, ["fed-1"]))

    def test_closed_rows_excluded(self) -> None:
        rows = [row(opportunity_id="fed-1", status="no-bid", title="Mattresses",
                    source="SAM.gov", buyer="US Army", win_score="99")]
        self.assertEqual(readiness.backlog(rows, [], CAPS), [])

    def test_deterministic_tie_break(self) -> None:
        # Two blockers with equal win + count: ordered by blocker name.
        rows = [
            row(opportunity_id="a", status="watching", title="Mattresses via Vizient"),
            row(opportunity_id="b", status="watching", title="Norix BN Furniture"),
        ]
        ranked = readiness.backlog(rows, [], CAPS)
        names = [b for b, *_ in ranked]
        self.assertEqual(names, sorted(names))


class CliTests(unittest.TestCase):
    def _run(self, *argv: str) -> tuple[int, str]:
        import io
        from contextlib import redirect_stdout, redirect_stderr
        out, err = io.StringIO(), io.StringIO()
        rc = -1
        with redirect_stdout(out), redirect_stderr(err):
            try:
                rc = readiness.main(list(argv))
            except SystemExit as exc:
                rc = int(exc.code) if exc.code is not None else 0
        return rc, out.getvalue() + err.getvalue()

    def test_dry_run_writes_nothing(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(tmp), True)
        active = tmp / "_pipeline.csv"
        pipeline.write_rows_atomic(active, [
            row(opportunity_id="fed-1", status="watching", title="Mattresses",
                source="SAM.gov", buyer="US Army")])
        before = active.read_text(encoding="utf-8")

        rc, out = self._run("annotate", "--active", str(active), "--dry-run")
        self.assertEqual(rc, 0, out)
        self.assertIn("dry-run", out)
        self.assertEqual(active.read_text(encoding="utf-8"), before)

    def test_annotate_writes(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(tmp), True)
        active = tmp / "_pipeline.csv"
        pipeline.write_rows_atomic(active, [
            row(opportunity_id="fed-1", status="watching", title="Mattresses",
                source="SAM.gov", buyer="US Army")])

        rc, out = self._run("annotate", "--active", str(active), "--today", "2026-06-28")
        self.assertEqual(rc, 0, out)
        _, rows = pipeline.read_rows(active)
        # Real capabilities have sam_active=true (2026-07-17), so the federal
        # row is not blocked; the write is proven by the stamped gate columns.
        self.assertEqual(rows[0]["gate_status"], "bid_ready")
        self.assertEqual(rows[0]["compliance_blocker"], "")
        self.assertEqual(rows[0]["last_reviewed"], "2026-06-28")


if __name__ == "__main__":
    unittest.main()
