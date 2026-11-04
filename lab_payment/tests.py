"""Full-route bot receipt and precise admin-agreement assertions."""
from decimal import Decimal
from otree.api import Bot
from otree.database import db
import lab_cash as cash
from lab_bot_checks import assert_participant_finished
from . import Payment


class PlayerBot(Bot):
    def play_round(self):
        p = self.player
        assert_participant_finished(p)
        record = cash.finalize(p)
        assert set(p.participant.vars[cash.WALLETS_KEY]) == cash.BLOCK_KEYS
        assert p.finalized and record['finalized']
        assert Decimal(p.participant.payoff_plus_participation_fee()) == Decimal(record['final_eur_cents']) / 100
        before = dict(record)
        assert cash.finalize(p) == before
        # The receipt is terminal: verify its GET response without inventing a submit.
        assert p.participant._current_page_name == Payment.__name__
        assert 'id="total-payment"' in self.html
        db.expire_all()
        assert cash.finalize(p) == before
        if p.participant.id_in_session == 1:
            print(f'Payment verified: {p.session.config["name"]}, '
                  f'{p.session.num_participants} complete nine-block ledgers, exact/admin EUR agreement.')
