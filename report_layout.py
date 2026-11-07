# -*- coding: utf-8 -*-
"""Graphic-first weekly report. Original wording and SVGs remain in a detail drawer."""
from pathlib import Path
from html import escape
import re
import math
import markdown
from html.parser import HTMLParser
from urllib.parse import urlparse
from datetime import datetime

ROOT = Path(__file__).resolve().parent
COLORS = ['#157f79', '#4c79b5', '#bc8658', '#8c75b6', '#b59b45', '#708996', '#a7b5bd', '#cbd4d9']


def e(value):
    return escape(str(value), quote=True)


def n(value):
    if 0 < abs(value) < 1:
        return f'{value:.3g}'
    return f'{value:,.0f}' if float(value).is_integer() else f'{value:,.1f}'.rstrip('0').rstrip('.')


class SafeMarkdown(HTMLParser):
    allowed = set('p br hr h1 h2 h3 h4 h5 h6 ul ol li blockquote code pre strong em del table thead tbody tr th td a'.split())

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'img':
            self.parts.append(e(attrs.get('alt', '')))
        elif tag in self.allowed:
            attr = ''
            if tag == 'a':
                href = attrs.get('href', '')
                try:
                    safe = urlparse(href).scheme.lower() in ('http', 'https', 'mailto')
                except ValueError:
                    safe = False
                if safe:
                    attr = f' href="{e(href)}" rel="noopener noreferrer"'
            self.parts.append(f'<{tag}{attr}>')

    def handle_endtag(self, tag):
        if tag in self.allowed and tag not in ('br', 'hr'):
            self.parts.append(f'</{tag}>')

    def handle_data(self, value):
        self.parts.append(e(value))


def md(value):
    parser = SafeMarkdown()
    parser.feed(markdown.markdown(escape(value, quote=False), extensions=['tables', 'fenced_code', 'sane_lists']))
    return ''.join(parser.parts)


def icon(name):
    paths = {
        'code': '<rect x="3" y="4" width="26" height="22" rx="3"/><path d="m12 11-4 4 4 4m8-8 4 4-4 4m-3-10-3 18"/>',
        'data': '<ellipse cx="16" cy="7" rx="11" ry="4"/><path d="M5 7v17c0 5 22 5 22 0V7M5 15c0 5 22 5 22 0"/>',
        'clinical': '<rect x="5" y="5" width="22" height="24" rx="3"/><path d="M11 5V2h10v3M11 16h10m-5-5v10"/>',
        'verify': '<path d="M16 2 5 7v10c0 7 11 13 11 13s11-6 11-13V7Z"/><path d="m10 16 4 4 8-9"/>',
        'slides': '<rect x="3" y="4" width="26" height="18" rx="2"/><path d="M16 22v7m-7 0h14M8 16l5-5 5 4 6-7"/>',
        'paper': '<path d="M7 2h13l6 6v22H7ZM20 2v7h6M11 15h11m-11 5h11m-11 5h7"/>',
        'arrow': '<path d="M4 16h23m-8-8 8 8-8 8"/>',
        'check': '<path d="m6 16 7 7L27 8"/>',
        'print': '<path d="M8 10V3h16v7M8 23H3V11h26v12h-5M8 19h16v11H8Z"/>',
        'book': '<path d="M3 5h10l3 3 3-3h10v23H19l-3 2-3-2H3ZM16 8v22"/>',
    }
    return '<svg viewBox="0 0 32 32" class="icon" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' + paths[name] + '</svg>'


def ring(values, colors, center, subtitle, interactive=False):
    out = [f'<svg viewBox="0 0 360 360" role="img" aria-label="{e(subtitle)}">']
    total, acc = sum(values), 0
    if not total:
        out.append('<circle cx="180" cy="180" r="132" fill="none" stroke="#e6ecef" stroke-width="30"/>')
    for i, value in enumerate(values):
        pct = 100 * value / total if total else 0
        if pct:
            gap = min(.85, pct * .12)
            out.append(f'<circle cx="180" cy="180" r="132" fill="none" stroke="{colors[i % len(colors)]}" stroke-width="30" pathLength="100" stroke-dasharray="{pct-gap:.4f} {100-pct+gap:.4f}" stroke-dashoffset="{-acc:.4f}" transform="rotate(-90 180 180)"/>')
        acc += pct
    value_id = ' id="share-value"' if interactive else ''
    label_id = ' id="share-label"' if interactive else ''
    out += [f'<text x="180" y="183" text-anchor="middle" class="ring-value"{value_id}>{e(center)}</text>',
            f'<text x="180" y="216" text-anchor="middle" class="ring-sub"{label_id}>{e(subtitle)}</text></svg>']
    return ''.join(out)


