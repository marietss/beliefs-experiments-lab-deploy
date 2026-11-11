"""Full 18/24-person oTree bot route; bots are test humans, never app fallbacks."""

from fractions import Fraction
import lab_instructions as instructions
from otree.api import Bot, Submission, SubmissionMustFail
from otree.database import db
from lab_persistence import decode_fraction
from . import PracticeDecision, PracticeComplete, ExperimentSplash, FirstBlockSplash, SectionComprehension, SectionComprehension2, SectionComprehension3, BlockStart, Reports, Decision, Result, BlockEnd


class PlayerBot(Bot):
    def play_round(self):
        p = self.player
        if p.round_number == 1:
            yield Submission(ExperimentSplash, timeout_happened=True, check_html=False)
            yield Submission(PracticeDecision, timeout_happened=True, check_html=False)
            yield PracticeComplete
            for page in (SectionComprehension, SectionComprehension2, SectionComprehension3):
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
            yield Reports, dict(expected_own_equipment_main=50, expected_group_average_main=50)
        # Exercise zero equipment, exact fractional cost, and negative wallets.
        mode = p.participant.id_in_session % 3
        retirement = (100 if mode == 0 else 1 if mode == 1 else 0) if p.period == 1 else 0
        yield Decision, dict(retirement=retirement)
        # HTTP requests settle in separate ORM sessions; refresh test observations.
        db.expire_all()
        assert p.period_settled and p.group.settlement_complete
        assert decode_fraction(p.group_mean) == Fraction(p.group.equipment_total, 6)
        yield Result
        if p.period == 10:
            assert p.final_equipment == 0
            assert decode_fraction(p.final_block_wallet) == (
                Fraction(0) if mode == 0 else Fraction('-279.7') if mode == 1 else Fraction(-300)
            )
        if p.period == 10:
            yield BlockEnd
