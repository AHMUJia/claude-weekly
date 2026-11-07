"""Collect Claude worklog statistics and prepare a blank, traceable weekly input."""
import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from build_report import atomic_write, dump_json
from report_model import ReportError, read_json, period_dates, aggregate_stats

ROOT = Path(__file__).resolve().parent


def sanitize_stats(stats):
    # Keep the exact numbers and timestamps. Do not ship prompt text or transcript paths.
    result = {k:stats[k] for k in ('start','end','multi_day') if k in stats}
    result['sessions'] = []
    for session in stats['sessions']:
        clean = {k:session[k] for k in ('key','title','from','to','turn_start','mode','usage_main','usage_by_day') if k in session}
        clean['user_turns'] = [{'time':t['time']} for t in session['user_turns']]
        # Subagent usage is already folded into usage_by_day; keep the breakdown so the
        # sanitized snapshot still balances. Task descriptions only, no prompts or paths.
        clean['subagents'] = [{k:a[k] for k in ('id','description','from','to','usage') if k in a}
                              for a in session.get('subagents') or []]
        result['sessions'].append(clean)
    return result


def empty_report(period, worklog_dir, stats):
    return {'schema_version':1,'status':'draft','period':period,
            'sources':{'stats':'stats.json','worklog_dir':str(worklog_dir),
                       'note':'统计来自本机 Claude 工作记录；成果须根据原始回合和已核验摘要整理。Token 不等于工时。'},
            'headline':'','workstreams':[],'outputs':[],'decisions':[],'priorities':[],
            'reflection':'','lessons':[],'pages':{},
            'unassigned_sessions':[{'key':s['key'],'title':s.get('title',s['key']),'turns':len(s['user_turns'])} for s in stats['sessions']]}


def prepare(stats, period, worklog_dir, data_root=None, raw_hash=None):
    start, end, _ = period_dates(period)
    # Validate the source before any file is changed. Temporary grouping checks totals only.
    stub = {'period':period,'workstreams':[{'id':'source','name':'源统计','session_keys':[s['key'] for s in stats['sessions']]}]}
    aggregate_stats(stub,stats)
    slug = start.strftime('%Y%m%d')+'-'+end.strftime('%Y%m%d')
    folder = (Path(data_root) if data_root else ROOT/'data')/slug
    clean = sanitize_stats(stats)
    clean_text = dump_json(clean)
    new_hash = hashlib.sha256(clean_text.encode('utf-8')).hexdigest()
    report_path, stats_path = folder/'report.json', folder/'stats.json'
    collection_path = folder/'collection.json'
    old_collection = read_json(collection_path) if collection_path.exists() else {}
    changed = stats_path.exists() and stats_path.read_text(encoding='utf-8-sig') != clean_text
    if raw_hash and old_collection.get('raw_source_sha256'):
        changed = changed or raw_hash != old_collection['raw_source_sha256']
    if report_path.exists():
        data = read_json(report_path)
        if data['period'] != period:
            raise ReportError('现有每期数据的周期或统计口径不同；请先核对，不能覆盖')
        if changed:
            stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            atomic_write(folder/'history'/f'report-{stamp}.json',dump_json(data))
            if stats_path.exists():
                atomic_write(folder/'history'/f'stats-{stamp}.json',stats_path.read_text(encoding='utf-8-sig'))
            data['status'] = 'draft'
            valid_keys = {s['key'] for s in clean['sessions']}
            for stream in data['workstreams']:
                stream['session_keys'] = [key for key in stream['session_keys'] if key in valid_keys]
            assigned = {key for stream in data['workstreams'] for key in stream['session_keys']}
            data['unassigned_sessions'] = [{'key':s['key'],'title':s.get('title',s['key']),'turns':len(s['user_turns'])} for s in clean['sessions'] if s['key'] not in assigned]
    else:
        data = empty_report(period,worklog_dir,clean)
    atomic_write(stats_path,clean_text)
    atomic_write(report_path,dump_json(data))
    manifest = {'collected_at':datetime.now(timezone.utc).isoformat(),'period':period,
                'worklog_dir':str(worklog_dir),'sanitized_stats_sha256':new_hash,
                'raw_source_sha256':raw_hash or old_collection.get('raw_source_sha256'),
                'sessions':len(clean['sessions']),'needs_review':data['status']!='ready'}
    atomic_write(collection_path,dump_json(manifest))
    return {'data':str(report_path),'status':data['status'],'sessions':len(clean['sessions']),
            'unassigned':len(data.get('unassigned_sessions',[])),
            'next':'按 CLAUDE.md 读取原始回合、补齐 report.json，再运行 build_report.py'}