def nice_top(value):
    if value <= 0:
        return 1
    power = 10 ** math.floor(math.log10(value))
    return next(x * power for x in (1, 2, 3, 4, 5, 6, 8, 10) if x * power >= value)


def bars(values, kind, metrics):
    top = nice_top(max(values, default=0))
    step = 548 / len(values)
    width = min(46, step * .65)
    unit = ' M token' if kind == 'token' else ' 轮'
    out = [f'<svg viewBox="0 0 620 250" role="img" aria-label="每日{e(unit)}">']
    divisions = 3 if top / (10 ** math.floor(math.log10(top))) in (3, 6) else 2
    for i in range(divisions+1):
        tick, y = top * i / divisions, 202 - i * 162 / divisions
        out.append(f'<line x1="40" x2="608" y1="{y}" y2="{y}" stroke="#e6ecef"/><text x="28" y="{y+4}" text-anchor="end" class="axis">{n(tick)}</text>')
    for i, value in enumerate(values):
        x, h = 52 + i * step + (step-width)/2, value / top * 162
        if metrics['weekend'][i]:
            out.append(f'<rect x="{x-5}" y="30" width="{width+10}" height="172" fill="#f2f5f6"/>')
        out.append(f'<g><title>{metrics["dates"][i]}：{n(value)}{unit}</title><rect x="{x}" y="{202-h}" width="{width}" height="{h}" rx="4" fill="{"#157f79" if value == max(values) else "#a4c9c8"}"/>')
        if len(values) <= 10:
            out.append(f'<text x="{x+width/2}" y="{191-h}" text-anchor="middle" class="chart-value">{n(value)}</text>')
        if len(values) <= 10 or i % math.ceil(len(values)/8) == 0 or i == len(values)-1:
            out.append(f'<text x="{x+width/2}" y="225" text-anchor="middle" class="axis">{metrics["labels"][i]}</text><text x="{x+width/2}" y="242" text-anchor="middle" class="axis faint">周{metrics["weekdays"][i]}</text>')
        out.append('</g>')
    return ''.join(out) + '</svg>'


def heatmap(metrics, interactive=True):
    out = ['<div class="heat-axis"><span></span>'+''.join(f'<span>{h:02d}</span>' if h%4==0 or h==23 else '<span></span>' for h in range(24))+'</div>']
    for i, values in enumerate(metrics['heat']):
        out.append(f'<div class="heat-row"><span class="heat-day">{metrics["labels"][i]}<small>周{metrics["weekdays"][i]}</small></span>')
        for hour, value in enumerate(values):
            tier = 0 if value==0 else 1 if value<=2 else 2 if value<=5 else 3 if value<=9 else 4
            label = f'{metrics["dates"][i]} 周{metrics["weekdays"][i]} {hour:02d}:00 · {value} 轮'
            if interactive:
                out.append(f'<button type="button" class="heat-cell h{tier}" tabindex="{0 if i==hour==0 else -1}" aria-label="{label}" title="{label}" data-label="{label}"></button>')
            else:
                out.append(f'<span class="heat-cell h{tier}" title="{label}"></span>')
        out.append('</div>')
    return ''.join(out)


def change_note(before, after, subject):
    if before == 0:
        return f'{subject}：{n(before)} → {n(after)}'
    change = 100 * (after - before) / before
    return f'{subject}约{"减少" if change < 0 else "增加"} {abs(change):.0f}%' if change else f'{subject}不变'


