"""One individual, non-remunerated questionnaire after the nine lab blocks.

The six falk_* items adapt the supplied Italian (Italy) Global Preferences
Survey to second-person Italian. This is not a verbatim validated translation.
See README.md for the source and item identifiers (never shown to participants).
"""
from otree.api import BaseConstants, BaseSubsession, BaseGroup, BasePlayer, Page, models

import lab_route


class C(BaseConstants):
    NAME_IN_URL = 'survey'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


WILLING_ENDPOINTS = ('Per niente disposto/a a farlo', 'Molto disposto/a a farlo')
DESCRIBE_ENDPOINTS = ('Non mi descrive per niente', 'Mi descrive perfettamente')
SLIDERS = {
    'experiment_liking': dict(label='Quanto ti è piaciuto partecipare a questo esperimento?',
                              endpoints=('Per nulla', 'Moltissimo')),
    'experiment_clarity': dict(label="Quanto ti sono sembrate chiare le istruzioni e le schermate dell'esperimento?",
                               endpoints=('Per nulla chiare', 'Del tutto chiare')),
    'falk_future': dict(label='Quanto sei disposto/a a rinunciare a qualcosa da cui trai beneficio oggi per beneficiarne maggiormente in futuro?',
                        endpoints=WILLING_ENDPOINTS),
    'falk_risk': dict(label='In generale, quanto sei disposto/a o non disposto/a a correre dei rischi?',
                      help='Per favore, dammi una risposta utilizzando una scala da 0 a 10, dove 0 significa che sei “assolutamente non disposto/a a correre rischi” e 10 significa che sei “completamente disposto/a a correre rischi”. Puoi utilizzare qualsiasi numero da 0 a 10.',
                      endpoints=('Assolutamente non disposto/a a correre rischi', 'Completamente disposto/a a correre rischi')),
    'falk_giving': dict(label='Quanto sei disposto/a a donare per una giusta causa senza aspettarti nulla in cambio?',
                        endpoints=WILLING_ENDPOINTS),
    'falk_favour': dict(label='Quando qualcuno mi fa un favore sono disposto/a a restituirglielo.',
                        endpoints=DESCRIBE_ENDPOINTS),
    'falk_revenge': dict(label='Se vengo trattato/a molto ingiustamente, mi vendicherò alla prima occasione, anche se ci sarà un costo per farlo.',
                         endpoints=DESCRIBE_ENDPOINTS),
    'falk_intentions': dict(label='Presumo che le persone abbiano solo le migliori intenzioni.',
                            endpoints=DESCRIBE_ENDPOINTS),
}


def scale(name):
    return models.IntegerField(min=0, max=10, label=SLIDERS[name]['label'])


def non_whitespace_length(value):
    return sum(not character.isspace() for character in (value or ''))


class Player(BasePlayer):
    experiment_liking = scale('experiment_liking')
    experiment_clarity = scale('experiment_clarity')
    experiment_clarity_improvement = models.LongStringField(blank=True, label='Come miglioreresti le istruzioni per renderle più chiare?')
    # Empty text is checked by the exact minimum-length validator below, rather
    # than the generic blank validator. Both responses remain mandatory.
    experiment_perceived_purpose = models.LongStringField(blank=True, label="Secondo te, qual era l'oggetto principale dell'esperimento? Descrivilo brevemente con parole tue.")
    experiment_changes = models.LongStringField(blank=True, label="C'è qualcosa che cambieresti per rendere l'esperimento più chiaro o più semplice da svolgere? Se non cambieresti nulla, spiegane brevemente il motivo.")
    gender = models.StringField(label='Con quale genere ti identifichi?',
                                choices=['Uomo', 'Donna', 'Altro', 'Preferisco non rispondere'])
    age = models.IntegerField(min=18, max=100, label='Quanti anni hai?')
    country_birth = models.StringField(label='In quale Paese sei nato/a?')
    country_residence = models.StringField(label='In quale Paese si trova la tua residenza permanente attuale?')
    university_affiliation = models.StringField(label='Qual è il tuo corso di studio o il dipartimento/struttura a cui sei affiliato/a?')
    university_status = models.StringField(label='Qual è la tua situazione attuale?', choices=[
        'Laurea triennale', 'Laurea magistrale', 'Laurea magistrale a ciclo unico',
        'Master', 'Dottorato di ricerca', 'Personale docente o ricercatore',
        'Personale tecnico-amministrativo', 'Altro', 'Preferisco non rispondere'])
    unibo_time = models.StringField(label="Da quanto tempo studi o lavori a Bologna?", choices=[
        'Questo è il mio primo anno', 'Questo è il mio secondo anno', 'Questo è il mio terzo anno',
        'Questo è il mio quarto anno', 'Da più di quattro anni', 'Preferisco non rispondere'])
    previous_experiment_experience = models.StringField(label='Prima di oggi, quante volte avevi già partecipato a un esperimento economico in laboratorio o online?', choices=[
        'Mai', '1 volta', '2–5 volte', 'Più di 5 volte', 'Non ricordo / Preferisco non rispondere'])
    falk_future = scale('falk_future')
    falk_risk = scale('falk_risk')
    falk_giving = scale('falk_giving')
    falk_favour = scale('falk_favour')
    falk_revenge = scale('falk_revenge')
    falk_intentions = scale('falk_intentions')


