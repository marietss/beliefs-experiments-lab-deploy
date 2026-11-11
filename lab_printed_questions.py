"""Comprehension items adapted from the researcher's printed document.

Economic values and examples follow the November 2026 recalibration.
The source hash identifies the original document, not the revised wording.

Only question paragraphs/options/feedback are reproduced, never the booklet.
Bullet glyphs are formatting; feedback excludes its editorial introductory label.
Option order is deliberately varied and fixed; no runtime randomisation.
"""

SOURCE_DOCUMENT = 'Istruzioni_lab_261026_chiarezza_impaginazione.docx'
SOURCE_SHA256 = '33bf19a57756a53ede4efee492b1a0e5cb72c5a0fed87d7321199b32eb249aed'

PRINTED_QUESTIONS = {'F': [{'prompt': 'Domanda 1 — All’inizio di ogni blocco, con cosa inizi?',
        'options': [('a', '1000 unità di attrezzatura e 100 punti nel portafoglio.'),
 ('b', '100 unità di attrezzatura e 1000 punti nel portafoglio.'),
 ('c', '100 unità di attrezzatura e 100 punti nel portafoglio.')],
        'feedback': 'Ogni blocco inizia con 100 unità di attrezzatura e 1000 punti nel portafoglio.',
        'id': 'reset',
        'correct': 'b'},
       {'prompt': 'Domanda 2 — Se dismetti parte dell’attrezzatura, questa può tornare disponibile più '
                  'avanti nello stesso blocco?',
        'options': [('a', 'No.'), ('b', 'Sì.')],
        'feedback': 'L’attrezzatura dismessa viene rimossa definitivamente per il resto del blocco.',
        'id': 'irreversible',
        'correct': 'a'},
       {'prompt': 'Domanda 3 — Da cosa dipende il costo di dismissione in un determinato periodo?',
        'options': [('a', 'Dal totale delle unità dismesse dall’inizio del blocco.'),
 ('b', 'Dalla quantità media di attrezzatura rimanente nel tuo gruppo.'),
 ('c', 'Dal numero di unità dismesse in quel periodo.')],
        'feedback': 'Il costo è calcolato separatamente in ogni periodo e dipende dalle unità dismesse in '
                    'quel periodo: 0,10 × unità dismesse². Dismettere 10 unità in ciascuno di due periodi costa 20 punti in totale, mentre dismetterne 20 in un solo periodo costa 40 punti.',
        'id': 'period_cost',
        'correct': 'c'},
       {'prompt': 'Domanda 4 — All’Accertamento Principale, cosa succede se rimane attrezzatura nella tua '
                  'azienda?',
        'options': [('a', 'Vengono sottratti 75 punti e il blocco continua con il Periodo 6.'),
 ('b',
  'Viene sottratta una sanzione pari a 175 + 0,5 × unità rimanenti e il blocco continua con '
  'il Periodo 6.'),
 ('c', 'Vengono sottratti 75 punti e il blocco termina.')],
        'feedback': 'Se rimangono unità di attrezzatura, la sanzione è pari a 175 + 0,5 × unità rimanenti. '
                    'Il blocco continua poi con il Periodo 6.',
        'id': 'fixed_positive',
        'correct': 'b'},
       {'prompt': 'Domanda 5 — Nella Sezione 1, la quantità media di attrezzatura rimanente nel tuo gruppo '
                  'influisce sulle sanzioni o sul portafoglio?',
        'options': [('a', 'No.'), ('b', 'Sì.')],
        'feedback': 'Nella Sezione 1 la media del gruppo viene mostrata solo a scopo informativo e non '
                    'determina né le sanzioni né i punti nel portafoglio.',
        'id': 'fixed_average',
        'correct': 'a'},
       {'prompt': 'Domanda 6 — Cosa succede se rimane attrezzatura nella tua azienda all’Accertamento '
                  'Finale?',
        'options': [('a', 'Non succede nulla: l’attrezzatura rimane in uso.'),
 ('b', 'Viene sottratta una sanzione di 75 punti, ma l’attrezzatura non viene dismessa.'),
 ('c',
  'Viene sottratta una sanzione di 75 punti; l’attrezzatura rimanente viene dismessa '
  'automaticamente e il costo è sottratto separatamente.')],
        'feedback': 'Se rimane attrezzatura al termine del Periodo 10, si applicano una sanzione di 75 '
                    'punti e, separatamente, il costo della dismissione automatica: 0,10 × unità rimanenti².',
        'id': 'follow_up',
        'correct': 'c'}],
 'E': [{'prompt': 'Domanda 1 — All’Accertamento Principale, cosa succede se la quantità media di '
                  'attrezzatura rimanente nel tuo gruppo è superiore a 37 unità?',
        'options': [('a', 'Viene applicata una sanzione a tutte le aziende con attrezzatura rimanente.'),
 ('b', 'La sanzione dipende soltanto dall’attrezzatura rimanente nella tua azienda.'),
 ('c', 'Non viene applicata alcuna sanzione.')],
        'feedback': 'Se la media del gruppo è superiore a 37 unità, non viene applicata alcuna sanzione '
                    'all’Accertamento Principale.',
        'id': 'known',
        'correct': 'c'},
       {'prompt': 'Domanda 2 — Se la quantità media di attrezzatura rimanente nel tuo gruppo è esattamente '
                  'uguale a 37 unità, cosa succede?',
        'options': [('a', 'Non viene applicata alcuna sanzione perché la media ha raggiunto la soglia.'),
 ('b',
  'Se nella tua azienda rimangono più di 0 unità, si applica la sanzione; con 0 unità non si '
  'applica.'),
 ('c', 'A tutti i manager viene applicata la stessa sanzione.')],
        'feedback': 'La media deve essere strettamente superiore alla soglia per escludere le sanzioni. '
                    'Quando è uguale alla soglia, conta l’attrezzatura rimanente nella tua azienda.',
        'id': 'equality',
        'correct': 'b'},
       {'prompt': 'Domanda 3 — L’attrezzatura rimanente nella tua azienda è inclusa nel calcolo della '
                  'quantità media del gruppo?',
        'options': [('a', 'Sì.'), ('b', 'No.')],
        'feedback': 'La media del gruppo è calcolata usando l’attrezzatura rimanente in tutte e sei le '
                    'aziende, inclusa la tua.',
        'id': 'own_inclusion',
        'correct': 'a'},
       {'prompt': 'Domanda 4 — Se la quantità media del gruppo è uguale o inferiore alla soglia e nella tua '
                  'azienda rimangono 50 unità, quanti punti di sanzione vengono sottratti dal portafoglio?',
        'options': [('a', 'Nessun punto.'),
 ('b', '175 punti, indipendentemente dall’attrezzatura rimanente.'),
 ('c', '200 punti.')],
        'feedback': 'Quando la media è uguale o inferiore alla soglia e rimane attrezzatura nella tua '
                    'azienda, la sanzione è 175 + 0,5 × 50 = 200 punti.',
        'id': 'zero',
        'correct': 'c'}],
 'A': [{'prompt': 'Domanda 1 — Prima dell’Accertamento Principale, cosa sai della soglia del blocco?',
        'options': [('a', 'È sempre uguale a 37 unità.'),
 ('b',
  'È un numero intero tra 33 e 42; non conosci il valore selezionato né la probabilità dei '
  'diversi valori.'),
 ('c',
  'Può avere qualsiasi valore tra 0 e 100 e tutti i valori sono dichiarati ugualmente '
  'probabili.')],
        'feedback': 'La soglia può assumere i valori interi da 33 a 42. Non ne conosci il valore prima '
                    'dell’Accertamento Principale né la probabilità dei diversi valori.',
        'id': 'support',
        'correct': 'b'},
       {'prompt': 'Domanda 2 — Se la quantità media di attrezzatura rimanente nel tuo gruppo è esattamente '
                  'uguale alla soglia, cosa succede?',
        'options': [('a', 'Non viene applicata alcuna sanzione perché la media ha raggiunto la soglia.'),
 ('b', 'A tutti i manager viene applicata la stessa sanzione.'),
 ('c',
  'Se nella tua azienda rimangono più di 0 unità, si applica la sanzione; con 0 unità non si '
  'applica.')],
        'feedback': 'La media deve essere strettamente superiore alla soglia per escludere le sanzioni. '
                    'Quando è uguale alla soglia, conta l’attrezzatura rimanente nella tua azienda.',
        'id': 'strict_unknown',
        'correct': 'c'},
       {'prompt': 'Domanda 3 — L’attrezzatura rimanente nella tua azienda è inclusa nel calcolo della '
                  'quantità media del gruppo?',
        'options': [('a', 'No.'), ('b', 'Sì.')],
        'feedback': 'La media del gruppo è calcolata usando l’attrezzatura rimanente in tutte e sei le '
                    'aziende, inclusa la tua.',
        'id': 'own_inclusion',
        'correct': 'b'},
       {'prompt': 'Domanda 4 — Se la quantità media del gruppo è uguale o inferiore alla soglia e nella tua '
                  'azienda rimangono 50 unità, quanti punti di sanzione vengono sottratti dal portafoglio?',
        'options': [('a', '200 punti.'),
 ('b', 'Nessun punto.'),
 ('c', '175 punti, indipendentemente dall’attrezzatura rimanente.')],
        'feedback': 'Quando la media è uguale o inferiore alla soglia e rimane attrezzatura nella tua '
                    'azienda, la sanzione è 175 + 0,5 × 50 = 200 punti.',
        'id': 'zero',
        'correct': 'a'}],
 'M': [{'prompt': 'Domanda 1 — All’Accertamento Principale, cosa succede se la quantità media di '
                  'attrezzatura rimanente nel tuo gruppo è superiore a 37 unità?',
        'options': [('a', 'Viene applicata una sanzione a tutte le aziende con attrezzatura rimanente.'),
 ('b', 'La sanzione dipende soltanto dall’attrezzatura rimanente nella tua azienda.'),
 ('c', 'Non viene applicata alcuna sanzione.')],
        'feedback': 'Se la media del gruppo è superiore a 37 unità, non viene applicata alcuna sanzione '
                    'all’Accertamento Principale.',
        'id': 'known',
        'correct': 'c'},
       {'prompt': 'Domanda 2 — Se la quantità media di attrezzatura rimanente nel tuo gruppo è esattamente '
                  'uguale a 37 unità, cosa succede?',
        'options': [('a',
  'Se nella tua azienda rimangono più di 0 unità, si applica la sanzione; con 0 unità non si '
  'applica.'),
 ('b', 'Non viene applicata alcuna sanzione perché la media ha raggiunto la soglia.'),
 ('c', 'A tutti i manager viene applicata la stessa sanzione.')],
        'feedback': 'La media deve essere strettamente superiore alla soglia per escludere le sanzioni. '
                    'Quando è uguale alla soglia, conta l’attrezzatura rimanente nella tua azienda.',
        'id': 'equality',
        'correct': 'a'},
       {'prompt': 'Domanda 3 — Quali informazioni relative alla prima previsione vengono mostrate al gruppo '
                  'durante il blocco?',
        'options': [('a', 'Soltanto la tua prima previsione.'),
 ('b', 'I sei valori individuali in forma anonima e la loro media.'),
 ('c', 'I sei valori individuali associati alle identità dei manager.')],
        'feedback': 'Vengono mostrati i sei valori individuali della prima previsione e la loro media, senza '
                    'rivelare a quale manager appartengano.',
        'id': 'two_reports',
        'correct': 'b'},
       {'prompt': 'Domanda 4 — Quale affermazione sulle previsioni è corretta?',
        'options': [('a', 'La seconda previsione viene mostrata al gruppo e determina la sanzione.'),
 ('b', 'La media della prima previsione sostituisce la quantità media del gruppo.'),
 ('c',
  'La seconda previsione rimane privata e l’Accertamento Principale dipende dall’attrezzatura '
  'rimanente.')],
        'feedback': 'La seconda previsione resta privata. Le previsioni mostrate hanno una funzione '
                    'informativa e non determinano le sanzioni.',
        'id': 'message_role',
        'correct': 'c'}],
 'P': [{'prompt': 'Domanda 1 — Quali sanzioni entrano nel fondo delle sanzioni da cui viene effettuata la '
                  'distribuzione?',
        'options': [('a', 'Le sanzioni dell’Accertamento Principale e dell’Accertamento Finale.'),
 ('b', 'Soltanto le sanzioni applicate all’Accertamento Principale.'),
 ('c', 'Tutti i costi di dismissione dell’attrezzatura.')],
        'feedback': 'Nel fondo entrano solo le sanzioni applicate all’Accertamento Principale. Le sanzioni e '
                    'i costi dell’Accertamento Finale non sono distribuiti.',
        'id': 'pool',
        'correct': 'b'},
       {'prompt': 'Domanda 2 — Come viene calcolato l’importo ricevuto da ciascun manager non sanzionato?',
        'options': [('a', 'L’intero fondo viene diviso in parti uguali tra tutti e sei i manager.'),
 ('b', 'Ogni manager non sanzionato riceve 175 punti, indipendentemente dal fondo.'),
 ('c',
  'Il 30% del fondo delle sanzioni viene diviso in parti uguali tra i manager non '
  'sanzionati.')],
        'feedback': 'Il 30% del fondo è distribuito in parti uguali soltanto tra i manager che non hanno '
                    'ricevuto una sanzione all’Accertamento Principale.',
        'id': 'share',
        'correct': 'c'},
       {'prompt': 'Domanda 3 — Quattro manager pagano una sanzione di 180 punti ciascuno e due manager non '
                  'vengono sanzionati. Quanti punti riceve ciascuno dei due manager non sanzionati?',
        'options': [('a', '108 punti.'), ('b', '216 punti.'), ('c', '180 punti.')],
        'feedback': 'Il fondo è 4 × 180 = 720 punti. Il 30% è pari a 216 punti, divisi tra due manager non '
                    'sanzionati: 108 punti ciascuno.',
        'id': 'distribution_example',
        'correct': 'a'},
       {'prompt': 'Domanda 4 — Quando non viene effettuata alcuna distribuzione dopo l’Accertamento '
                  'Principale?',
        'options': [('a', 'Ogni volta che almeno un manager riceve una sanzione.'),
 ('b', 'Quando tutti i manager sono sanzionati oppure quando nessuno è sanzionato.'),
 ('c', 'Ogni volta che un manager ha 0 unità di attrezzatura.')],
        'feedback': 'Se tutti sono sanzionati non ci sono destinatari; se nessuno è sanzionato, il fondo è '
                    'pari a 0. In entrambi i casi la distribuzione non avviene.',
        'id': 'no_distribution',
        'correct': 'b'}]}
