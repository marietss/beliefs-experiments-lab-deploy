"""Decision-only Italian charts and untouched selection; real lab records and offline UI."""
import json
from pathlib import Path
import re
import unittest

import test_fixed
from otree.database import db
from otree.templating.template import Template
from test_fixed_browser import CHROME
import test_messages_browser as browser_harness


def environments():
    import fixed, endogenous, ambiguity, messages, policy
    import test_endogenous as e, test_ambiguity as a, test_messages as m, test_policy as p
    return [(fixed, test_fixed, None), (endogenous, e, None), (ambiguity, a, None),
            (messages, m, None)] + [(policy, p, b) for b in 'EAM']


def decision_case(app, helpers, branch=None, *, zero=False):
    session = helpers.make_session(branch) if branch else helpers.make_session()
    helpers.ready(session)
    group = helpers.subsession(session).get_groups()[0]
    if zero:
        helpers.run_period(group, [100] * 6)
        player = group.get_players()[0].in_round(2)
    else:
        helpers.reports(group)
        player = group.get_players()[0]
    context = dict(player=player, **app.Decision.vars_for_template(player))
    html = Template(Path(app.__name__, 'Decision.html').read_text()).render(context)
    return player, html


class DecisionPresentationTests(unittest.TestCase):
    def tearDown(self): db.rollback()

    def test_all_seven_environments_clean_left_graph_and_empty_submission(self):
        for app, helpers, branch in environments():
            player, html = decision_case(app, helpers, branch)
            left = html.split('<h2>La tua attrezzatura</h2>', 1)[1].split('</section>', 1)[0]
            for removed in ('Il grafico mostra', 'All\'inizio di un blocco', 'Blu: la tua', 'Grigio tratteggiato'):
                self.assertNotIn(removed, left)
            self.assertNotIn('id="slider-help"', html)
            self.assertNotIn('aria-describedby="slider-help"', html)
            self.assertIn('value=""', html)
            self.assertIn('data-untouched', html)
            self.assertIn('aria-valuetext="Nessuna quantità selezionata"', html)
            self.assertRegex(html, r'id="confirm-retirement"[^>]+disabled')
            self.assertIn('<h2>Costo della dismissione</h2>', html)
            self.assertNotIn('Il costo selezionato è mostrato anche qui sotto', html)
            labels = re.findall(r'<dt>(.*?)</dt>', html)
            self.assertEqual(len(labels), 4)
            self.assertTrue(all(label.endswith(':') for label in labels))
            self.assertIn('fixed/decision-charts.js', html)
            if app.__name__ in ('endogenous', 'messages') or app.__name__ == 'policy' and branch != 'A':
                self.assertNotIn('id="known-threshold"', left)
            if app.__name__ == 'ambiguity' or branch == 'A':
                self.assertNotIn('id="revealed-threshold"', left)
                config = json.loads(re.search(r'id="lab-chart-config" type="application/json">(.*?)</script>', html, re.S).group(1))
                self.assertNotIn('threshold', config)
                self.assertNotIn('ambiguity_thresholds', html)
            if app.__name__ == 'messages' or branch == 'M':
                self.assertNotIn('id="public-report-mean"', html)
                self.assertIn('publicReportMean', html)
                self.assertIn('publicReportPlans', html)
                self.assertNotIn('public_report_record', html)
            db.rollback()

    def test_display_rounding_does_not_round_settled_costs_or_budgets(self):
        from fractions import Fraction
        from lab_persistence import decode_fraction
        for app, helpers, branch in environments():
            session = helpers.make_session(branch) if branch else helpers.make_session()
            helpers.ready(session)
            group = helpers.subsession(session).get_groups()[0]
            helpers.run_period(group, [25, 25, 0, 0, 0, 0])
            player = group.get_players()[0]
            self.assertEqual(decode_fraction(player.voluntary_cost), Fraction(125, 2))
            self.assertEqual(decode_fraction(player.wallet_after), Fraction(1875, 2))
            db.rollback()

    def test_results_keep_the_original_shared_graph_templates_and_scripts(self):
        for app, _, _ in environments():
            source = Path(app.__name__, 'Result.html').read_text()
            self.assertIn(f"'{app.__name__}/EquipmentGraph.html'", source)
            self.assertNotIn('decision-charts.js', source)
            self.assertNotIn('DecisionEquipmentGraph', source)
        css = Path('_static/fixed/decision-interface.css').read_text()
        self.assertIn('#retirement-slider[data-untouched]::-webkit-slider-thumb', css)
        self.assertIn('#retirement-slider[data-untouched]::-moz-range-thumb', css)
        self.assertIn('opacity: 0', css)


