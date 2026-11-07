"""Validated, date-aware data input for the reusable graphic weekly report."""
from collections import Counter
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json
import math
import re

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent
TOKEN_FIELDS = ('input', 'cache_write', 'cache_read', 'output')
COLORS = ['#157f79', '#4c79b5', '#bc8658', '#8c75b6', '#b59b45', '#708996', '#a7b5bd', '#cbd4d9']


class ReportError(ValueError):
    pass


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportError(f'无法读取 JSON：{path}：{exc}') from exc


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def period_dates(period):
    try:
        start, end = date.fromisoformat(period['start']), date.fromisoformat(period['end'])
        zone = ZoneInfo(period['timezone'])
    except (ValueError, KeyError) as exc:
        raise ReportError('period 的日期或时区无效') from exc
    if not 1 <= (end - start).days + 1 <= 31:
        raise ReportError('报告须覆盖 1 至 31 个完整日期；周报通常为 7 天')
    return start, end, zone


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ReportError(f'{label} 必须是有限、非负数字')
    return value


def _date_label(value, start, end):
    """Resolve MM-DD safely across New Year, without assigning every row this year."""
    label = str(value).strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', label):
        return date.fromisoformat(label)
    if not re.fullmatch(r'\d{2}-\d{2}', label):
        raise ReportError(f'不支持的日期标记：{value}')
    candidates = []
    for year in range(start.year - 1, end.year + 2):
        try:
            candidate = date.fromisoformat(f'{year}-{label}')
        except ValueError:
            continue
        if start - timedelta(days=1) <= candidate <= end:
            candidates.append(candidate)
    if len(candidates) != 1:
        raise ReportError(f'日期 {value} 不属于当前统计周期，或无法唯一定位年份')
    return candidates[0]


def _timestamp(value, start, end, zone):
    text = re.sub(r'#\d+$', '', str(value).strip())
    if re.match(r'^\d{4}-\d{2}-\d{2}[T ]', text):
        parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
        return parsed.replace(tzinfo=zone) if parsed.tzinfo is None else parsed.astimezone(zone)
    match = re.fullmatch(r'(?:(\d{2}-\d{2}) )?(\d{2}):(\d{2})', text)
    if not match:
        raise ReportError(f'不支持的回合时间：{value}')
    day = _date_label(match[1], start, end) if match[1] else start
    if not match[1] and start != end:
        raise ReportError('多日统计中的回合时间必须包含 MM-DD 日期')
    return datetime.combine(day, time(int(match[2]), int(match[3])), zone)


def validate_data(data):
    def check_finite(value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ReportError('报告数据不能包含 NaN 或 Infinity')
        if isinstance(value, dict):
            for item in value.values():
                check_finite(item)
        elif isinstance(value, list):
            for item in value:
                check_finite(item)
    check_finite(data)
    schema = read_json(ROOT / 'report.schema.json')
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data), key=lambda e: str(e.path))
    if errors:
        raise ReportError('\n'.join(f'{".".join(map(str,e.path)) or "report"}：{e.message}' for e in errors[:15]))
    if data['status'] != 'ready':
        raise ReportError('这是待整理草稿；读完证据、补齐成果与分类后，将 status 设为 ready 再生成')
    if data.get('unassigned_sessions'):
        raise ReportError('还有未归类的会话：unassigned_sessions 必须清空')
    period_dates(data['period'])
    streams = data['workstreams']
    ids = [s['id'] for s in streams]
    if len(ids) != len(set(ids)):
        raise ReportError('workstreams.id 不能重复')
    for output in data['outputs']:
        if output['workstream'] not in ids:
            raise ReportError(f'成果 {output["id"]} 引用了不存在的工作线')
    if len({x['id'] for x in data['outputs']}) != len(data['outputs']):
        raise ReportError('outputs.id 不能重复')
    if len({p['level'] for p in data['priorities']}) != len(data['priorities']):
        raise ReportError('同一优先级不能重复定义')
    pages = data['pages']
    widgets = list(pages.get('results', {}).get('widgets', []))
    for name in ('performance', 'pipeline'):
        if pages.get(name):
            widgets.append(pages[name])
    for widget in widgets:
        if widget['workstream'] not in ids:
            raise ReportError('图形引用的 workstream 不存在：' + widget['workstream'])
    perf = pages.get('performance', {})
    reg = perf.get('regression')
    if reg and reg['passed'] > reg['after']:
        raise ReportError('regression.passed 不能大于 after')
    det = perf.get('detection')
    if det and max(det['before'], det['after']) > det['total']:
        raise ReportError('检出数量不能大于样本总数')
    pipe = pages.get('pipeline', {})
    if pipe:
        statuses = [s['id'] for s in pipe['statuses']]
        if len(statuses) != len(set(statuses)):
            raise ReportError('pipeline.statuses.id 重复')
        for row in pipe['rows']:
            if row['status'] not in statuses:
                raise ReportError('投库/项目状态不存在：' + row['status'])
    for widget in pages.get('results', {}).get('widgets', []):
        if widget['type'] == 'checks' and widget['errors'] > widget['verified']:
            raise ReportError('checks.errors 不能大于 verified')


