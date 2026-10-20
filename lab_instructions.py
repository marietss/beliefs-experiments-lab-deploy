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

QUIZ_VERSION = 'lab_comprehension_v1'


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
        c = context(player)
        follow_up = q('follow_up', "Cosa succede se hai ancora attrezzatura rimanente all'accertamento finale dopo il Periodo 10?",
            "Viene imposta una sanzione di 275 punti, tutta l'attrezzatura rimanente viene dismessa automaticamente e il costo separato della dismissione viene sottratto dal tuo portafoglio.",
            "Viene imposta solo una sanzione di 275 punti; l'attrezzatura rimane disponibile.",
            "Dopo il Periodo 10, l'attrezzatura rimanente comporta una sanzione di 275 punti, la dismissione automatica e un costo separato di 0.075 × attrezzatura rimanente². A zero non si applica né la sanzione né il costo di dismissione automatica.")
        if c['is_fixed']:
            result = [
                q('reset', "All'inizio di ogni blocco, con cosa inizi?", '100 unità di attrezzatura e 1000 punti nel tuo portafoglio', '1000 unità di attrezzatura e 100 punti nel tuo portafoglio', 'Ogni blocco inizia con 100 unità di attrezzatura e 1000 punti nel tuo portafoglio.'),
                q('irreversible', "Se dismetti dell'attrezzatura, può tornare disponibile più avanti nello stesso blocco?", 'No', 'Sì', "No. L'attrezzatura dismessa durante un blocco viene rimossa definitivamente dall'uso per il resto di quel blocco."),
                q('period_cost', "Cosa determina il costo della dismissione dell'attrezzatura in un dato periodo?", 'Il numero di unità che dismetti in quel periodo', "Il numero totale di unità che hai dismesso dall'inizio del blocco", 'Il costo in un dato periodo dipende da quante unità dismetti in quel periodo.'),
                q('fixed_positive', "Dopo la tua decisione del Periodo 5 nella Sezione 1, rimangono 50 unità. Quale sanzione viene imposta all'accertamento principale?", "200 punti, indipendentemente dalla media del gruppo. Se non rimanesse attrezzatura, non sarebbe imposta alcuna sanzione all'accertamento principale.", "La sanzione dipende dall'attrezzatura media rimanente del gruppo.", "Nella Sezione 1, la sanzione all'accertamento principale dipende dalla tua attrezzatura rimanente, non dalla media del gruppo. Con 50 unità è 175 + 0.5 × 50 = 200 punti. A zero non viene imposta alcuna sanzione all'accertamento principale."),
                q('fixed_average', "Nella Sezione 1, l'attrezzatura media rimanente del gruppo influisce sull'accertamento principale, sull'accertamento finale o sui punti nel tuo portafoglio?", 'No', 'Sì', 'Nella Sezione 1, la media del gruppo è solo informativa. Non determina nessuno dei due accertamenti o i punti nel tuo portafoglio.'),
                follow_up,
            ]
            result[0]['options'].append(('c', '100 unità di attrezzatura e 100 punti nel tuo portafoglio'))
            result[2]['options'].append(('c', "L'attrezzatura media rimanente del gruppo"))
        elif c['is_ambiguity']:
            result = [
                q('reveal', "Prima dell'accertamento principale, conosci la soglia applicabile a quel blocco?", "No. Non conosci la soglia fino all'accertamento principale.", "Sì. È nota prima dell'inizio del blocco.", "Non conosci la soglia del blocco fino all'accertamento principale, dopo che tutti e sei i responsabili hanno completato le decisioni del Periodo 5 e l'accertamento principale è completato."),
                q('support', 'Quali valori può assumere la soglia?', 'Numeri interi da 40 a 50 unità, estremi inclusi.', 'Solo 45 unità.', 'La soglia è un numero intero da 40 a 50 unità, estremi inclusi.'),
                q('above', "Cosa succede se l'attrezzatura media rimanente del gruppo è maggiore della soglia?", "Non viene imposta alcuna sanzione all'accertamento principale.", "Viene imposta una sanzione all'accertamento principale alle imprese con attrezzatura rimanente.", "Se l'attrezzatura media rimanente del gruppo è maggiore della soglia, non viene imposta alcuna sanzione all'accertamento principale."),
                q('strict_unknown', "Se l'attrezzatura media rimanente del gruppo è uguale alla soglia, cosa succede poi?", "Viene controllata la propria attrezzatura rimanente: se è positiva comporta 175 + 0.5 × la propria attrezzatura rimanente; a zero non viene imposta alcuna sanzione all'accertamento principale.", "La condizione favorevole è soddisfatta e non viene imposta alcuna sanzione all'accertamento principale.", "L'uguaglianza non soddisfa la condizione favorevole. La propria attrezzatura rimanente positiva comporta la sanzione all'accertamento principale. A zero non viene imposta alcuna sanzione all'accertamento principale."),
                q('own_inclusion', "L'attrezzatura della tua impresa è inclusa nell'attrezzatura media rimanente del gruppo?", 'Sì', 'No', 'Sì. La media del gruppo include la tua impresa e le altre cinque imprese.'),
                q('probabilities', "Prima dell'accertamento principale, quali informazioni ricevi su quanto siano probabili i diversi valori della soglia?", 'Non ti vengono fornite informazioni su quanto siano probabili i diversi valori.', 'Ti viene fornita una probabilità per ogni valore possibile.', 'Non ti vengono fornite informazioni su quanto siano probabili i diversi valori.'),
            ]
        else:
            result = [
                q('known', "Cosa succede all'accertamento principale se l'attrezzatura media rimanente del gruppo è maggiore di 45 unità?", "Non viene imposta alcuna sanzione all'accertamento principale.", "Viene imposta una sanzione all'accertamento principale alle imprese con attrezzatura rimanente.", "Se l'attrezzatura media rimanente del gruppo è maggiore di 45 unità, non viene imposta alcuna sanzione all'accertamento principale."),
                q('equality', "Se l'attrezzatura media rimanente del gruppo è esattamente 45 unità, cosa succede poi?", "Viene controllata la propria attrezzatura rimanente; se è positiva comporta la sanzione all'accertamento principale, mentre l'attrezzatura zero è esente.", "Non viene imposta alcuna sanzione all'accertamento principale perché la media ha raggiunto 45.", "La media deve essere strettamente maggiore di 45. L'uguaglianza non soddisfa questa condizione."),
                q('own_inclusion', "L'attrezzatura della tua impresa è inclusa nell'attrezzatura media rimanente del gruppo?", 'Sì', 'No', 'Sì. La media del gruppo include la tua impresa e le altre cinque imprese.'),
                q('zero', "Se la media del gruppo è 45 unità o meno e la tua impresa ha 50 unità rimanenti, a quanto ammonta la sanzione all'accertamento principale?", "200 punti. Con attrezzatura zero non verrebbe imposta alcuna sanzione all'accertamento principale.", '175 punti per ogni impresa, incluse le imprese a zero.', "La sanzione all'accertamento principale è 175 + 0.5 × 50 = 200 punti. Un'impresa con attrezzatura zero non paga alcuna sanzione all'accertamento principale."),
            ]
        if c['is_messages'] and not c['is_policy']:
            result = [
                q('report1', 'Cosa ti chiede di dichiarare la Risposta 1?', "L'attrezzatura che pianifichi di avere rimanente all'accertamento principale.", "Solo l'attrezzatura delle altre cinque imprese.", "La Risposta 1 riguarda l'attrezzatura che pianifichi di avere rimanente dopo la tua decisione del Periodo 5."),
                q('report2', 'Cosa ti chiede di dichiarare la Risposta 2?', "L'attrezzatura media rimanente del gruppo che ti aspetti all'accertamento principale, inclusa la tua impresa.", 'La media attesa del gruppo escludendo la tua impresa.', 'La Risposta 2 riguarda tutte e sei le imprese, inclusa la tua.'),
                q('two_reports', 'Dopo che tutti e sei i responsabili hanno inviato le risposte, quali informazioni vengono mostrate al gruppo?', 'La media anonima e i sei valori individuali anonimi della Risposta 1.', 'Tutte e sei le risposte individuali e le identità dei responsabili.', 'Vengono mostrati la media anonima e i sei valori individuali anonimi della Risposta 1. Le identità non vengono mostrate.'),
                q('private_second', 'La Risposta 2 viene mostrata agli altri responsabili?', 'No. Rimane privata e non fa parte della media pubblica.', 'Sì. Entrambe le risposte sono incluse nella media pubblica.', 'La Risposta 2 rimane privata. Solo la Risposta 1 contribuisce alla media pubblica delle risposte del gruppo.'),
                q('message_role', "Quale attrezzatura determina l'esito dell'accertamento principale?", "L'attrezzatura effettiva rimanente nelle sei imprese, inclusa la tua, non i piani dichiarati.", 'La media pubblica delle risposte del gruppo.', "L'accertamento principale usa l'attrezzatura effettiva rimanente. Le risposte non hanno effetti meccanici sulle sanzioni."),
                q('equality', "Quando non viene imposta alcuna sanzione all'accertamento principale a nessuna impresa?", "Quando la media effettiva del gruppo è maggiore di 45. A 45 o meno, la propria attrezzatura positiva comporta una sanzione all'accertamento principale.", 'Quando la media effettiva del gruppo è 45 o maggiore.', "La media effettiva del gruppo deve essere strettamente maggiore di 45. L'uguaglianza comporta l'applicazione delle sanzioni alle imprese con attrezzatura rimanente positiva."),
            ]
        if c['is_policy']:
            result = [
                q('pool', 'Quali punti entrano nel fondo delle sanzioni del gruppo?', "Solo le sanzioni effettive all'accertamento principale pagate dalle sei imprese.", "Sanzioni all'accertamento principale, costi di dismissione e sanzioni all'accertamento finale.", "Solo le sanzioni effettive all'accertamento principale entrano nel fondo. I costi di dismissione e le sanzioni all'accertamento finale non vi entrano."),
                q('recipient', 'Quali imprese ricevono un trasferimento?', 'Le imprese con attrezzatura rimanente esattamente zero dopo la decisione del Periodo 5.', 'Le imprese con il portafoglio più basso o che raggiungono zero dopo il Periodo 10.', "Il diritto a ricevere un trasferimento dipende dall'avere attrezzatura zero all'accertamento principale, dopo la decisione del Periodo 5."),
                q('share', f"Con {c['policy_share']} redistribuito da un fondo delle sanzioni di 780 punti, quanto riceve ciascuna delle due imprese idonee?", f"{c['example_transfer']} punti.", "L'intero fondo delle sanzioni.", f"L'importo redistribuito è {c['policy_share']} di 780, diviso in parti uguali tra le due imprese idonee."),
                q('no_recipients', "Cosa succede se nessuna impresa ha attrezzatura zero all'accertamento principale?", 'Non avviene alcuna redistribuzione.', "L'importo viene diviso tra tutte e sei le imprese.", 'Se nessuna impresa è idonea, non avviene alcuna redistribuzione.'),
                q('no_double_charge', "Le sanzioni all'accertamento principale vengono addebitate una seconda volta per finanziare la redistribuzione?", "No. Il fondo deriva dalle sanzioni all'accertamento principale già sottratte una volta.", 'Sì. Viene sottratta una quota aggiuntiva.', "La sanzione ordinaria all'accertamento principale viene pagata una sola volta. Non è previsto alcun addebito aggiuntivo per la redistribuzione."),
                q('no_follow_up_pool', "Avviene una redistribuzione all'accertamento finale?", 'No', 'Sì', "La redistribuzione avviene solo all'accertamento principale. Le sanzioni all'accertamento finale e i costi di dismissione automatica non vengono redistribuiti."),
            ]
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