def performance(page, decision_count):
    panels = []
    if 'speed' in page:
        s = page['speed']
        before, after = s['before'], s['after']
        top = nice_top(max(before, after))
        svg = [f'<svg viewBox="0 0 600 230" role="img" aria-label="耗时从{before}{e(s["unit"])}变为{after}{e(s["unit"])}">']
        for i in range(5):
            x = 74 + i * 121
            svg.append(f'<path d="M{x} 30v160" stroke="#e4ecef"/><text x="{x}" y="216" text-anchor="middle" class="axis">{n(top*i/4)}{e(s["unit"]) if i==4 else ""}</text>')
        for value, y, label, color in [(before, 50, '调整前', '#d4dee4'), (after, 127, '调整后', '#157f79')]:
            width = value / top * 484
            inside = width > 400
            svg.append(f'<text x="8" y="{y+30}" class="axis">{label}</text><rect x="74" y="{y}" width="{width}" height="42" rx="5" fill="{color}"/><text x="{74+width-14 if inside else 74+width+14}" y="{y+29}" text-anchor="{"end" if inside else "start"}" class="bar-number">{n(value)}</text>')
        svg.append('</svg>')
        hero = s.get('headline', n(before/after) if after else '—')
        unit = s.get('headline_unit', '×')
        sample = f'{page["sample_count"]} 份样本实测' if 'sample_count' in page else ''
        panels.append(f'<article class="viz-panel speed-panel"><div class="panel-top"><h2>{e(s.get("headline_label", "耗时对比"))}</h2><span>{sample}</span></div><p class="hero-stat">{e(hero)}<span>{e(unit)}</span></p>{"".join(svg)}<div class="graph-caption"><span>{e(s["scope"])}</span><strong>{change_note(before,after,"耗时")}</strong></div></article>')
    if 'regression' in page:
        r = page['regression']
        visible = min(r['after'], 70)
        dots = ''.join(f'<i class="{"existing" if i<r["before"] else "added"}"></i>' for i in range(visible))
        dot_note = '每点 = 1 项' if r['after'] <= 70 else f'图示前 70 / {r["after"]} 项'
        passed = '全部通过' if r['passed'] == r['after'] else f'{r["passed"]} 项通过'
        delta = r['after'] - r['before']
        panels.append(f'<article class="viz-panel regression-panel"><div class="panel-top"><h2>回归验证</h2><span>{dot_note}</span></div><div class="small-stat">{n(r["before"])} <span>→</span> <strong>{n(r["after"])}</strong></div><div class="test-dots" aria-label="{r["after"]}项测试，{r["passed"]}项通过">{dots}</div><div class="legend"><span><i class="old-dot"></i>原有 {r["before"]}</span><span><i class="new-dot"></i>{"新增" if delta>=0 else "减少"} {abs(delta)}</span><b>{passed}</b></div></article>')
    if 'detection' in page:
        d = page['detection']
        rows = []
        for key, label in [('before','调整前'), ('after','调整后')]:
            if d['total'] <= 14:
                dots = ''.join(f'<span class="{"hit" if i<d[key] else "miss"}">{"✓" if i<d[key] else ""}</span>' for i in range(d['total']))
            else:
                dots = f'<span class="detection-bar"><i style="width:{100*d[key]/d["total"] if d["total"] else 0}%"></i></span>'
            rows.append(f'<div class="detection-row {key}"><span>{label}</span><div>{dots}</div><b>{d[key]}/{d["total"]}</b></div>')
        panels.append(f'<article class="viz-panel detection-panel"><div class="panel-top"><h2>样本检出</h2><span>同一组样本</span></div>{"".join(rows)}<p class="short-caption">{e(d["note"])}</p></article>')
    release = ''
    if page.get('release'):
        r = page['release']
        bits = f'<span>{n(r["size_mb"])} MB 安装包</span>' if 'size_mb' in r else ''
        if 'verified_files' in r:
            bits += f'<span>{n(r["verified_files"])} 个文件核验</span>'
        release = f'<div class="release-strip"><span class="release-label">本周交付</span><b>{e(r["version"])}</b>{bits}<button type="button" data-record="decisions">{decision_count} 项关键决策 ↗</button></div>'
    full = all(key in page for key in ('speed','regression','detection'))
    return '<div class="software-grid'+('' if full else ' flexible-panels')+'">'+''.join(panels)+'</div>'+release


