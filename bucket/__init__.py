"""Experimental individual task. Integer cents; only lab_payment writes payoff."""
import json
import time
from otree.api import BaseConstants, BaseSubsession, BaseGroup, BasePlayer, Page, models
from otree.database import db


class C(BaseConstants):
    NAME_IN_URL = 'bucket'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    NUM_BALLS = 50
    TASK_SECONDS = 300
    BLUE_CENTS = 5
    YELLOW_CENTS = 10


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    balls_blue = models.IntegerField(initial=0)
    balls_yellow = models.IntegerField(initial=0)
    balls_placed = models.IntegerField(initial=0)
    bucket_payoff_cents = models.IntegerField(initial=0)
    timed_out = models.BooleanField(initial=False)
    task_started_at = models.FloatField(blank=True)
    task_deadline = models.FloatField(blank=True)
    completed = models.BooleanField(initial=False)
    task_finished_at = models.FloatField(blank=True)
    allocation_sequence = models.LongStringField(initial='[]')
    allocation_times = models.LongStringField(initial='[]')


def creating_session(subsession):
    import lab_route
    if subsession.session.config['app_sequence'] != lab_route.payment_sequence(subsession.session.config['branch']):
        raise ValueError('Bucket requires the complete lab route, before survey and payment.')


def locked(player):
    # PostgreSQL row lock also protects against concurrent tabs/workers. oTree
    # 6.0.15 serializes synchronous live calls; never rely on client disabling.
    return Player.objects_filter(id=player.id).populate_existing().with_for_update().one()


def validate(player):
    history = json.loads(player.allocation_sequence)
    times = json.loads(player.allocation_times)
    if (player.balls_placed != player.balls_blue + player.balls_yellow
            or not 0 <= player.balls_placed <= C.NUM_BALLS
            or min(player.balls_blue, player.balls_yellow) < 0
            or player.bucket_payoff_cents != C.BLUE_CENTS * player.balls_blue + C.YELLOW_CENTS * player.balls_yellow
            or len(history) != player.balls_placed or len(times) != player.balls_placed
            or [e['ball'] for e in history] != list(range(1, player.balls_placed + 1))
            or sum(e['bucket'] == 'blue' for e in history) != player.balls_blue
            or sum(e['bucket'] == 'yellow' for e in history) != player.balls_yellow
            or [e['elapsed_seconds'] for e in history] != times):
        raise ValueError('Inconsistent bucket allocation record.')


def start(player, now=None):
    now = time.time() if now is None else now
    player = locked(player)
    if player.field_maybe_none('task_deadline') is None:
        player.task_started_at = now
        player.task_deadline = now + C.TASK_SECONDS
    db.commit()


def expire(player, now):
    if (not player.completed and player.field_maybe_none('task_deadline') is not None
            and now >= player.task_deadline):
        player.timed_out = player.balls_placed < C.NUM_BALLS
        player.completed = True
        player.task_finished_at = player.task_deadline


def state(player, now=None):
    now = time.time() if now is None else now
    validate(player)
    deadline = player.field_maybe_none('task_deadline')
    return dict(balls_blue=player.balls_blue, balls_yellow=player.balls_yellow,
                balls_placed=player.balls_placed, balls_remaining=C.NUM_BALLS-player.balls_placed,
                blue_earnings_cents=C.BLUE_CENTS*player.balls_blue,
                yellow_earnings_cents=C.YELLOW_CENTS*player.balls_yellow,
                total_earnings_cents=player.bucket_payoff_cents,
                seconds_remaining=max(0, deadline-now) if deadline is not None and not player.completed else 0,
                done=player.completed, timed_out=player.timed_out)


def receive(player, data, now=None):
    player = locked(player)
    now = time.time() if now is None else now
    if player.field_maybe_none('task_deadline') is None:
        raise ValueError('Bucket instructions must be completed before allocation.')
    expire(player, now)
    if (not player.completed and isinstance(data, dict) and data.get('action') == 'allocate'
            and data.get('bucket') in ('blue', 'yellow')
            and type(data.get('expected_index')) is int
            and data['expected_index'] == player.balls_placed + 1
            and player.balls_placed < C.NUM_BALLS):
        color = data['bucket']
        if color == 'blue':
            player.balls_blue += 1
        else:
            player.balls_yellow += 1
        player.balls_placed += 1
        player.bucket_payoff_cents = C.BLUE_CENTS*player.balls_blue + C.YELLOW_CENTS*player.balls_yellow
        elapsed = round(max(0, now-player.task_started_at), 3)
        player.allocation_sequence = json.dumps(json.loads(player.allocation_sequence) + [
            dict(ball=player.balls_placed, bucket=color, elapsed_seconds=elapsed)])
        player.allocation_times = json.dumps(json.loads(player.allocation_times) + [elapsed])
        if player.balls_placed == C.NUM_BALLS:
            player.completed = True
            player.task_finished_at = now
    result = state(player, now)
    db.commit()  # durable before acknowledging a drop, including replay/timeout
    return result


def payment_bonus(participant):
    player = Player.objects_get(participant=participant, round_number=1)
    validate(player)
    if not player.completed:
        raise ValueError('Bucket must be completed before final payment.')
    if player.payoff != 0:
        raise ValueError('Bucket payoff must be credited only through lab_payment.')
    return player.bucket_payoff_cents


class BucketInstructions(Page):
    @staticmethod
    def before_next_page(player, timeout_happened):
        start(player)


class BucketTask(Page):
    @staticmethod
    def get_timeout_seconds(player):
        deadline = player.field_maybe_none('task_deadline')
        if deadline is None:
            raise ValueError('Bucket timer has not been started.')
        return max(0, deadline-time.time())

    @staticmethod
    def js_vars(player):
        return dict(bucket=receive(player, dict(action='sync')))

    @staticmethod
    def live_method(player, data):
        return {player.id_in_group: receive(player, data)}

    @staticmethod
    def error_message(player, values):
        if not state(player)['done'] and time.time() < player.task_deadline:
            return 'Completa il task o attendi lo scadere del tempo.'

    @staticmethod
    def before_next_page(player, timeout_happened):
        player = locked(player)
        now = time.time()
        expire(player, now)
        if not player.completed:
            if not timeout_happened:
                raise ValueError('Cannot leave an unfinished bucket task.')
            # Native/admin forced timeout ends only this individual task.
            player.completed = True
            player.timed_out = True
            player.task_finished_at = now
        validate(player)
        db.commit()


class BucketComplete(Page):
    @staticmethod
    def error_message(player, values):
        if not player.completed:
            return 'Completa prima il task individuale.'


page_sequence = [BucketInstructions, BucketTask, BucketComplete]
