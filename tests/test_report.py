from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from build_report import build, dump_json
from report_layout import render_report, md
from report_model import aggregate_stats, validate_data, load_report, ReportError
from weekly_report import prepare, sanitize_stats
from fixtures import sample, extended


class ReportTests(unittest.TestCase):
    def setUp(self):
        qa = ROOT/'验收'
        qa.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix='test-',dir=qa)
        self.folder = Path(self.tmp.name).resolve()
        assert qa.resolve() in self.folder.parents
        self.addCleanup(self.tmp.cleanup)

    def write(self,data,stats):
        (self.folder/'report.json').write_text(dump_json(data),encoding='utf-8')
        (self.folder/'stats.json').write_text(dump_json(stats),encoding='utf-8')
        return self.folder/'report.json'

    def test_bundled_sample_renders(self):
        """随包的虚构示例必须能完整渲染；换成你自己的数据后，把下面的断言也换掉。"""
        data,m,p = load_report(ROOT/'data/20260105-20260111/report.json')
        self.assertEqual((m['session_count'],m['total_turns'],m['total_tokens']),(4,26,46800000))
        self.assertEqual(m['daily_turns'],[5,5,3,6,5,2,0])
        self.assertEqual((m['carry_turns'],m['carry_tokens']),(0,0))
        html,pages = render_report(data,m,p)
        self.assertEqual(pages,6)
        self.assertIn('数据清洗流水线',html)
        self.assertIn('2026.01.05 — 01.11',html)
        for stream in data['workstreams']:
            self.assertIn(md(stream['body']),html)
        for decision in data['decisions']:
            self.assertIn(md(decision['body']),html)
        self.assertIn(md(data['reflection']),html)

    def test_cross_year_new_projects_auto_scale(self):
        data,stats = sample()
        path = self.write(data,stats)
        result = build(path,self.folder/'fresh.html')
        html = (self.folder/'fresh.html').read_text(encoding='utf-8')
        self.assertEqual(result['pages'],3)
        for old in ('数据清洗流水线','月度报表','环境排查','2026.01.05','2026-01-11'):
            self.assertNotIn(old,html)
        self.assertIn('2026.12.30 — 2027.01.05',html)
        m = aggregate_stats(data,stats)
        self.assertEqual(m['daily_tokens'],[0,900000000,0,200000000,0,0,0])
        self.assertEqual(m['weekdays'],list('三四五六日一二'))
        self.assertEqual(m['total_turns'],189)

    def test_empty_period_has_no_nan(self):
        data,stats = sample(empty=True)
        path = self.write(data,stats)
        build(path,self.folder/'empty.html')
        html = (self.folder/'empty.html').read_text(encoding='utf-8')
        self.assertNotIn('NaN',html)
        self.assertNotIn('Infinity',html)
        self.assertIn('暂无已确认成果',html)

    def test_optional_widgets_and_additional_pages(self):
        data,stats = extended()
        path = self.write(data,stats)
        result = build(path,self.folder/'extended.html')
        self.assertEqual(result['pages'],7)
        html = (self.folder/'extended.html').read_text(encoding='utf-8')
        self.assertIn('data-page="6"',html)
        self.assertIn('图示前 70 / 105 项',html)
        self.assertIn('101 项通过',html)
        self.assertIn('--statuses:4',html)

    def test_stale_or_bad_source_never_overwrites_output(self):
        data,stats = sample()
        output = self.folder/'preserved.html'
        output.write_text('approved',encoding='utf-8')
        for mutate in [lambda d,s:s.update(start='2026-10-30T00:00:00+08:00'),
                       lambda d,s:d.update(status='draft'),
                       lambda d,s:d['workstreams'][0]['session_keys'].append('session-b'),
                       lambda d,s:d['workstreams'][0].update(session_keys=[]),
                       lambda d,s:s['sessions'][0]['usage_by_day'].update({'12-31':1})]:
            d,s = deepcopy(data),deepcopy(stats)
            mutate(d,s)
            path = self.write(d,s)
            with self.assertRaises(ReportError):
                build(path,output)
            self.assertEqual(output.read_text(encoding='utf-8'),'approved')

    def test_schema_rejects_impossible_numbers(self):
        data,stats = sample()
        for invalid in [float('nan'),float('inf'),-1,True]:
            d=deepcopy(data)
            d['pages']['performance']={'title':'测试','workstream':'line-0','regression':{'before':0,'after':3,'passed':invalid}}
            with self.assertRaises(ReportError):validate_data(d)
        data['pages']['performance']={'title':'测试','workstream':'line-0','detection':{'before':2,'after':7,'total':6,'note':''}}
        with self.assertRaises(ReportError):validate_data(data)

    def test_carry_in_and_leap_day(self):
        data,stats = sample()
        s=stats['sessions'][0]
        s['user_turns'][0]['time']='12-29 23:45'
        s['usage_by_day']={'12-29':100,'12-31':899999900}
        m=aggregate_stats(data,stats)
        self.assertEqual((m['carry_turns'],m['carry_tokens']),(1,100))
        self.assertEqual(m['heat'][0][23],1)
        s['user_turns'][0]['time']='12-29 17:59'
        with self.assertRaises(ReportError):aggregate_stats(data,stats)
        d,s=sample(empty=True)
        d['period'].update(start='2028-02-28',end='2028-03-01')
        s.update(start='2028-02-28T00:00:00+08:00',end='2028-03-01T23:59:59+08:00')
        self.assertEqual(aggregate_stats(d,s)['dates'],['2028-02-28','2028-02-29','2028-03-01'])

    def test_untrusted_text_cannot_execute_or_load_images(self):
        text='<script>alert(1)</script>\n\n[open](javascript:alert)\n\n![private](https://example.test/track.png)\n\n[ok](https://example.test/)'
        html=md(text)
        self.assertNotIn('<script',html)
        self.assertNotIn('href="javascript',html)
        self.assertNotIn('<img',html)
        self.assertIn('href="https://example.test/"',html)

    def test_new_period_starts_blank_and_changed_source_returns_to_draft(self):
        data,stats=sample()
        result=prepare(stats,data['period'],self.folder/'worklog',self.folder/'data')
        path=Path(result['data'])
        blank=json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(blank['outputs'],[])
        self.assertEqual(blank['pages'],{})
        self.assertEqual(len(blank['unassigned_sessions']),2)
        path.write_text(dump_json(data),encoding='utf-8')
        result=prepare(stats,data['period'],self.folder/'worklog',self.folder/'data')
        self.assertEqual(result['status'],'ready')
        stats['sessions'][0]['user_turns'].append({'time':'12-31 15:00','text':'new'})
        result=prepare(stats,data['period'],self.folder/'worklog',self.folder/'data')
        self.assertEqual(result['status'],'draft')
        self.assertTrue(list((path.parent/'history').glob('report-*.json')))
        self.assertNotIn('text',sanitize_stats(stats)['sessions'][0]['user_turns'][0])

    def test_collect_cli_uses_configured_collector_and_prepares_plan(self):
        data,stats=sample()
        collector=self.folder/'fake_collector.py'
        collector.write_text('import sys,json,os\nassert sys.argv[1:]==["2026-12-30","00:00","--to","2027-01-05"]\nassert os.environ["WORKLOG_TZ"]=="+08:00"\nprint('+repr(dump_json(stats))+')\n',encoding='utf-8')
        config={'claude_config_dir':str(self.folder/'claude'),'worklog_root':str(self.folder/'worklog'),
                'collector':str(collector),'timezone':'Asia/Singapore','collector_timezone':'+08:00'}
        cp=self.folder/'config.json'
        cp.write_text(dump_json(config),encoding='utf-8')
        result=subprocess.run([sys.executable,str(ROOT/'weekly_report.py'),'--config',str(cp),'collect',
                               '--start','2026-12-30','--end','2027-01-05','--data-root',str(self.folder/'data')],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        outcome=json.loads(result.stdout)
        self.assertEqual(outcome['status'],'draft')
        plan=json.loads(Path(outcome['plan']).read_text(encoding='utf-8'))
        self.assertEqual(plan['session-a']['turns'][1]['key'],'12-31 09:20#2')

    def test_validate_only_writes_nothing(self):
        data,stats=sample()
        path=self.write(data,stats)
        output=self.folder/'unused.html'
        build(path,output,True)
        self.assertFalse(output.exists())


if __name__=='__main__':unittest.main()