def pipeline(page, next_index):
    statuses, rows = page['statuses'], page['rows']
    counts = [sum(row['status']==s['id'] for row in rows) for s in statuses]
    head = '<div class="matrix-head"><span>项目 / 本周状态</span>'+''.join(f'<span>{e(s["label"])} <b>{counts[i]}</b></span>' for i,s in enumerate(statuses))+'</div>'
    matrix = [head]
    for row in rows:
        cells = f'<span class="dataset-name"><b>{e(row["name"])}</b><small>{e(row["note"])}</small></span>'
        for i, status in enumerate(statuses):
            content = f'<span class="state-result">{icon("check" if i<len(statuses)-1 else "arrow")}<b>{e(row["result"])}</b></span>' if row['status']==status['id'] else '<span class="state-empty" aria-hidden="true">—</span>'
            cells += f'<span class="state-cell state-{i}">{content}</span>'
        matrix.append('<div class="matrix-row">'+cells+'</div>')
    aside = '<div class="three-status">'+''.join(f'<div><b>{counts[i]}</b><span>{e(s["short"])}</span></div>' for i,s in enumerate(statuses))+'</div>'
    if page.get('compression'):
        c = page['compression']
        top = max(c['before'], c['after'], 1)
        before, after = c['before']/top*110, c['after']/top*110
        svg = f'<svg viewBox="0 0 260 150" role="img" aria-label="{e(c["title"])}：{c["before"]} → {c["after"]} {e(c["unit"])}"><rect x="20" y="{125-before}" width="86" height="{before}" rx="4" fill="#d9e5ed"/><rect x="166" y="{125-after}" width="86" height="{after}" rx="2" fill="#4c79b5"/><path d="M123 72h28m-6-6 6 6-6 6" fill="none" stroke="#9bafb9" stroke-width="2"/><text x="63" y="{max(25,125-before/2)}" text-anchor="middle" class="compression-big">{n(c["before"])}</text><text x="209" y="{max(25,110-after)}" text-anchor="middle" class="compression-small">{n(c["after"])}</text><text x="63" y="147" text-anchor="middle" class="axis">{e(c["unit"])}</text><text x="209" y="147" text-anchor="middle" class="axis">{e(c["unit"])}</text></svg>'
        aside += f'<div class="compression"><div class="panel-top"><h2>{e(c["title"])}</h2></div>{svg}<p>{e(c["caption"])} · {change_note(c["before"],c["after"],"体积")}</p></div>'
    if page.get('next_action'):
        aside += f'<button type="button" class="next-action" data-page="{next_index}"><span>下一步</span><b>{e(page["next_action"])}</b>{icon("arrow")}</button>'
    return f'<div class="submission-layout"><div class="status-matrix" style="--statuses:{len(statuses)}">{"".join(matrix)}</div><aside class="submission-side">{aside}</aside></div>'


def result_widget(w):
    kind = w['type']
    ico = {'flow':'verify','tiles':'slides','checks':'clinical','papers':'paper'}[kind]
    top = f'<div class="panel-top"><h2>{icon(ico)}{e(w["title"])}</h2><span>{e(w.get("subtitle",""))}</span></div>'
    if kind == 'flow':
        outputs = ''.join(f'<span><b>{n(x["value"])}</b>{e(x["label"])}</span>' for x in w['outputs'])
        finding = ''
        if w.get('finding'):
            f = w['finding']
            finding = f'<div class="finding"><b>{n(f["value"])}</b><span>{e(f["label"])}</span></div>'
        content = f'<div class="validation-flow"><div class="flow-source"><b>{n(w["source_count"])}</b><span>{e(w["source_label"])}</span><div class="data-stack"><i></i><i></i><i></i></div></div>{icon("arrow")}<div class="flow-output">{outputs}</div></div>'+finding
    elif kind == 'tiles':
        tiles = '<i><span></span><span></span></i>' * min(w['count'], 54)
        secondary = ''.join(f'<span><strong>{n(x["value"])}</strong>{e(x["label"])}</span>' for x in w['secondary'])
        cap = '<small class="cap-note">图示前 54 项</small>' if w['count']>54 else ''
        dots = '<i></i>' * min(w['dot_count'], 30)
        dot_label = e(w['dot_label']) + (f' · 共 {w["dot_count"]} 项' if w['dot_count']>30 else '')
        content = f'<div class="defense-viz"><div><div class="slide-tiles">{tiles}</div>{cap}</div><div class="defense-numbers"><b>{n(w["count"])}<span>{e(w["unit"])}</span></b>{secondary}</div></div><div class="issue-dots">{dots}<span>{dot_label}</span></div>'
    elif kind == 'checks':
        blocks = '<i></i>' * min(w['source_count'], 12)
        content = f'<div class="clinical-viz"><div class="api-blocks">{blocks}</div>{icon("arrow")}<div class="clinical-count"><b>{n(w["verified"])}</b><span>{e(w["verified_label"])} · {n(w["errors"])} {e(w["error_label"])}</span></div></div><div class="clinical-foot"><span>{n(w["source_count"])} {e(w["source_label"])}{"（图示前 12 项）" if w["source_count"]>12 else ""}</span><strong>{e(w["note"])}</strong></div>'
    else:
        papers = ''.join(f'<span class="review-paper {cls}">{icon("paper")}</span>' for cls, count in [('journal',w['left_count']),('thesis',w['right_count'])] for _ in range(min(count,6)))
        cap = '<small class="cap-note">各组最多示意 6 项，数量见下方</small>' if max(w['left_count'],w['right_count'])>6 else ''
        content = f'<div class="paper-viz">{papers}</div>{cap}<div class="paper-labels"><span>{w["left_count"]} {e(w["left_label"])}</span><span>{w["right_count"]} {e(w["right_label"])}</span></div><div class="online"><i></i><b>{e(w["online_title"])}</b><span>{e(w["online_text"])}</span></div>'
    return f'<button type="button" class="viz-panel research-card" data-record="workstream-{e(w["workstream"])}">{top}{content}</button>'


