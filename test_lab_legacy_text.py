"""Copy provenance anchors from main@a462a3a; no quiz or economic logic changes.

The comparison record identifies the source paragraphs. Existing multiplayer,
privacy and freeze tests remain the authority for behavior.
"""
from pathlib import Path
import re
import hashlib
import unittest
from fractions import Fraction


def text(path):
    return ' '.join(re.sub(r'<[^>]+>', '', Path(path).read_text()).split())


class LegacyTextTests(unittest.TestCase):
    def test_general_source_paragraphs(self):
        s = text('general_instructions/LabGeneralBody.html')
        for sentence in (
            'Benvenuto! Questo è un esperimento sul processo decisionale. Leggi attentamente tutte le istruzioni.',
            "Ogni partecipante gestisce un'impresa separata.",
            'Il tuo gruppo rimane lo stesso per tutto il blocco.',
            'La tua impresa vuole che tu completi la dismissione richiesta al minor costo possibile.',
            "Riceverai istruzioni dettagliate prima dell'inizio di ogni sezione.",
            'Devi rispondere correttamente a tutte le domande prima di continuare.',
            'Prendi quindi ogni decisione in ciascun blocco come se quel blocco dovesse determinare il tuo pagamento.',
        ):
            self.assertIn(sentence, s)

    def test_fixed_capital_decision_and_cost_source_paragraphs(self):
        s = text('general_instructions/LabComparableSectionBody.html')
        for sentence in (
            'You are the manager of a firm. Your task is to decide when and how many units of your firm’s equipment to retire.',
            'Both your firm’s equipment and your budget are always visible on screen.',
            'They do not carry over from one block to the next one.',
            'Any equipment of your firm that you retire cannot be restored within that block.',
            'The number of units in your firm’s equipment can stay the same or decrease, but it cannot increase during a block.',
            'An external authority evaluates the number of units in your firm’s equipment.',
        ):
            self.assertIn(sentence, s)
        costs = text('general_instructions/LabComparableCosts.html')
        self.assertIn('The cost is the same for all participants.', costs)
        self.assertIn('You do not need to calculate it yourself.', costs)
        self.assertIn('It is more convenient to spread retirement across more periods than concentrating it in fewer periods.', costs)
        self.assertIn('all six group members have submitted their decisions', costs)

    def test_adapted_examples_are_exact(self):
        costs = text('general_instructions/LabComparableCosts.html')
        self.assertIn('Retiring 50 units costs 250 points, whether you do so in Period 1, Period 2, or any other period.', costs)
        self.assertIn('62.5 + 62.5 = 125 points', costs)
        self.assertEqual(Fraction(1, 10) * 50**2, Fraction('250'))
        self.assertEqual(2 * Fraction(1, 10) * 25**2, Fraction('125'))
        follow = text('general_instructions/LabComparableSectionBody.html')
        self.assertIn('800 points − 75 points penalty − 62.5 points retirement cost = 662.5 points.', follow)
        self.assertEqual(800 - 75 - Fraction(1, 10) * 25**2, Fraction('662.5'))

    def test_E_and_A_historical_rules_keep_strict_comparison(self):
        for app in ('endogenous', 'ambiguity'):
            s = text(f'{app}/Rules.html')
            self.assertIn("L'attrezzatura della tua impresa è inclusa in questa media.", s)
            self.assertIn('quando tutti e sei i responsabili hanno completato le loro decisioni', s)
            self.assertIn('uguale o inferiore alla soglia', s)
            self.assertIn("Se l'attrezzatura della tua impresa è 0", s)
        a = Path('ambiguity/Rules.html').read_text()
        self.assertNotIn('{{ threshold }}', a)
        self.assertNotIn('<script', a)
        self.assertNotIn('comparison_value', a)
        self.assertIn('non ti vengono fornite le probabilità dei diversi valori', a)

    @unittest.skipUnless(Path('general_instructions/LabQuiz.html').is_file(), 'Historical quiz-deck wrapper absent; active ComprehensionPair is tested separately.')
    def test_all_quizzes_use_the_canonical_instruction_family(self):
        s = Path('general_instructions/LabQuiz.html').read_text()
        self.assertIn('LabComparableStyles', s)
        self.assertIn('data-quiz-deck', s)
        self.assertIn('quiz_page.questions', s)
        self.assertIn('value="{{ value }}"', s)
        self.assertNotIn('LabComparableQuestion', s)
        self.assertNotIn('LabComparableOption', s)

    def test_scoring_and_counter_functions_are_unchanged(self):
        import ast
        expected = {'question': 'ed3335e65f9443b72b0bb37557d9e0dfd46bb53d39d1400db42b419a1ee48e45', 'quiz_fields': '2feefcfe1989f3630a99348f8f1e26462ecee057f9b8db402c3909989c249c38', 'check_answers': 'be0ed51fa99adef0a58d44144e06439da19200253a6656f125844ea80d041c2b', 'correct_answers': 'e3338d2fb029299b7bfc2f160948ab57553ce32e337aff66ff5ef8e32e799a06'}
        tree = ast.parse(Path('lab_instructions.py').read_text())
        actual = {n.name: hashlib.sha256(ast.dump(n).encode()).hexdigest()
                  for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in expected}
        self.assertEqual(actual, expected)

    def test_no_legacy_controls_or_simulated_scripts_restored(self):
        for app in ('fixed', 'endogenous', 'ambiguity'):
            for filename in ('Decision', 'Rules', 'EquipmentGraph', 'Result'):
                s = Path(app, filename + '.html').read_text()
                for bad in ('stageGameConfig', 'simulatedAverage', 'dismissal_choice', 'type="number"'):
                    self.assertNotIn(bad, s)
