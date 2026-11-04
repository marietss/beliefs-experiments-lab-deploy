"""Full A bot sessions; test-only choices cover above, equality and mixed zero."""

from fractions import Fraction
import lab_instructions as instructions
from otree.api import Bot, Submission, SubmissionMustFail
from otree.database import db
from lab_persistence import decode_fraction
from . import SectionSplash, FirstBlockSplash, SectionComprehension, SectionComprehension2, BlockStart, Reports, Decision, Result, BlockEnd, presentation


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
            yield SubmissionMustFail(Reports, dict(expected_own_equipment_main=-1, expected_group_average_main=101))
            yield Reports, dict(expected_own_equipment_main=50, expected_group_average_main=50)
        # Config access is confined to these test bots, never participant JS.
        k = p.session.config['ambiguity_thresholds'][str(p.global_block)]
        initial_retirement = (0 if p.local_block == 1 else 100 - k if p.local_block == 2
                              else 100 if p.id_in_group == 1 else 101 - k)
        if p.period <= 5:
            context = presentation.chart_context(p)
            assert 'threshold' not in context
            assert not context['threshold_revealed']
        yield Decision, dict(retirement=initial_retirement if p.period == 1 else 0)
        db.expire_all()
        assert p.period_settled and p.group.settlement_complete
        assert decode_fraction(p.group_mean) == Fraction(p.group.equipment_total, 6)
        if p.period == 5:
            assert p.applied_main_threshold == p.group.threshold == k
            assert p.main_enforcement_applied == (p.local_block != 1)
            assert presentation.outcome_context(p)['threshold'] == k
        yield Result
        if p.period == 10:
            remaining = 100 - initial_retirement
            main = Fraction(175) + Fraction(remaining, 2) if p.local_block != 1 and remaining else 0
            expected = 1000 - Fraction(1, 10) * (initial_retirement ** 2 + remaining ** 2) - main - (75 if remaining else 0)
            assert p.final_equipment == 0
            assert decode_fraction(p.final_block_wallet) == expected
