"""Standalone 18/24-human M bots: above, equal, and below the Main threshold."""

from fractions import Fraction
import lab_instructions as instructions
from otree.api import Bot, Submission, SubmissionMustFail
from otree.database import db
from lab_persistence import decode_fraction
from . import SectionSplash, FirstBlockSplash, SectionComprehension, SectionComprehension2, BlockStart, Reports, Decision, Result, BlockEnd, public_reports


class PlayerBot(Bot):
    def play_round(self):
        p = self.player
        if p.round_number == 1:
            yield Submission(SectionSplash, timeout_happened=True, check_html=False)
            for page in (SectionComprehension, SectionComprehension2):
                yield SubmissionMustFail(page, {})
                answers = instructions.correct_answers(p)
                yield page, {field: answers[field] for field in page.get_form_fields(p)}
        if p.period == 1:
            if p.local_block == 1:
                yield Submission(FirstBlockSplash, timeout_happened=True, check_html=False)
            else:
                yield BlockStart
            yield SubmissionMustFail(Reports, dict(
                expected_own_equipment_main=-1, expected_group_average_main=101,
            ))
            yield Reports, dict(expected_own_equipment_main=(p.id_in_group - 1 if p.local_block < 3 else int(p.id_in_group == 6)), expected_group_average_main=100)
            db.expire_all()
            assert public_reports.read(p) == (Fraction(5, 2) if p.local_block < 3 else Fraction(1, 6))
        # Test choices only: each group sees above, equality, then mixed zero/positive.
        amount = (0 if p.local_block == 1 else 60 if p.local_block == 2
                  else 100 if p.id_in_group == 1 else 60) if p.period == 1 else 0
        yield Decision, dict(retirement=amount)
        db.expire_all()
        assert p.period_settled and p.group.settlement_complete
        assert decode_fraction(p.group_mean) == Fraction(p.group.equipment_total, 6)
        if p.period == 5:
            assert p.main_enforcement_applied == (p.local_block != 1)
            assert p.applied_main_threshold == p.group.threshold == 40
            assert decode_fraction(p.main_fine) == (
                0 if p.local_block == 1 or p.voluntary_equipment_after == 0
                else Fraction(195) if p.local_block == 2 else 195
            )
            if p.local_block == 2:
                assert p.group.equipment_total == 240
        yield Result
        if p.period == 10:
            yield BlockEnd
            assert p.final_equipment == 0
            expected = (-75 if p.local_block == 1 else Fraction(210) if p.local_block == 2
                        else 0 if p.id_in_group == 1 else 210)
            assert decode_fraction(p.final_block_wallet) == expected
