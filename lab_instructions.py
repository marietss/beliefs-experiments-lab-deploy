"""Participant instruction content and comprehension only; no settlement writes.

Instruction pages live at round 1 inside the substantive apps. General lab
material is hosted by fixed using lab-only general_instructions templates;
legacy online pages/routes are untouched. Quiz process measures live on the
first-round Player: attempts count submissions, errors count incorrect or
missing answers, and question_errors records counts per stable question ID.
Only an allowlisted display context is returned, never session/config objects.
"""
from fractions import Fraction
import json

from lab_policy import configured_rho
from lab_presentation import points, mean_display
import lab_rules as rules

QUIZ_VERSION = 'lab_comprehension_printed_20261026_pairs_v3'

from lab_printed_questions import PRINTED_QUESTIONS


def question(key, prompt, correct, wrong, feedback):
    return dict(id=key, prompt=prompt, options=[('a', correct), ('b', wrong)],
                correct='a', feedback=feedback)


def context(player):
    app = player.subsession.get_folder_name()
    branch = {'endogenous': 'E', 'ambiguity': 'A', 'messages': 'M'}.get(app)
    policy = app == 'policy'
    if policy:
        branch = player.underlying_branch
    rho = configured_rho(player.session.config) if policy else Fraction(0)
    share = 'un terzo' if rho == Fraction(1, 3) else points(rho * 100) + '%'
    return dict(
        instruction_section=3 if policy else 1 if app == 'fixed' else 2,
        section_title=('Sezione con redistribuzione' if policy else {'fixed': 'Sezione fissa',
                       'endogenous': 'Sezione con soglia nota', 'ambiguity': 'Sezione con soglia sconosciuta',
                       'messages': 'Sezione con messaggi pubblici'}[app]),
        is_fixed=app == 'fixed', is_policy=policy,
        is_ambiguity=branch == 'A', is_messages=branch == 'M',
        session_size=player.session.config['lab_session_size'],
        cost_examples=[dict(retirement=d, cost=points(rules.retirement_cost(d))) for d in (10, 20, 25, 50)],
        split_cost=points(2 * rules.retirement_cost(10)),
        **(dict(support_low=40, support_high=50) if branch == 'A' else {}),
        **(dict(policy_share=share, policy_remainder='due terzi' if rho == Fraction(1, 3) else points((1-rho)*100) + '%', example_pool=780, example_recipients=2,
                example_redistribution=mean_display(rho * 780),
                example_transfer=mean_display(rho * 390)) if policy else {}),
    )


def questions(player, *, general=False):
    q = question
    if general:
        result = [
            q('timing', 'Quali scadenze si applicano in ogni blocco?', '10 periodi; Accertamento principale dopo il 5; Accertamento finale dopo il 10.', "Le scadenze degli accertamenti variano da un blocco all'altro.", 'Ogni blocco ha 10 periodi: Accertamento principale dopo il 5 e Accertamento finale dopo il 10.'),
            q('reset', 'Con cosa inizi ogni blocco?', '100 unità di attrezzatura e un portafoglio separato di 1000 punti.', "L'attrezzatura e il portafogli rimasti dal blocco precedente.", "L'attrezzatura viene ripristinata a 100 e il portafoglio a 1000 in ogni blocco."),
            q('irreversible', "L'attrezzatura dismessa può tornare disponibile durante un blocco?", "No; l'attrezzatura può solo restare uguale o diminuire.", 'Sì, se il portafoglio è positivo.', "La dismissione è irreversibile all'interno di un blocco, anche a zero."),
            q('period_cost', 'Dismetti 10 unità ora e 10 in un periodo successivo: qual è il costo totale?', '15 punti.', '30 punti.', 'Ogni dismissione costa 0.075 × 10² = 7.5, quindi il totale è 15.'),
            q('own_inclusion', "Di chi è l'attrezzatura inclusa nella media del gruppo?", 'Di tutti e sei i partecipanti, te incluso.', 'Solo degli altri cinque partecipanti.', 'La media del gruppo include la tua attrezzatura esattamente una volta.'),
            q('wallet', "Un portafoglio basso o negativo limita le scelte di dismissione dell'attrezzatura?", "No; è possibile scegliere qualsiasi numero intero da 0 fino all'attrezzatura attuale.", 'Sì; la dismissione è limitata dal portafoglio.', 'Il portafoglio è un saldo contabile, non un vincolo di liquidità.'),
            q('payment', 'Come viene calcolato il tuo pagamento finale?', '€7.50 + 0.01 euro × il portafoglio finale di un blocco selezionato esternamente.', 'La somma di tutti e nove i portafogli, con un minimo garantito.', 'Un blocco selezionato esternamente determina la componente variabile; il suo portafoglio può essere negativo.'),
            q('selection', 'Quando scopri quale blocco determina il pagamento?', 'Alla fine, dopo tutti e nove i blocchi.', 'Prima di prendere decisioni in quel blocco.', 'Il blocco selezionato rimane sconosciuto durante le decisioni.'),
        ]
    else:
        app = player.subsession.get_folder_name()
        section = {'fixed': 'F', 'endogenous': 'E', 'ambiguity': 'A', 'messages': 'M', 'policy': 'P'}[app]
        return [dict(row, options=list(row['options']), field=f'comprehension_{i}')
                for i, row in enumerate(PRINTED_QUESTIONS[section], 1)]
    prefix = 'general' if general else 'comprehension'
    for i, row in enumerate(result, 1):
        if i % 2 == 0:
            row['options'] = [('a', row['options'][1][1]), ('b', row['options'][0][1])]
            row['correct'] = 'b'
    return [dict(row, field=f'{prefix}_{i}') for i, row in enumerate(result, 1)]


def quiz_fields(player, *, general=False):
    return [q['field'] for q in questions(player, general=general)]


def quiz_context(player, *, general=False):
    rows = questions(player, general=general)
    return dict(context(player), questions=rows, general=general,
                quiz_pages=[dict(number=i//2+1, questions=rows[i:i+2]) for i in range(0, len(rows), 2)])


def check_answers(player, values, *, general=False):
    """Count all submitted incorrect/missing answers, including blank form fields."""
    prefix = 'general' if general else 'comprehension'
    qs = questions(player, general=general)
    errors = [q for q in qs if values.get(q['field']) != q['correct']]
    setattr(player, prefix + '_attempts', getattr(player, prefix + '_attempts') + 1)
    counts = json.loads(getattr(player, prefix + '_question_errors') or '{}')
    for q in errors:
        counts[q['id']] = counts.get(q['id'], 0) + 1
    setattr(player, prefix + '_question_errors', json.dumps(counts, sort_keys=True))
    setattr(player, prefix + '_errors', getattr(player, prefix + '_errors') + len(errors))
    setattr(player, prefix + '_passed', not errors)
    if errors:
        return ' '.join(q['feedback'] for q in errors)


def correct_answers(player, *, general=False):
    """Test/bot answers, kept server-side and never included in page context."""
    return {q['field']: q['correct'] for q in questions(player, general=general)}


def page_quiz_context(player, *, general=False):
    # Strip answer keys before browser rendering, including from nested objects.
    c = quiz_context(player, general=general)
    c['questions'] = [{k: v for k, v in q.items() if k not in ('correct', 'feedback')} for q in c['questions']]
    c['quiz_pages'] = [dict(number=i//2+1, questions=c['questions'][i:i+2]) for i in range(0, len(c['questions']), 2)]
    return c