def overview(data, metrics):
    groups = []
    for i, stream in enumerate(data['workstreams']):
        outputs = [x for x in data['outputs'] if x['workstream']==stream['id']]
        if outputs:
            groups.append((stream, outputs, COLORS[i % len(COLORS)]))
    nodes = []
    for i, (stream, outputs, color) in enumerate(groups):
        items = ''.join(f'<span><i></i>{e(x["short"])}</span>' for x in outputs[:4])
        if len(outputs)>4:
            items += f'<span class="more-outputs">另有 {len(outputs)-4} 项，点击查看 ↗</span>'
        nodes.append(f'<button type="button" class="map-node node-{i}" style="--group:{color}" data-record="workstream-{e(stream["id"])}" aria-label="查看{e(stream["name"])}的{len(outputs)}项成果"><span class="map-node-title">{icon(stream["icon"])}<b>{e(stream["name"])}</b><span class="node-count">{len(outputs)}</span></span><span class="node-items">{items}</span></button>')
    graph = ''
    if len(groups)==6:
        graph = '<svg class="map-connections" viewBox="0 0 1100 420" preserveAspectRatio="none" aria-hidden="true"><g fill="none" stroke="#d4e1e5" stroke-width="1.5"><path d="M270 58H320L425 155M270 218H400M270 370H320L425 278M830 58H780L675 155M830 218H700M830 370H780L675 278"/></g></svg>'
    graph += ''.join(nodes)
    graph += '<div class="map-center">'+ring([len(x[1]) for x in groups], [x[2] for x in groups] or COLORS, len(data['outputs']), '项成果')+'<span class="map-key">每个圆点对应 1 项成果</span></div>'
    if not groups:
        graph += '<p class="empty-state">本期暂无已确认成果，工作过程见完整记录。</p>'
    token = n(round(metrics['total_tokens']/1e6)) if metrics['total_tokens']>=1e6 else n(metrics['total_tokens'])
    unit = 'M token' if metrics['total_tokens']>=1e6 else 'token'
    footer = f'<div class="overview-footer"><div class="week-stats"><span><b>{len(data["workstreams"])}</b>条工作线</span><span><b>{metrics["session_count"]}</b>个会话</span><span><b>{metrics["total_turns"]}</b>轮对话</span><span><b>{token}</b>{unit}</span></div><span class="interaction-hint">点击成果分组，查看对应记录 ↗</span></div>'
    return '<div class="achievement-map'+('' if len(groups)==6 else ' adaptive-map')+f'" style="--map-columns:{max(1,min(3,len(groups)))}">'+graph+'</div>'+footer


