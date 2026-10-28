"""Server-validated printed question pairs; reuse existing quiz data fields.

Validation is read-only. Only the enclosing HTTP POST records one submission.
Failed POSTs redirect to GET, so refreshing feedback never resubmits answers.
No model schema, economic calculation, wait or experimenter gate is changed.
"""
from contextvars import ContextVar
import json

from otree.api import Page
from otree.constants import redisplay_with_errors_http_header, get_param_truth_value
from starlette.datastructures import FormData, UploadFile
from starlette.responses import RedirectResponse

import lab_instructions as instructions

_SUBMISSION = ContextVar('lab_comprehension_submission', default=None)
_FEEDBACK = 'lab_comprehension_feedback_v1'
_ADMIN_PAIRS = 'lab_comprehension_admin_pairs_v1'


def pair_questions(player, number):
    return instructions.questions(player)[2 * (number - 1):2 * number]


def pair_feedback(player, values, number):
    """Pure validation, including when oTree validates the same form twice."""
    pending = _SUBMISSION.get()
    if pending is not None:
        pending.setdefault('values', dict(values))
    wrong = [q for q in pair_questions(player, number) if values.get(q['field']) != q['correct']]
    return ' '.join(q['feedback'] for q in wrong) or None


def record_submission(player, values, number):
    rows = pair_questions(player, number)
    wrong = [q for q in rows if values.get(q['field']) != q['correct']]
    counts = json.loads(player.comprehension_question_errors or '{}')
    for q in instructions.questions(player):
        counts.setdefault(q['id'], 0)
    for q in wrong:
        counts[q['id']] += 1
    player.comprehension_question_errors = json.dumps(counts, sort_keys=True)
    player.comprehension_attempts += 1
    player.comprehension_errors += len(wrong)
    # Keep both selections, including the correct half of an unsuccessful pair.
    for q in rows:
        value = values.get(q['field'])
        setattr(player, q['field'], value if value in dict(q['options']) else '')
    if wrong:
        player.comprehension_passed = False
        player.participant.vars[_FEEDBACK] = dict(
            app=player.subsession.get_folder_name(), page=number,
            wrong=[q['id'] for q in wrong],
        )
    else:
        player.participant.vars.pop(_FEEDBACK, None)
    return bool(wrong)


def saved_feedback(player, number):
    flash = player.participant.vars.get(_FEEDBACK, {})
    if flash.get('app') != player.subsession.get_folder_name() or flash.get('page') != number:
        return []
    return [q['feedback'] for q in pair_questions(player, number) if q['id'] in flash.get('wrong', [])]


def pair_context(player, number):
    all_rows = instructions.questions(player)
    rows = [dict({k: v for k, v in q.items() if k not in ('correct', 'feedback')},
                 selected=player.field_maybe_none(q['field']) or '')
            for q in pair_questions(player, number)]
    return dict(instruction_section=1 if player.subsession.get_folder_name() == 'fixed' else
                3 if player.subsession.get_folder_name() == 'policy' else 2,
                questions=rows, feedbacks=saved_feedback(player, number),
                question_first=2 * number - 1, question_last=2 * number,
                question_total=len(all_rows))


def accept_pair(player, number, admin_advanced=False):
    rows = instructions.questions(player)
    app = player.subsession.get_folder_name()
    overrides = player.participant.vars.get(_ADMIN_PAIRS, {})
    cleared = overrides.get(app, [])
    if admin_advanced:
        # Administrative clearance is not a correct answer. Preserve raw answers
        # and all counters, and retain an explicit record of the bypassed pair.
        cleared = sorted(set(cleared + [number]))
        player.participant.vars[_ADMIN_PAIRS] = {**overrides, app: cleared}
        player.participant.vars.pop(_FEEDBACK, None)
    prefix = rows[:2 * number]
    if any(player.field_maybe_none(q['field']) != q['correct']
           for index, q in enumerate(prefix) if index // 2 + 1 not in cleared):
        raise ValueError('Every question in this and preceding pairs must be correct.')
    # Existing barrier clearance flag; raw answers and the admin record retain
    # the distinction between answered correctly and advanced by the researcher.
    player.comprehension_passed = len(prefix) == len(rows)


class ComprehensionPair(Page):
    template_name = 'lab/ComprehensionPair.html'
    form_model = 'player'

    def post_handle_form(self, post_data):
        # No page timer exists: oTree sets this flag only for authenticated admin
        # advancement. Use its native progression, without auto-filling answers.
        if self.timeout_happened:
            return None
        # WTForms otherwise reuses a saved value for an omitted StringField.
        # Invalid/oversized/duplicate values are missing answers, not a reason
        # to bypass our printed feedback or the single-POST accounting path.
        rows = pair_questions(self.player, self.pair_number)
        fields = {q['field'] for q in rows}
        items = [(key, value) for key, value in post_data.multi_items() if key not in fields]
        for q in rows:
            values = post_data.getlist(q['field'])
            value = values[0] if len(values) == 1 else ''
            if not isinstance(value, str) or value not in dict(q['options']):
                for submitted in values:
                    if isinstance(submitted, UploadFile):
                        submitted.file.close()
                value = ''
            items.append((q['field'], value))
        return super().post_handle_form(FormData(items))

    def post(self):
        pending = {}
        token = _SUBMISSION.set(pending)
        player = self.player
        try:
            response = super().post()
            if 'values' in pending and record_submission(player, pending['values'], self.pair_number):
                return RedirectResponse(self.request.url.path, status_code=303)
            return response
        finally:
            _SUBMISSION.reset(token)

    def get(self):
        response = super().get()
        if saved_feedback(self.player, self.pair_number):
            response.headers[redisplay_with_errors_http_header] = get_param_truth_value
        return response


def pair_page(number):
    """Bind each real oTree Page to one immutable pair of printed items."""
    class BoundPair(ComprehensionPair):
        pair_number = number
        is_displayed = staticmethod(lambda player: player.round_number == 1)
        get_form_fields = staticmethod(lambda player: [q['field'] for q in pair_questions(player, number)])
        vars_for_template = staticmethod(lambda player: pair_context(player, number))
        error_message = staticmethod(lambda player, values: pair_feedback(player, values, number))
        before_next_page = staticmethod(lambda player, timeout_happened: accept_pair(player, number, timeout_happened))
    return BoundPair
