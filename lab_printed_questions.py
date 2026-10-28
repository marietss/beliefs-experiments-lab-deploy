"""Literal comprehension items from the researcher's printed document.

Only question paragraphs/options/feedback are reproduced, never the booklet.
Bullet glyphs are formatting; feedback excludes its editorial introductory label.
Option order is fixed. Answer keys follow the stated rules; no option shuffling.
"""

SOURCE_DOCUMENT = 'Istruzioni_lab_261026_chiarezza_impaginazione.docx'
SOURCE_SHA256 = '33bf19a57756a53ede4efee492b1a0e5cb72c5a0fed87d7321199b32eb249aed'

PRINTED_QUESTIONS = {'F': [{'prompt': 'Domanda 1 — All’inizio di ogni blocco, con cosa inizi?',
        'options': [('a', '100 unità di attrezzatura e 1000 punti nel portafoglio.'),
                    ('b', '1000 unità di attrezzatura e 100 punti nel portafoglio.'),
                    ('c', '100 unità di attrezzatura e 100 punti nel portafoglio.')],
        'feedback': 'Ogni blocco inizia con 100 unità di attrezzatura e 1000 punti nel portafoglio.',
        'id': 'reset',
        'correct': 'a'},
       {'prompt': 'Domanda 2 — Se dismetti parte dell’attrezzatura, questa può tornare disponibile più '
                  'avanti nello stesso blocco?',
        'options': [('a', 'Sì.'), ('b', 'No.')],
        'feedback': 'L’attrezzatura dismessa viene rimossa definitivamente per il resto del blocco.',
        'id': 'irreversible',
        'correct': 'b'},
       {'prompt': 'Domanda 3 — Da cosa dipende il costo di dismissione in un determinato periodo?',
        'options': [('a', 'Dal numero di unità dismesse in quel periodo.'),
                    ('b', 'Dal totale delle unità dismesse dall’inizio del blocco.'),
                    ('c', 'Dalla quantità media di attrezzatura rimanente nel tuo gruppo.')],
        'feedback': 'Il costo è calcolato separatamente in ogni periodo e dipende dalle unità dismesse in '
                    'quel periodo.',
        'id': 'period_cost',
        'correct': 'a'},
       {'prompt': 'Domanda 4 — All’Accertamento Principale, cosa succede se rimane attrezzatura nella tua '
                  'azienda?',
        'options': [('a',
                     'Viene sottratta una sanzione pari a 175 + 0,5 × unità rimanenti e il blocco continua '
                     'con il Periodo 6.'),
                    ('b', 'Vengono sottratti 275 punti e il blocco continua con il Periodo 6.'),
                    ('c', 'Vengono sottratti 275 punti e il blocco termina.')],
        'feedback': 'Se rimangono unità di attrezzatura, la sanzione è pari a 175 + 0,5 × unità rimanenti. '
                    'Il blocco continua poi con il Periodo 6.',
        'id': 'fixed_positive',
        'correct': 'a'},
       {'prompt': 'Domanda 5 — Nella Sezione 1, la quantità media di attrezzatura rimanente nel tuo gruppo '
                  'influisce sulle sanzioni o sul portafoglio?',
        'options': [('a', 'Sì.'), ('b', 'No.')],
        'feedback': 'Nella Sezione 1 la media del gruppo viene mostrata solo a scopo informativo e non '
                    'determina né le sanzioni né i punti nel portafoglio.',
        'id': 'fixed_average',
        'correct': 'b'},
       {'prompt': 'Domanda 6 — Cosa succede se rimane attrezzatura nella tua azienda all’Accertamento '
                  'Finale?',
        'options': [('a',
                     'Viene sottratta una sanzione di 275 punti; l’attrezzatura rimanente viene dismessa '
                     'automaticamente e il costo è sottratto separatamente.'),
                    ('b', 'Non succede nulla: l’attrezzatura rimane in uso.'),
                    ('c',
                     'Viene sottratta una sanzione di 275 punti, ma l’attrezzatura non viene dismessa.')],
        'feedback': 'Se rimane attrezzatura al termine del Periodo 10, si applicano una sanzione di 275 '
                    'punti e, separatamente, il costo della dismissione automatica.',
        'id': 'follow_up',
        'correct': 'a'}],
 'E': [{'prompt': 'Domanda 1 — All’Accertamento Principale, cosa succede se la quantità media di '
                  'attrezzatura rimanente nel tuo gruppo è superiore a 45 unità?',
        'options': [('a', 'Non viene applicata alcuna sanzione.'),
                    ('b', 'Viene applicata una sanzione a tutte le aziende con attrezzatura rimanente.'),
                    ('c', 'La sanzione dipende soltanto dall’attrezzatura rimanente nella tua azienda.')],
        'feedback': 'Se la media del gruppo è superiore a 45 unità, non viene applicata alcuna sanzione '
                    'all’Accertamento Principale.',
        'id': 'known',
        'correct': 'a'},
       {'prompt': 'Domanda 2 — Se la quantità media di attrezzatura rimanente nel tuo gruppo è esattamente '
                  'uguale a 45 unità, cosa succede?',
        'options': [('a', 'Non viene applicata alcuna sanzione perché la media ha raggiunto la soglia.'),
                    ('b',
                     'Se nella tua azienda rimangono più di 0 unità, si applica la sanzione; con 0 unità non '
                     'si applica.'),
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
        'options': [('a', '200 punti.'),
                    ('b', 'Nessun punto.'),
                    ('c', '175 punti, indipendentemente dall’attrezzatura rimanente.')],
        'feedback': 'Quando la media è uguale o inferiore alla soglia e rimane attrezzatura nella tua '
                    'azienda, la sanzione è 175 + 0,5 × 50 = 200 punti.',
        'id': 'zero',
        'correct': 'a'}],
 'A': [{'prompt': 'Domanda 1 — Prima dell’Accertamento Principale, cosa sai della soglia del blocco?',
        'options': [('a',
                     'È un numero intero tra 40 e 50; non conosci il valore selezionato né la probabilità '
                     'dei diversi valori.'),
                    ('b', 'È sempre uguale a 45 unità.'),
                    ('c',
                     'Può avere qualsiasi valore tra 0 e 100 e tutti i valori sono dichiarati ugualmente '
                     'probabili.')],
        'feedback': 'La soglia può assumere i valori interi da 40 a 50. Non ne conosci il valore prima '
                    'dell’Accertamento Principale né la probabilità dei diversi valori.',
        'id': 'support',
        'correct': 'a'},
       {'prompt': 'Domanda 2 — Se la quantità media di attrezzatura rimanente nel tuo gruppo è esattamente '
                  'uguale alla soglia, cosa succede?',
        'options': [('a', 'Non viene applicata alcuna sanzione perché la media ha raggiunto la soglia.'),
                    ('b',
                     'Se nella tua azienda rimangono più di 0 unità, si applica la sanzione; con 0 unità non '
                     'si applica.'),
                    ('c', 'A tutti i manager viene applicata la stessa sanzione.')],
        'feedback': 'La media deve essere strettamente superiore alla soglia per escludere le sanzioni. '
                    'Quando è uguale alla soglia, conta l’attrezzatura rimanente nella tua azienda.',
        'id': 'strict_unknown',
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
        'options': [('a', '200 punti.'),
                    ('b', 'Nessun punto.'),
                    ('c', '175 punti, indipendentemente dall’attrezzatura rimanente.')],
        'feedback': 'Quando la media è uguale o inferiore alla soglia e rimane attrezzatura nella tua '
                    'azienda, la sanzione è 175 + 0,5 × 50 = 200 punti.',
        'id': 'zero',
        'correct': 'a'}],
 'M': [{'prompt': 'Domanda 1 — All’Accertamento Principale, cosa succede se la quantità media di '
                  'attrezzatura rimanente nel tuo gruppo è superiore a 45 unità?',
        'options': [('a', 'Non viene applicata alcuna sanzione.'),
                    ('b', 'Viene applicata una sanzione a tutte le aziende con attrezzatura rimanente.'),
                    ('c', 'La sanzione dipende soltanto dall’attrezzatura rimanente nella tua azienda.')],
        'feedback': 'Se la media del gruppo è superiore a 45 unità, non viene applicata alcuna sanzione '
                    'all’Accertamento Principale.',
        'id': 'known',
        'correct': 'a'},
       {'prompt': 'Domanda 2 — Se la quantità media di attrezzatura rimanente nel tuo gruppo è esattamente '
                  'uguale a 45 unità, cosa succede?',
        'options': [('a', 'Non viene applicata alcuna sanzione perché la media ha raggiunto la soglia.'),
                    ('b',
                     'Se nella tua azienda rimangono più di 0 unità, si applica la sanzione; con 0 unità non '
                     'si applica.'),
                    ('c', 'A tutti i manager viene applicata la stessa sanzione.')],
        'feedback': 'La media deve essere strettamente superiore alla soglia per escludere le sanzioni. '
                    'Quando è uguale alla soglia, conta l’attrezzatura rimanente nella tua azienda.',
        'id': 'equality',
        'correct': 'b'},
       {'prompt': 'Domanda 3 — Quali informazioni relative alla prima previsione vengono mostrate al gruppo '
                  'durante il blocco?',
        'options': [('a', 'I sei valori individuali in forma anonima e la loro media.'),
                    ('b', 'Soltanto la tua prima previsione.'),
                    ('c', 'I sei valori individuali associati alle identità dei manager.')],
        'feedback': 'Vengono mostrati i sei valori individuali della prima previsione e la loro media, senza '
                    'rivelare a quale manager appartengano.',
        'id': 'two_reports',
        'correct': 'a'},
       {'prompt': 'Domanda 4 — Quale affermazione sulle previsioni è corretta?',
        'options': [('a',
                     'La seconda previsione rimane privata e l’Accertamento Principale dipende '
                     'dall’attrezzatura rimanente.'),
                    ('b', 'La seconda previsione viene mostrata al gruppo e determina la sanzione.'),
                    ('c', 'La media della prima previsione sostituisce la quantità media del gruppo.')],
        'feedback': 'La seconda previsione resta privata. Le previsioni mostrate hanno una funzione '
                    'informativa e non determinano le sanzioni.',
        'id': 'message_role',
        'correct': 'a'}],
 'P': [{'prompt': 'Domanda 1 — Quali sanzioni entrano nel fondo delle sanzioni da cui viene effettuata la '
                  'distribuzione?',
        'options': [('a', 'Soltanto le sanzioni applicate all’Accertamento Principale.'),
                    ('b', 'Le sanzioni dell’Accertamento Principale e dell’Accertamento Finale.'),
                    ('c', 'Tutti i costi di dismissione dell’attrezzatura.')],
        'feedback': 'Nel fondo entrano solo le sanzioni applicate all’Accertamento Principale. Le sanzioni e '
                    'i costi dell’Accertamento Finale non sono distribuiti.',
        'id': 'pool',
        'correct': 'a'},
       {'prompt': 'Domanda 2 — Come viene calcolato l’importo ricevuto da ciascun manager non sanzionato?',
        'options': [('a',
                     'Un terzo del fondo delle sanzioni viene diviso in parti uguali tra i manager non '
                     'sanzionati.'),
                    ('b', 'L’intero fondo viene diviso in parti uguali tra tutti e sei i manager.'),
                    ('c', 'Ogni manager non sanzionato riceve 175 punti, indipendentemente dal fondo.')],
        'feedback': 'Un terzo del fondo è distribuito in parti uguali soltanto tra i manager che non hanno '
                    'ricevuto una sanzione all’Accertamento Principale.',
        'id': 'share',
        'correct': 'a'},
       {'prompt': 'Domanda 3 — Quattro manager pagano una sanzione di 180 punti ciascuno e due manager non '
                  'vengono sanzionati. Quanti punti riceve ciascuno dei due manager non sanzionati?',
        'options': [('a', '120 punti.'), ('b', '240 punti.'), ('c', '180 punti.')],
        'feedback': 'Il fondo è 4 × 180 = 720 punti. Un terzo è pari a 240 punti, divisi tra due manager non '
                    'sanzionati: 120 punti ciascuno.',
        'id': 'distribution_example',
        'correct': 'a'},
       {'prompt': 'Domanda 4 — Quando non viene effettuata alcuna distribuzione dopo l’Accertamento '
                  'Principale?',
        'options': [('a', 'Quando tutti i manager sono sanzionati oppure quando nessuno è sanzionato.'),
                    ('b', 'Ogni volta che almeno un manager riceve una sanzione.'),
                    ('c', 'Ogni volta che un manager ha 0 unità di attrezzatura.')],
        'feedback': 'Se tutti sono sanzionati non ci sono destinatari; se nessuno è sanzionato, il fondo è '
                    'pari a 0. In entrambi i casi la distribuzione non avviene.',
        'id': 'no_distribution',
        'correct': 'a'}]}