def activity(metrics):
    shares = metrics['shares']
    peak = max(shares,key=lambda x:x['tokens']) if shares else {'id':'','name':'暂无用量','percent':0}
    allocation = ring([x['tokens'] for x in shares],[x['color'] for x in shares] or COLORS, f'{peak["percent"]:.1f}%', peak['name'], interactive=True)
    legend = ''.join(f'<button type="button" class="share-key{" selected" if x["id"]==peak["id"] else ""}" data-share="{x["percent"]:.6f}" data-label="{e(x["name"])}" aria-pressed="{str(x["id"]==peak["id"]).lower()}"><i style="background:{x["color"]}"></i><span>{e(x["name"])}</span><b>{x["percent"]:.1f}%</b></button>' for x in shares)
    if not shares:
        legend = '<p class="empty-state">本期无会话记录</p>'
    values = metrics['daily_turns']
    high, low = values.index(max(values)), values.index(min(values))
    readout = f'{metrics["labels"][high]} {values[high]} 轮 · {metrics["labels"][low]} {values[low]} 轮'
    million = [x/1e6 for x in metrics['daily_tokens']]
    # Avoid showing small but nonzero activity as an exact zero.
    million = [x if x < 1 else round(x) for x in million]
    return f'''<div class="activity-grid"><article class="viz-panel share-panel"><div class="panel-top"><h2>工作线投入</h2><span>token 占比，非工时</span></div><div class="share-layout"><div class="share-ring">{allocation}</div><div class="share-legend">{legend}</div></div></article><article class="viz-panel daily-panel"><div class="panel-top"><h2>每日活动</h2><div class="chart-switch" role="group" aria-label="每日活动指标"><button type="button" class="selected" data-chart="turns" aria-pressed="true">对话轮次</button><button type="button" data-chart="token" aria-pressed="false">Token / M</button></div></div><div class="daily-chart" id="chart-turns">{bars(values,'turns',metrics)}</div><div class="daily-chart" id="chart-token" hidden>{bars(million,'token',metrics)}</div></article><article class="viz-panel heat-panel"><div class="panel-top"><h2>本期活动时段</h2><p id="heat-readout" aria-live="polite">{readout}</p><span class="heat-legend">少 <i class="h0"></i><i class="h1"></i><i class="h2"></i><i class="h3"></i><i class="h4"></i> 多</span></div><div class="heat-grid" aria-label="{len(values)}天24小时的对话轮次热力图">{heatmap(metrics)}</div></article></div>'''


def priorities(data):
    rows = []
    for p in sorted(data['priorities'],key=lambda x:x['level']):
        items = []
        for i, item in enumerate(p['items']):
            if p['level']=='P0':
                short = e(item['short']).replace('\n','<br>')
                items.append(f'<button type="button" class="task-focus" data-record="plans">{icon("data" if i%2==0 else "verify")}<b>{e(item["title"])}</b><span>{short}</span></button>')
            else:
                items.append(f'<button type="button" data-record="plans"><span>{i+1:02d}</span>{e(item["title"])}</button>')
        if items:
            cls = '' if p['level']=='P0' else ' small-tasks'
            rows.append(f'<div class="priority-row {p["level"].lower()}"><span class="priority-marker">{p["level"]}<small>{e(p["label"])}</small></span><div class="priority-tasks{cls}">{"".join(items)}</div></div>')
    lessons = ''.join(f'<div class="lesson"><span class="lesson-icon">{i+1:02d}</span><b>{e(x["before"])}</b>{icon("arrow")}<span>{e(x["after"])}</span></div>' for i,x in enumerate(data['lessons']))
    decisions = len(data['decisions'])
    empty = '<p class="empty-state">下期计划待确认。</p>' if not rows else ''
    return f'<div class="next-layout"><div class="priority-map">{"".join(rows)}{empty}</div><aside class="reflection-viz"><h2>把本周经验带到下周</h2>{lessons}<button type="button" data-record="reflection">查看复盘依据 ↗</button><div class="decision-summary"><b>{decisions}</b><span>项关键决策<br>背景与推理可追溯</span><button type="button" data-record="decisions" aria-label="查看{decisions}项关键决策">↗</button></div></aside></div>'