def aggregate_stats(data, stats):
    start, end, zone = period_dates(data['period'])
    boundary = datetime.combine(start, time.min, zone)
    if not isinstance(stats.get('sessions'), list):
        raise ReportError('stats.json 缺少 sessions 数组')
    for field, expected in [('start', start), ('end', end)]:
        try:
            actual = datetime.fromisoformat(stats[field].replace('Z', '+00:00'))
        except (KeyError, ValueError, AttributeError) as exc:
            raise ReportError('stats.json 缺少有效的 start/end') from exc
        if actual.tzinfo is None or actual.astimezone(zone).date() != expected:
            raise ReportError(f'stats.json 的 {field} 与本期日期不一致；禁止使用上一周统计')
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    index = {day: i for i, day in enumerate(days)}
    assigned = {}
    for stream in data['workstreams']:
        for key in stream['session_keys']:
            if key in assigned:
                raise ReportError('会话重复归类，可能造成重复统计：' + key)
            assigned[key] = stream['id']
    actual_keys = [s.get('key') for s in stats['sessions']]
    if any(not isinstance(k, str) or not k for k in actual_keys) or len(actual_keys) != len(set(actual_keys)):
        raise ReportError('stats.json 会话 key 缺失或重复')
    if set(actual_keys) != set(assigned):
        missing, extra = sorted(set(actual_keys) - set(assigned)), sorted(set(assigned) - set(actual_keys))
        raise ReportError(f'会话分类不完整：未归类 {missing[:8]}；不存在的 key {extra[:8]}')
    tokens = [0] * len(days)
    turns = [0] * len(days)
    heat = [[0] * 24 for _ in days]
    totals = {s['id']: {'tokens': 0, 'turns': 0, 'sessions': 0} for s in data['workstreams']}
    carry_tokens = carry_turns = output_tokens = total_tokens = 0
    sessions = []
    for session in stats['sessions']:
        key = session['key']
        stream = assigned[key]
        usage = session.get('usage_main')
        if not isinstance(usage, dict):
            raise ReportError('会话缺少 usage_main：' + key)
        tok = 0
        for model, block in usage.items():
            if not isinstance(block, dict):
                raise ReportError('usage_main 模型用量格式错误：' + key)
            for field in TOKEN_FIELDS:
                value = _number(block.get(field, 0), f'{key}.{model}.{field}')
                tok += value
                if field == 'output':
                    output_tokens += value
        # 采集器把子代理用量并入母会话的 usage_by_day，另在 subagents 列明细。
        # 会话合计必须同口径计入，否则派过子代理的会话会与分日统计对不上。
        for agent in session.get('subagents') or []:
            if not isinstance(agent, dict):
                raise ReportError('subagents 条目格式错误：' + key)
            for model, block in (agent.get('usage') or {}).items():
                if not isinstance(block, dict):
                    raise ReportError('子代理用量格式错误：' + key)
                for field in TOKEN_FIELDS:
                    value = _number(block.get(field, 0), f'{key}.subagent.{model}.{field}')
                    tok += value
                    if field == 'output':
                        output_tokens += value
        by_day = session.get('usage_by_day')
        if not isinstance(by_day, dict):
            raise ReportError('缺少 usage_by_day；请用采集器的 --to 参数生成分日统计')
        day_total = 0
        for label, raw_value in by_day.items():
            value = _number(raw_value, f'{key}.usage_by_day.{label}')
            day_total += value
            day = _date_label(label, start, end)
            if day < start:
                if data['period'].get('carry_in') != 'previous_turn' or day != start - timedelta(days=1):
                    raise ReportError('含期前 token，但没有显式启用 previous_turn 归属规则')
                carry_tokens += value
                day = start
            if day not in index:
                raise ReportError('统计含期外用量：' + label)
            tokens[index[day]] += value
        if abs(day_total-tok) > .001:
            raise ReportError(f'会话 {key} 的分日用量与模型用量不一致')
        user_turns = session.get('user_turns')
        if not isinstance(user_turns, list):
            raise ReportError('会话缺少 user_turns 数组：' + key)
        for turn in user_turns:
            stamp = _timestamp(turn['time'], start, end, zone)
            day = stamp.date()
            if day < start:
                if data['period'].get('carry_in') != 'previous_turn' or not boundary - timedelta(hours=6) <= stamp < boundary:
                    raise ReportError('出现不在周期内、也不满足前 6 小时跨界规则的回合')
                carry_turns += 1
                day = start
            if day not in index:
                raise ReportError('回合时间不属于本期：' + str(turn['time']))
            turns[index[day]] += 1
            heat[index[day]][stamp.hour] += 1
        totals[stream]['tokens'] += tok
        totals[stream]['turns'] += len(user_turns)
        totals[stream]['sessions'] += 1
        total_tokens += tok
        first = _timestamp(session['from'], start, end, zone)
        last = _timestamp(session['to'], start, end, zone)
        if last < first:
            raise ReportError('会话结束早于开始：' + key)
        sessions.append({'key': key, 'name': session.get('title', key), 'stream': stream,
                         'from': first.isoformat(), 'to': last.isoformat(), 'tokens': tok,
                         'turns': len(user_turns)})
    if abs(sum(tokens) - total_tokens) > .001:
        raise ReportError(f'分日 token 合计 {sum(tokens)} 与 usage_main 合计 {total_tokens} 不一致；请核对采集口径')
    shares = []
    for i, stream in enumerate(data['workstreams']):
        row = dict(totals[stream['id']])
        row.update(id=stream['id'], name=stream['name'], color=COLORS[i % len(COLORS)],
                   percent=100 * row['tokens'] / total_tokens if total_tokens else 0)
        shares.append(row)
    return {'dates': [d.isoformat() for d in days], 'labels': [d.strftime('%m/%d') for d in days],
            'weekdays': ['一二三四五六日'[d.weekday()] for d in days],
            'weekend': [d.weekday() >= 5 for d in days], 'daily_tokens': tokens,
            'daily_turns': turns, 'heat': heat, 'sessions': sessions, 'shares': shares,
            'total_tokens': total_tokens, 'output_tokens': output_tokens,
            'total_turns': sum(turns), 'session_count': len(sessions),
            'carry_tokens': carry_tokens, 'carry_turns': carry_turns}


def load_report(path):
    path = Path(path).resolve()
    data = read_json(path)
    validate_data(data)
    stats_path = Path(data['sources']['stats'])
    if not stats_path.is_absolute():
        stats_path = path.parent / stats_path
    stats = read_json(stats_path)
    metrics = aggregate_stats(data, stats)
    return data, metrics, {'data_path': str(path), 'stats_path': str(stats_path.resolve()),
                           'data_sha256': file_hash(path), 'stats_sha256': file_hash(stats_path)}