def experiment_perceived_purpose_error_message(player, value):
    if non_whitespace_length(value) < 20:
        return "Descrivi brevemente con qualche dettaglio che cosa pensi studiasse l'esperimento."


def experiment_changes_error_message(player, value):
    if non_whitespace_length(value) < 20:
        return 'Descrivi brevemente con qualche dettaglio che cosa pensi.'


def country_birth_error_message(player, value):
    if not value.strip():
        return 'Indica il Paese in cui sei nato/a.'


def country_residence_error_message(player, value):
    if not value.strip():
        return 'Indica il Paese della tua residenza permanente.'


def university_affiliation_error_message(player, value):
    if not value.strip():
        return 'Indica il tuo corso di studio o la tua struttura di affiliazione.'


def creating_session(subsession):
    if subsession.session.config['app_sequence'] != lab_route.payment_sequence(subsession.session.config['branch']):
        raise ValueError('The survey belongs after Policy and immediately before laboratory payment.')


class SurveyFormPage(Page):
    template_name = 'survey/SurveyPage.html'
    form_model = 'player'
    form_fields = []
    heading = 'Questionario finale'
    introduction = []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sliders, other_fields = [], []
        form = context['form']
        for name in self.form_fields:
            field = form[name]
            if name in SLIDERS:
                value = field.data
                answered = type(value) is int and 0 <= value <= 10
                sliders.append(dict(SLIDERS[name], name=name, help=SLIDERS[name].get('help', ''),
                                    answered=answered, value=value if answered else ''))
            else:
                if name != 'experiment_clarity_improvement':
                    other_fields.append(field)
        clarity = form['experiment_clarity'].data if 'experiment_clarity' in self.form_fields else None
        context.update(survey_heading=self.heading, introduction=self.introduction,
                       sliders=sliders, other_fields=other_fields, ticks=list(range(11)),
                       clarity_improvement_visible=type(clarity) is int and 0 <= clarity < 5)
        return context


class SurveyWelcome(SurveyFormPage):
    introduction = [
        'Ti chiediamo ora di compilare un breve questionario finale.',
        "Le tue risposte saranno trattate in forma riservata e utilizzate esclusivamente per l'analisi dei dati dell'esperimento.",
        'Le risposte al questionario non influiranno sul tuo pagamento.',
    ]


class ExperimentFeedback(SurveyFormPage):
    heading = "La tua esperienza nell'esperimento"
    form_fields = ['experiment_liking', 'experiment_clarity', 'experiment_clarity_improvement', 'experiment_perceived_purpose', 'experiment_changes']

    @staticmethod
    def error_message(player, values):
        clarity = values.get('experiment_clarity')
        if type(clarity) is int and 0 <= clarity < 5 and non_whitespace_length(values.get('experiment_clarity_improvement')) < 5:
            return {'experiment_clarity_improvement': 'Descrivi brevemente come renderesti più chiare le istruzioni.'}


class Demographics(SurveyFormPage):
    heading = 'Alcune informazioni su di te'
    form_fields = ['gender', 'age', 'country_birth', 'country_residence']


class UniversityBackground(SurveyFormPage):
    heading = 'La tua esperienza universitaria'
    form_fields = ['university_affiliation', 'university_status', 'unibo_time', 'previous_experiment_experience']


class Preferences1(SurveyFormPage):
    heading = 'Le tue preferenze'
    introduction = ['Ora ti chiederemo della tua volontà di agire in un determinato modo. Per favore, dammi una risposta utilizzando una scala da 0 a 10. 0 significa “per niente disposto/a a farlo” e 10 significa “molto disposto/a a farlo”. Puoi utilizzare qualsiasi numero da 0 a 10.']
    form_fields = ['falk_future', 'falk_risk', 'falk_giving']


class Preferences2(SurveyFormPage):
    heading = 'Le tue preferenze'
    introduction = ['Quanto sono appropriate le seguenti affermazioni per descriverti come persona? Per favore, dammi una risposta utilizzando una scala da 0 a 10. 0 significa “non mi descrive per niente” e 10 significa “mi descrive perfettamente”. Puoi utilizzare qualsiasi numero da 0 a 10.']
    form_fields = ['falk_favour', 'falk_revenge', 'falk_intentions']


page_sequence = [SurveyWelcome, ExperimentFeedback, Demographics, UniversityBackground, Preferences1, Preferences2]