@unittest.skipUnless(CHROME, 'Headless Chrome unavailable.')
class DecisionPresentationBrowserTests(unittest.TestCase):
    browser = browser_harness.MessagesBrowserTests.browser
    def tearDown(self): db.rollback()

    def test_ambiguity_fill_and_prediction_reference_line_occlusion(self):
        for app, helpers, branch in environments():
            if app.__name__ not in ('ambiguity', 'messages', 'policy') or app.__name__ == 'policy' and branch == 'E':
                continue
            session = helpers.make_session(branch) if branch else helpers.make_session()
            helpers.ready(session)
            group = helpers.subsession(session).get_groups()[0]
            if app.__name__ == 'messages' or branch == 'M':
                helpers.reports(group, own=[20, 40, 50, 50, 60, 80])
            else:
                helpers.reports(group)
            player = group.get_players()[0]
            for page in (app.Decision, app.Result):
                if page is app.Result:
                    helpers.decide(group, [10]*6)
                    app.PeriodWait.after_all_players_arrive(group)
                html = Template(Path(app.__name__, page.__name__ + '.html').read_text()).render(
                    dict(player=player, **page.vars_for_template(player)))
                html = html.replace('/static/', Path('_static').resolve().as_uri() + '/')
                self.browser(html, """
                    const graph=Chart.getChart('equipment-chart');
                    const config=JSON.parse(document.getElementById('lab-chart-config').textContent);
                    assert(graph && document.getElementById('chart-unavailable').hidden,'chart renders');
                    const ctx=graph.ctx, mainX=graph.scales.x.getPixelForValue(config.mainPeriod);
                    if(Object.hasOwn(config,'thresholdLow')) {
                        const reference=graph.config.plugins.find(p=>p.id==='ambiguityThreshold');
                        const rectangles=[], original=ctx.fillRect;
                        ctx.fillRect=function(...args){rectangles.push(args);return original.apply(this,args);};
                        try {reference.beforeDatasetsDraw(graph);} finally {ctx.fillRect=original;}
                        const top=graph.scales.y.getPixelForValue(config.thresholdHigh);
                        const bottom=graph.scales.y.getPixelForValue(config.thresholdLow);
                        assert(rectangles.some(r=>Math.abs(r[0]-(mainX-8))<0.01 && r[1]===top && r[2]===16 && r[3]===bottom-top),'filled continuous public range');
                        assert(!Object.hasOwn(config,'threshold'),'no realized threshold in pre-Main config');
                    } else {
                        const checks=graph.config.plugins.find(p=>p.id==='labChecks');
                        const segments=[], originalMove=ctx.moveTo, originalLine=ctx.lineTo;
                        let start;
                        ctx.moveTo=function(x,y){start=[x,y];return originalMove.call(this,x,y);};
                        ctx.lineTo=function(x,y){segments.push([start,[x,y]]);return originalLine.call(this,x,y);};
                        try {checks.beforeDatasetsDraw(graph);} finally {ctx.moveTo=originalMove;ctx.lineTo=originalLine;}
                        for(const dataset of graph.data.datasets.slice(3)) {
                            assert(dataset.pointStyle==='rect','prediction square preserved');
                            for(const point of dataset.data) {
                                const py=graph.scales.y.getPixelForValue(point.y), radius=dataset.pointRadius;
                                assert(!segments.some(([a,b])=>Math.abs(a[0]-mainX)<0.01 && a[1]<py+radius && b[1]>py-radius),'line has no stroke behind square');
                            }
                        }
                        // Compare real rendered pixels with/without the reference
                        // lines. Every square footprint must be identical.
                        graph.update('none');
                        const pixels=()=>graph.data.datasets.slice(3).flatMap(ds=>ds.data.map(p=>{
                            const py=graph.scales.y.getPixelForValue(p.y), d=graph.currentDevicePixelRatio;
                            return [...ctx.getImageData(Math.round(mainX*d),Math.round((py-ds.pointRadius+1)*d),1,Math.max(1,Math.floor((2*ds.pointRadius-2)*d))).data];
                        }));
                        const foreground=pixels(), draw=checks.beforeDatasetsDraw;
                        checks.beforeDatasetsDraw=()=>{};
                        try {graph.update('none');assert(JSON.stringify(pixels())===JSON.stringify(foreground),'no reference line visible through grey or purple squares');}
                        finally {checks.beforeDatasetsDraw=draw;graph.update('none');}
                        assert(graph.data.datasets[4].data.length===6,'six anonymous plans preserved');
                    }
                """)
            db.rollback()

    def test_graph_labels_hidden_preview_cost_annotation_and_deliberate_choices(self):
        for app, helpers, branch in environments():
            _, html = decision_case(app, helpers, branch)
            html = html.replace('/static/', Path('_static').resolve().as_uri() + '/')
            # Record the first draw too: the removed technical label must never flash.
            recorder = """<script>
                window.firstDrawLabels=[];
                const originalFill=CanvasRenderingContext2D.prototype.fillText;
                CanvasRenderingContext2D.prototype.fillText=function(text,...args){
                    window.firstDrawLabels.push(String(text));return originalFill.call(this,text,...args);
                };
            </script>"""
            html = html.replace('<script src=', recorder + '<script src=', 1)
            self.browser(html, r"""
                const format=window.labDecisionDisplayNumber;
                for(const [raw,expected] of [['46.875','46.88'],['58.8','58.80'],['30.000','30'],['275/3','91.67'],['-250','-250'],['-46.875','-46.88']]) assert(format(raw)===expected,'display only '+raw);
                const slider=document.getElementById('retirement-slider');
                const field=document.getElementById('retirement-value');
                const confirm=document.getElementById('confirm-retirement');
                const form=document.getElementById('form');
                const equipment=Chart.getChart('equipment-chart');
                const cost=Chart.getChart('cost-chart');
                assert(field.value==='' && confirm.disabled && slider.hasAttribute('data-untouched'),'no initial choice');
                assert(document.getElementById('selected-retirement').textContent.trim()==='— unità','no visible selected zero');
                assert(!form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})),'untouched cannot submit');
                assert(slider.min==='0' && slider.max==='100' && slider.step==='1','same integer range');
                assert(equipment.options.scales.x.title.text==='Periodo','Italian x');
                assert(equipment.options.scales.y.title.text==='Unità di attrezzatura','Italian y');
                assert(equipment.data.datasets[0].label==='La tua attrezzatura','own label');
                assert(equipment.data.datasets[1].label==='Attrezzatura media del tuo gruppo','group label');
                assert(equipment.data.datasets[2].label==='','no technical preview label');
                assert(!equipment.legend.legendItems.some(item=>item.datasetIndex===2),'no preview legend');
                assert(!equipment.options.plugins.tooltip.filter({datasetIndex:2}),'no preview tooltip');
                assert(equipment.options.plugins.tooltip.filter({datasetIndex:1}),'group tooltip retained');
                assert(cost.options.scales.x.title.text==='Unità di attrezzatura','cost x');
                assert(document.querySelector('.graph-row').children.length===2,'equipment left and cost right without an extra message grid cell');
                const message=document.getElementById('public-report-mean');
                if(message) assert(!message.closest('.graph-row'),'public message retained above the graphs');
                assert(cost.options.scales.y.title.text==='Costo','cost y');
                const tooltip=equipment.options.plugins.tooltip.callbacks.label;
                assert(tooltip({dataset:{label:'Attrezzatura media del tuo gruppo'},parsed:{y:275/3}}).endsWith('91.67'),'group tooltip rounded only for display');
                const boxes=Array.from(document.querySelectorAll('.graph-row .chart-box'));
                assert(boxes.length===2 && boxes[0].clientHeight===boxes[1].clientHeight,'equal graph heights');
                assert(cost.data.datasets[1].data.length===0,'no initial cost choice');
                assert(!window.firstDrawLabels.some(s=>/anteprima|confermata|Unconfirmed|Preview/i.test(s)),'no technical labels even on first draw');
                assert(!window.firstDrawLabels.includes('0 punti'),'no cost annotation before a choice');
                assert(cost.options.scales.x.ticks.maxRotation===0,'readable cost ticks');
                const drawn=[];
                const fillText=CanvasRenderingContext2D.prototype.fillText;
                CanvasRenderingContext2D.prototype.fillText=function(text,...args){drawn.push(String(text));return fillText.call(this,text,...args);};
                equipment.draw();
                assert(drawn.includes('Accertamento') && drawn.includes('principale') && drawn.includes('finale'),'short Italian markers');
                slider.click();
                assert(field.value==='0' && !confirm.disabled && !slider.hasAttribute('data-untouched'),'deliberate initial zero works');
                assert(cost.data.datasets[1].data[0].y===0 && drawn.includes('0 punti'),'initial zero annotation');
                for(const [d,value,label] of [[20,40,'40 punti'],[25,62.5,'62.50 punti'],[1,0.10,'0.10 punti'],[100,1000,'1000 punti'],[0,0,'0 punti']]) {
                    drawn.length=0;slider.value=String(d);slider.dispatchEvent(new Event('input'));
                    assert(field.value===String(d) && !confirm.disabled && !slider.hasAttribute('data-untouched'),'explicit choice');
                    assert(equipment.data.datasets[2].data[1].y===100-d,'equipment preview retained');
                    assert(cost.data.datasets[1].data[0].y===value,'same cost source');
                    assert(document.getElementById('selected-cost').textContent===label,'exact summary');
                    assert(drawn.includes(label),'cost visibly drawn without hovering: '+d+' ('+cost.width+'x'+cost.height+'): '+drawn.join(','));
                }
                CanvasRenderingContext2D.prototype.fillText=fillText;
                assert(form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})),'deliberate zero may submit');
                assert(!document.querySelector('input[type=number]'),'slider only');
            """)
            db.rollback()

    def test_zero_equipment_still_continues_without_slider_or_interaction(self):
        for app, helpers, branch in environments():
            _, html = decision_case(app, helpers, branch, zero=True)
            html = html.replace('/static/', Path('_static').resolve().as_uri() + '/')
            self.browser(html, """
                assert(!document.getElementById('retirement-slider'),'no decision at zero');
                assert(document.getElementById('retirement-value').value==='0','normal zero submission');
                const button=document.getElementById('confirm-retirement');
                assert(!button.disabled && button.textContent==='Continua','zero Continue retained');
                assert(document.getElementById('form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})),'normal form');
                assert(Chart.getChart('cost-chart').data.datasets[1].data.length===0,'cost curve retained without a selected point at zero');
            """)
            db.rollback()

    def test_ordinary_main_final_preview_has_no_name_legend_or_tooltip(self):
        for app, helpers, branch in environments():
            session = helpers.make_session(branch) if branch else helpers.make_session()
            helpers.ready(session)
            for period in range(1, 11):
                group = helpers.subsession(session, period).get_groups()[0]
                if period == 1:
                    helpers.reports(group)
                player = group.get_players()[0]
                if period in (1, 5, 10):
                    html = Template(Path(app.__name__, 'Decision.html').read_text()).render(dict(player=player, **app.Decision.vars_for_template(player)))
                    html = html.replace('/static/', Path('_static').resolve().as_uri() + '/')
                    self.browser(html, """
                        const chart=Chart.getChart('equipment-chart');
                        const slider=document.getElementById('retirement-slider');
                        slider.value='1';slider.dispatchEvent(new Event('input'));
                        assert(chart.data.datasets[2].data[1].y===99,'preview still updates');
                        assert(chart.data.datasets[2].label==='','unnamed preview');
                        assert(!chart.legend.legendItems.some(x=>x.datasetIndex===2),'no preview legend at any check');
                        assert(!chart.options.plugins.tooltip.filter({datasetIndex:2}),'no preview tooltip at any check');
                        assert(!/Anteprima della dismissione non confermata|Unconfirmed discontinuation preview/.test(document.body.innerText),'no visible technical label');
                    """)
                helpers.run_period(group, [0]*6)
                if period in (1, 5, 10):
                    html = Template(Path(app.__name__, 'Result.html').read_text()).render(dict(player=player, **app.Result.vars_for_template(player)))
                    html = html.replace('/static/', Path('_static').resolve().as_uri() + '/')
                    self.browser(html, """
                        const chart=Chart.getChart('equipment-chart');
                        assert(chart.data.datasets[2].label==='','no Results preview name');
                        assert(!chart.legend.legendItems.some(x=>x.datasetIndex===2),'no Results preview legend');
                        assert(!chart.options.plugins.tooltip.filter({datasetIndex:2}),'no Results preview tooltip');
                    """)
            db.rollback()

    def test_fractional_budget_and_group_tooltip_display_without_changing_records(self):
        for app, helpers, branch in environments():
            session = helpers.make_session(branch) if branch else helpers.make_session()
            helpers.ready(session)
            group = helpers.subsession(session).get_groups()[0]
            helpers.run_period(group, [25, 25, 0, 0, 0, 0])
            player = group.get_players()[0].in_round(2)
            html = Template(Path(app.__name__, 'Decision.html').read_text()).render(dict(player=player, **app.Decision.vars_for_template(player)))
            html = html.replace('/static/', Path('_static').resolve().as_uri() + '/')
            self.browser(html, """
                assert(document.getElementById('current-wallet').textContent==='937.50 punti','display budget to two decimals');
                const chart=Chart.getChart('equipment-chart');
                const raw=chart.data.datasets[1].data.find(point=>point.x===1).y;
                assert(Math.abs(raw-275/3)<1e-9,'unrounded stored group mean source');
                assert(chart.options.plugins.tooltip.callbacks.label({dataset:chart.data.datasets[1],parsed:{y:raw}}).endsWith('91.67'),'rounded group tooltip');
                assert(document.getElementById('retirement-value').value==='','rounding does not choose a decision');
            """)
            db.rollback()

    def test_reports_deliberate_zero_both_answers_required_and_endpoint_labels(self):
        from otree.forms.forms import get_form
        for app, helpers, branch in environments():
            session = helpers.make_session(branch) if branch else helpers.make_session()
            helpers.ready(session)
            player = helpers.subsession(session).get_players()[0]
            context = dict(player=player, **app.Reports.vars_for_template(player))
            context['form'] = get_form(player, app.Reports.form_fields, app.Reports, None)
            html = Template(Path(app.__name__, 'Reports.html').read_text()).render(context)
            html = html.replace('/static/', Path('_static').resolve().as_uri() + '/')
            self.browser(html, """
                const first=document.getElementById('report-own-slider');
                const second=document.getElementById('report-group-slider');
                const own=document.getElementById('report-own-value');
                const group=document.getElementById('report-group-value');
                const button=document.getElementById('reports-continue');
                const form=document.getElementById('form');
                assert(button.disabled && own.value==='' && group.value==='','both reports unselected');
                assert(first.hasAttribute('data-untouched') && second.hasAttribute('data-untouched'),'hidden initial handles');
                assert(!form.dispatchEvent(new Event('submit',{cancelable:true,bubbles:true})),'untouched reports cannot submit');
                for(const slider of [first,second]) assert(slider.min==='0' && slider.max==='100' && slider.step==='1','report bounds');
                for(const endpoints of document.querySelectorAll('.report-slider-endpoints')) assert(endpoints.textContent==='0100','report endpoints');
                first.click();
                assert(own.value==='0' && group.value==='' && button.disabled,'deliberate zero alone not enough');
                assert(document.getElementById('report-own-selected').textContent==='0','zero shown');
                second.value='37';second.dispatchEvent(new Event('input'));
                assert(group.value==='37' && !button.disabled,'both deliberate reports enable Continue');
                assert(document.getElementById('report-group-selected').textContent==='37','second value shown');
                assert(form.dispatchEvent(new Event('submit',{cancelable:true,bubbles:true})),'both reports may submit');
            """)
            db.rollback()

    def test_reduced_equipment_fixed_scales_grey_region_and_current_references(self):
        for app, helpers, branch in environments():
            session = helpers.make_session(branch) if branch else helpers.make_session()
            helpers.ready(session)
            group = helpers.subsession(session).get_groups()[0]
            helpers.run_period(group, [28]*6)
            player = group.get_players()[0].in_round(2)
            html = Template(Path(app.__name__, 'Decision.html').read_text()).render(dict(player=player, **app.Decision.vars_for_template(player)))
            html = html.replace('/static/', Path('_static').resolve().as_uri() + '/')
            self.browser(html, """
                const config=JSON.parse(document.getElementById('lab-chart-config').textContent);
                const slider=document.getElementById('retirement-slider');
                const cost=Chart.getChart('cost-chart');
                const graph=Chart.getChart('equipment-chart');
                assert(slider.max==='72','only feasible equipment selectable');
                assert(cost.options.scales.x.min===0 && cost.options.scales.x.max===100,'fixed full x scale');
                assert(cost.options.scales.y.min===0 && cost.options.scales.y.max===1000,'fixed full y scale');
                assert(cost.data.datasets[0].data.length===101,'entire cost function');
                assert(cost.data.datasets[0].segment.borderColor({p1:{parsed:{x:73}}})==='#b8b8b8','unavailable curve grey');
                assert(cost.data.datasets[0].segment.borderColor({p1:{parsed:{x:72}}})==='#007bff','feasible curve active');
                assert(document.querySelector('.decision-slider-endpoints').textContent==='0100','fixed slider endpoint labels');
                const reference=graph.config.plugins.find(p=>p.id==='knownMainThreshold'||p.id==='ambiguityThreshold');
                if(reference) {
                    const ctx=graph.ctx, moves=[], lines=[];
                    const oldMove=ctx.moveTo, oldLine=ctx.lineTo;
                    ctx.moveTo=function(x,y){moves.push([x,y]);return oldMove.call(this,x,y);};
                    ctx.lineTo=function(x,y){lines.push([x,y]);return oldLine.call(this,x,y);};
                    try { reference.beforeDatasetsDraw(graph); }
                    finally {ctx.moveTo=oldMove;ctx.lineTo=oldLine;}
                    const bounds=Object.hasOwn(config,'thresholdLow')?[config.thresholdLow,config.thresholdHigh]:[config.threshold];
                    const mainX=graph.scales.x.getPixelForValue(5);
                    assert(moves.length===bounds.length && lines.length===bounds.length,'only public threshold references');
                    bounds.forEach((value,index)=>{
                        const expectedY=graph.scales.y.getPixelForValue(value);
                        assert(Math.abs(moves[index][0]-(mainX-16))<0.01 && Math.abs(lines[index][0]-(mainX+16))<0.01,'short marker centered at Period 5');
                        assert(Math.abs(moves[index][1]-expectedY)<0.01 && Math.abs(lines[index][1]-expectedY)<0.01,'configured public threshold coordinate');
                    });
                }

                slider.value='73';slider.dispatchEvent(new Event('input'));
                assert(document.getElementById('retirement-value').value==='72','cannot submit above current equipment');
                assert(document.getElementById('selected-unit-count').textContent==='72','number box updates');
                assert(getComputedStyle(document.getElementById('selected-unit-count')).fontSize==='38px','current number font');
                if(Object.hasOwn(config,'publicReportMean')) {
                    const mean=graph.data.datasets[3], plans=graph.data.datasets[4];
                    assert(mean.pointStyle==='rect' && mean.label==='Attrezzatura media prevista','public mean square');
                    assert(mean.data[0].x===5 && mean.data[0].y===config.publicReportMean,'public mean at Main');
                    assert(plans.pointStyle==='rect' && plans.label==='Attrezzatura individuale prevista','individual planned squares');
                    assert(plans.data.length===6 && plans.data.every(p=>p.x===5),'six anonymous plans at Main');
                    assert(JSON.stringify(plans.data.map(p=>p.y))===JSON.stringify(config.publicReportPlans),'stored report primitives');
                    assert(!document.getElementById('public-report-mean'),'no repeated public mean box');
                    const tooltip=graph.options.plugins.tooltip.callbacks.label({datasetIndex:3,parsed:{y:config.publicReportMean}});
                    assert(tooltip==='Attrezzatura media prevista al Periodo 5: '+window.labDisplayNumber(config.publicReportMean)+' unità','planned tooltip wording');
                } else assert(!Object.hasOwn(config,'publicReportPlans'),'no individual disclosure outside M');
            """)
            db.rollback()