def statistics_record(metrics):
    total = n(metrics['total_tokens'])
    note = f'<p>主会话 token 合计 {total}；包括输入、缓存写入、缓存读取和输出，不等于工时。子会话用量不另行叠加。每日柱图按显示单位取舍，精确数值见表。</p>'
    if metrics['carry_turns'] or metrics['carry_tokens']:
        note += f'<p>跨界规则：统计器纳入期初前 6 小时内开始的延续回合。{metrics["carry_turns"]} 轮与 {n(metrics["carry_tokens"])} token 归入首日；热力图保留该回合原开始小时。</p>'
    figures = [f'<figure class="fig"><figcaption>活动时段（对话轮次）</figcaption><div class="heat-grid">{heatmap(metrics,False)}</div></figure>',
               f'<figure class="fig"><figcaption>每日 token / M</figcaption>{bars([x/1e6 for x in metrics["daily_tokens"]],"token",metrics)}</figure>',
               f'<figure class="fig"><figcaption>每日对话轮次</figcaption>{bars(metrics["daily_turns"],"turns",metrics)}</figure>']
    allocation = '<table><thead><tr><th>工作线</th><th>会话</th><th>轮次</th><th>Token</th><th>占比</th></tr></thead><tbody>'+''.join(f'<tr><td>{e(x["name"])}</td><td>{x["sessions"]}</td><td>{x["turns"]}</td><td>{n(x["tokens"])}</td><td>{x["percent"]:.2f}%</td></tr>' for x in metrics['shares'])+'</tbody></table>'
    daily = '<table><thead><tr><th>日期</th><th>轮次</th><th>Token</th></tr></thead><tbody>'+''.join(f'<tr><td>{date}</td><td>{metrics["daily_turns"][i]}</td><td>{n(metrics["daily_tokens"][i])}</td></tr>' for i,date in enumerate(metrics['dates']))+'</tbody></table>'
    start = datetime.fromisoformat(metrics['dates'][0])
    end = datetime.fromisoformat(metrics['dates'][-1])
    span = (end-start).total_seconds()+86400
    timeline = []
    for s in metrics['sessions']:
        first, last = datetime.fromisoformat(s['from']).replace(tzinfo=None), datetime.fromisoformat(s['to']).replace(tzinfo=None)
        left = max(0,min(100,(first-start).total_seconds()/span*100))
        right = max(left,min(100,(last-start).total_seconds()/span*100))
        timeline.append(f'<div class="timeline-row"><span title="{e(s["key"])}">{e(s["name"])}</span><div class="timeline-track"><i style="left:{left}%;width:{max(.2,right-left)}%" title="{e(s["from"])} — {e(s["to"])}"></i></div><small>{s["turns"]} 轮</small></div>')
    figures += ['<figure class="fig"><figcaption>会话时间跨度（非持续工时）</figcaption>'+''.join(timeline)+'</figure>', '<figure class="fig"><figcaption>工作线投入</figcaption>'+allocation+'</figure>']
    return note+''.join(figures)+daily


def make_records(data, metrics, provenance):
    entries = []
    for stream in data['workstreams']:
        entries.append(('workstream-'+stream['id'],stream['name'],f'<h3>{e(stream["title"])}</h3><p class="record-lead">{e(stream["summary"])}</p>'+md(stream['body'])))
    stream_names = {x['id']:x['name'] for x in data['workstreams']}
    outputs = '<div class="record-output-grid">'+''.join(f'<article><small>{e(stream_names[x["workstream"]])}</small><h4>{e(x["label"])}</h4><p>{e(x["description"])}</p><small>依据：{e(x["evidence"])}</small></article>' for x in data['outputs'])+'</div>'
    decisions = ''.join(f'<details class="record-decision"><summary>{i+1}. {e(x["title"])}</summary>{md(x["body"])}</details>' for i,x in enumerate(data['decisions']))
    plans = ''.join(f'<h4>{x["level"]} · {e(x["label"])}</h4>'+''.join(f'<h5>{e(item["title"])}</h5>{md(item["detail"])}' for item in x['items']) for x in data['priorities'])
    source = f'<p>{e(data["headline"])}</p><p>{e(data["sources"].get("note",""))}</p><p>周期：{data["period"]["start"]} — {data["period"]["end"]} · {e(data["period"]["timezone"])}</p><p>数据指纹：<code>{provenance["data_sha256"]}</code><br>统计指纹：<code>{provenance["stats_sha256"]}</code></p>'
    entries += [('outputs',f'{len(data["outputs"])} 项成果',outputs),('decisions',f'{len(data["decisions"])} 项关键决策',decisions),('plans','下周计划原文',plans),('reflection','复盘原文',md(data['reflection'])),('charts','图表与统计口径',statistics_record(metrics)),('sources','来源与说明',source)]
    records = ''.join(f'<section class="record" id="record-{key}" hidden><h3>{e(label)}</h3>{body}</section>' for key,label,body in entries)
    menu = ''.join(f'<button type="button" data-record="{key}">{e(label)}</button>' for key,label,_ in entries)
    return records, menu


