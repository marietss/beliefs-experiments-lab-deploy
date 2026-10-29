"""Printed-instruction page gates; no economics, rematching or report disclosure."""
from otree.common import get_models_module
import lab_rules as rules


def admin_only(player, values):
    # oTree skips error_message only for an authenticated admin advancement.
    # These pages have no timer, so participant-supplied timeout flags cannot pass.
    return 'Attendi le indicazioni del ricercatore.'


def initial_splash(player):
    return dict(splash_title='Studio', splash_message='Lo studio inizierà a breve.', show_logo=True)


def section_splash(player):
    section = 3 if player.subsession.get_folder_name() == 'policy' else 2
    return dict(splash_title=f'Sezione {section} — Attendi le nuove istruzioni.', splash_message='', show_logo=False)


def first_block_splash(player):
    app = player.subsession.get_folder_name()
    section = 1 if app == 'fixed' else 3 if app == 'policy' else 2
    return dict(splash_title=f'Blocco {section}.1', splash_message='Attendi l’inizio del blocco.', show_logo=False)


def comprehension_complete(subsession):
    players = subsession.get_players()
    if len(players) != subsession.session.config['lab_session_size'] or not all(p.comprehension_passed for p in players):
        raise ValueError('Every configured participant must pass section comprehension before release.')


def start_block(subsession):
    players = subsession.get_players()
    if len(players) != subsession.session.config['lab_session_size'] or not all(p.period == 1 for p in players):
        raise ValueError('Every configured participant must arrive at the block-start barrier.')
    app = get_models_module(subsession.get_folder_name())
    for player in players:
        app.require_block_ready(player)
    for player in players:
        player.block_entered = True


def result_complete(player, timeout_happened):
    if not player.period_settled or not player.group.settlement_complete:
        raise ValueError('Cannot leave a Result before synchronized settlement.')
    if rules.is_follow_up_period(player.period):
        # Existing completion/export marker, now set on leaving Period-10 Result.
        player.block_feedback_submitted = True


def results_complete(group):
    players = group.get_players()
    if len(players) != rules.GROUP_SIZE or not all(p.period_settled for p in players) or not group.settlement_complete:
        raise ValueError('All six participants must finish the settled Result.')


def block_summary_context(player):
    """Anonymous end-of-block feedback, read only after the session barrier."""
    from lab_persistence import decode_fraction
    from lab_presentation import points

    if not rules.is_follow_up_period(player.period) or not player.subsession.block_barrier_complete:
        raise ValueError('Block summary requires the completed session-wide block barrier.')
    peers = player.group.get_players()
    if len(peers) != rules.GROUP_SIZE:
        raise ValueError('Block feedback requires the six firms from the completed block.')
    main_round = player.round_number - player.period + rules.MAIN_CHECK_PERIOD
    rows = []
    for peer in sorted(peers, key=lambda p: p.id != player.id):
        main = peer.in_round(main_round)
        if not (peer.period_settled and peer.group.settlement_complete
                and main.period_settled and main.group.settlement_complete):
            raise ValueError('Block feedback requires settled Main and Final outcomes.')
        own = peer.id == player.id
        rows.append(dict(is_own=own, company='TU' if own else 'Altra azienda',
                         main_equipment=main.voluntary_equipment_after,
                         points=points(decode_fraction(peer.final_block_wallet))))
    app = player.subsession.get_folder_name()
    return dict(summary_section=1 if app == 'fixed' else 3 if app == 'policy' else 2,
                summary_rows=rows)