def prepare_plan(stats, worklog_dir, config):
    """Same summaries/plan contract as the installed worklog skill, using its real config root."""
    worklog_dir = Path(worklog_dir)
    summaries_path = worklog_dir/'summaries.json'
    summaries = read_json(summaries_path) if summaries_path.exists() else {}
    start, end = date.fromisoformat(stats['start'][:10]), date.fromisoformat(stats['end'][:10])
    for i in range((end-start).days+1):
        day = start+timedelta(days=i)
        daily = Path(config['worklog_root'])/day.strftime('%Y%m%d')/'summaries.json'
        if daily.exists():
            for key, value in read_json(daily).items():
                target = summaries.setdefault(key,{})
                for name in ('request','delivery'):
                    target.setdefault(name,value.get(name,''))
                for turn_key, turn_text in value.get('turns',{}).items():
                    key_with_date = turn_key if ' ' in turn_key else f'{day:%m-%d} {turn_key}'
                    target.setdefault('turns',{}).setdefault(key_with_date,turn_text)
                for name, label in value.get('subagent_names',{}).items():
                    target.setdefault('subagent_names',{}).setdefault(name,label)
    plan = {}
    for s in stats['sessions']:
        counts, turns = Counter(), []
        for turn in s['user_turns']:
            counts[turn['time']] += 1
            key = turn['time'] + (f'#{counts[turn["time"]]}' if counts[turn['time']]>1 else '')
            turns.append({'key':key,'text':turn.get('text',''),
                          'existing_summary':summaries.get(s['key'],{}).get('turns',{}).get(key)})
        transcript = s.get('transcript')
        if not transcript and s.get('cli_session_id'):
            found = list((Path(config['claude_config_dir'])/'projects').glob('*/'+s['cli_session_id']+'.jsonl'))
            transcript = str(found[0]) if found else None
        plan[s['key']] = {'title':s.get('title',s['key']),'cwd':s.get('cwd',''),
                          'transcript':transcript,'active':s['from']+'~'+s['to'],'turns':turns,
                          'subagent_descriptions':[x.get('description','') for x in s.get('subagents',[])],
                          'existing_request':summaries.get(s['key'],{}).get('request'),
                          'existing_delivery':summaries.get(s['key'],{}).get('delivery')}
    atomic_write(summaries_path,dump_json(summaries))
    atomic_write(worklog_dir/'plan.json',dump_json(plan))


def main():
    parser = argparse.ArgumentParser(description='图解周报的数据采集入口；成果由 Claude 读原始记录后整理')
    parser.add_argument('--config',default=str(ROOT/'report_config.json'))
    sub = parser.add_subparsers(dest='command',required=True)
    for name in ('collect','prepare'):
        p = sub.add_parser(name,help='采集本机工作记录' if name=='collect' else '导入已有统计')
        p.add_argument('--start',required=True)
        p.add_argument('--end',required=True)
        p.add_argument('--data-root',help='数据目录；默认使用方案目录下的 data')
        p.add_argument('--carry-in',choices=['none','previous_turn'],default='previous_turn')
        if name=='prepare':
            p.add_argument('--stats',required=True)
    args = parser.parse_args()
    try:
        config = read_json(args.config)
        period = {'start':args.start,'end':args.end,'timezone':config['timezone'],'carry_in':args.carry_in}
        start,end,_ = period_dates(period)
        slug = start.strftime('%Y%m%d')+'-'+end.strftime('%Y%m%d')
        worklog_dir = Path(config['worklog_root'])/slug
        if args.command=='collect':
            collector = Path(config['collector'])
            if not collector.is_file():
                raise ReportError('找不到现有 worklog 采集器，请检查 report_config.json')
            env = {**os.environ,'CLAUDE_CONFIG_DIR':config['claude_config_dir'],
                   'WORKLOG_TZ':config['collector_timezone'],'PYTHONIOENCODING':'utf-8'}
            result = subprocess.run([sys.executable,str(collector),args.start,'00:00','--to',args.end],
                                    env=env,capture_output=True,text=True,encoding='utf-8',check=False)
            if result.returncode:
                raise ReportError('原始采集失败：'+result.stderr[-1500:])
            stats = json.loads(result.stdout)
            raw_hash = hashlib.sha256(result.stdout.encode('utf-8')).hexdigest()
            outcome = prepare(stats,period,worklog_dir,args.data_root,raw_hash)
            source_path = worklog_dir/'stats.json'
            if source_path.exists() and source_path.read_text(encoding='utf-8-sig')!=result.stdout:
                stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
                atomic_write(worklog_dir/'history'/f'stats-{stamp}.json',source_path.read_text(encoding='utf-8-sig'))
            atomic_write(source_path,result.stdout)
            prepare_plan(stats,worklog_dir,config)
            outcome['plan'] = str(worklog_dir/'plan.json')
        else:
            source_path = Path(args.stats).resolve()
            stats = read_json(source_path)
            raw_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
            outcome = prepare(stats,period,source_path.parent,args.data_root,raw_hash)
        print(dump_json(outcome))
    except (ReportError,OSError,ValueError,KeyError,TypeError) as exc:
        print(f'准备未完成：{exc}',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