def render_report(data, metrics, provenance):
    pages = data['pages']
    results = pages.get('results',{}).get('widgets',[])
    chunks = [results[i:i+4] for i in range(0,len(results),4)]
    page_count = 3 + int('performance' in pages) + int('pipeline' in pages) + len(chunks)
    scenes = [('overview','成果总览','本周成果，一图看清',f'{len(data["outputs"])} 项成果明细','outputs',overview(data,metrics))]
    if pages.get('performance'):
        p = pages['performance']
        scenes.append(('software','性能验证',p['title'],'查看测评与修复记录','workstream-'+p['workstream'],performance(p,len(data['decisions']))))
    if pages.get('pipeline'):
        p = pages['pipeline']
        scenes.append(('submission','项目进度',p['title'],'查看项目记录','workstream-'+p['workstream'],pipeline(p,page_count-1)))
    for i, widgets in enumerate(chunks):
        label = '交付成果'+(f' {i+1}' if len(chunks)>1 else '')
        scenes.append((f'research-{i}',label,pages['results']['title'],'查看完整工作记录','workstream-'+widgets[0]['workstream'],'<div class="research-grid">'+''.join(result_widget(w) for w in widgets)+'</div>'))
    peak = max(metrics['shares'],key=lambda x:x['tokens']) if metrics['shares'] else None
    focus = f'本周投入，集中在{peak["name"]}' if peak and metrics['total_tokens'] else '本周投入与活动节奏'
    scenes.append(('allocation','投入节奏',focus,'图表与统计口径','charts',activity(metrics)))
    priority_count = sum(len(p['items']) for p in data['priorities'] if p['level'] in ('P0','P1'))
    title = f'下周，先收尾这 {priority_count} 件事' if priority_count else '下周重点与复盘'
    scenes.append(('next','下周重点',title,'查看计划与复盘原文','plans',priorities(data)))
    assert len(scenes)==page_count
    nav = ''.join(f'<button type="button" class="chapter-link{" active" if i==0 else ""}" data-page="{i}"><span>{i+1:02d}</span>{e(s[1])}</button>' for i,s in enumerate(scenes))
    dots = ''.join(f'<button type="button" class="page-dot{" active" if i==0 else ""}" data-page="{i}" aria-label="第{i+1}页：{e(s[1])}"></button>' for i,s in enumerate(scenes))
    body = []
    for i,(ident,label,title,note,record,content) in enumerate(scenes):
        head = f'<header class="scene-heading"><div><p class="eyebrow">{i+1:02d} / WEEKLY REPORT</p><h1>{e(title)}</h1></div><button type="button" class="detail-link" data-record="{record}">{e(note)} <span aria-hidden="true">↗</span></button></header>'
        body.append(f'<section class="scene{" current" if i==0 else ""}" id="{ident}" data-title="{e(label)}">{head}{content}</section>')
    start, end = data['period']['start'], data['period']['end']
    date_label = start.replace('-','.')+' — '+(end[5:].replace('-','.') if start[:4]==end[:4] else end.replace('-','.'))
    title = f'工作周报 · {start} — {end}'
    css = (ROOT/'report_theme.css').read_text(encoding='utf-8').replace('__REPORT_PERIOD__',date_label)
    js = (ROOT/'report_interactions.js').read_text(encoding='utf-8')
    records, menu = make_records(data,metrics,provenance)
    html = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light"><meta name="description" content="{page_count}页图解回顾本周成果、进度、投入与下周重点。"><title>{e(title)} · 图解版</title><style>{css}</style></head><body>
<a class="skip-link" href="#report">跳到图解正文</a>
<header class="app-header"><a class="brand" href="#overview"><span class="brand-mark">W.</span><span>工作周报<small>{date_label}</small></span></a><nav class="chapters" aria-label="图解章节">{nav}</nav><div class="header-actions"><button type="button" id="view-toggle" aria-pressed="false">连续浏览</button><button type="button" class="records-button" data-record="outputs">{icon('book')}<span>完整记录</span></button><button type="button" id="print-report" aria-label="打印{page_count}页图解" title="打印{page_count}页图解">{icon('print')}</button></div></header>
<main id="report" tabindex="-1">{''.join(body)}</main>
<footer class="page-controls"><button type="button" id="previous-page" disabled>← 上一页</button><div class="pager-middle"><span id="page-count">01 / {page_count:02d}</span><div class="page-dots">{dots}</div><span class="keyboard-tip">← → 翻页</span></div><button type="button" id="next-page">下一页 →</button></footer>
<div class="sr-only" id="page-status" role="status" aria-live="polite"></div>
<dialog id="record-dialog" aria-labelledby="record-title"><header class="dialog-header"><div><small>按需展开 · 原文保留</small><h2 id="record-title">完整记录</h2></div><button type="button" id="close-records" aria-label="关闭记录">×</button></header><div class="dialog-layout"><nav class="record-menu" aria-label="原始记录分类">{menu}</nav><div class="record-content" tabindex="0">{records}</div></div></dialog>
<noscript><style>.scene{{display:block!important}}.header-actions,.page-controls,.detail-link,.interaction-hint{{display:none}}</style><p class="noscript-note">已显示全部图解。查看详细记录需启用 JavaScript。</p></noscript>
<script>{js}</script></body></html>'''
    return html, page_count


