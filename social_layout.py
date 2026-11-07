"""Portrait, illustration-led weekly story cards. All artwork is editable inline SVG."""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def e(value):
    return escape(str(value), quote=True)


def icon(name, cls='icon'):
    shapes = {
        'code':'<rect x="4" y="5" width="32" height="25" rx="5"/><path d="M1 35h38M15 13l-5 5 5 5m10-10 5 5-5 5m-3-12-4 20"/>',
        'check':'<path d="M20 3 6 9v10c0 10 14 18 14 18s14-8 14-18V9Z"/><path d="m12 19 6 6 11-12"/>',
        'chart':'<rect x="5" y="3" width="30" height="34" rx="5"/><path d="M11 28h18M13 24v-5m7 5V13m7 11V9"/>',
        'data':'<ellipse cx="20" cy="9" rx="14" ry="5"/><path d="M6 9v22c0 7 28 7 28 0V9M6 20c0 7 28 7 28 0"/>',
        'test':'<rect x="3" y="4" width="34" height="30" rx="5"/><path d="M3 12h34M9 8h1m5 0h1M10 23l5 5L29 17"/>',
        'upload':'<path d="M3 15V9h14l5 5h15v21H3ZM20 29V17m-6 6 6-6 6 6"/>',
        'verify':'<path d="M7 3h17l8 8v22H7ZM23 3v9h9M12 17h9m-9 6h5"/><circle cx="27" cy="27" r="8"/><path d="m33 33 5 5m-14-11 2 2 4-4"/>',
        'arrow':'<path d="M5 20h29m-9-9 11 9-11 9"/>',
        'spark':'<path d="m20 3 4 12 13 5-13 4-4 13-5-13L3 20l12-5Z"/>',
    }
    return f'<svg class="{cls}" viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{shapes[name]}</svg>'


def hero_art():
    return '''<svg viewBox="0 0 1080 650" class="hero-art" aria-hidden="true">
<defs><pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.7" fill="#c6d3c6"/></pattern><linearGradient id="screen" x2="1" y2="1"><stop stop-color="#edf4e8"/><stop offset="1" stop-color="#d1e5da"/></linearGradient></defs>
<ellipse cx="550" cy="578" rx="400" ry="34" fill="#d9e0d3" opacity=".52"/>
<circle cx="555" cy="310" r="260" fill="#e8ecdf"/><circle cx="555" cy="310" r="226" fill="none" stroke="#c2d4c6" stroke-dasharray="5 13" stroke-width="2"/>
<rect x="47" y="70" width="175" height="145" fill="url(#dots)"/><rect x="868" y="385" width="154" height="162" fill="url(#dots)"/>
<path d="M195 191C270 80 434 84 499 150M822 227q130 74 68 193" fill="none" stroke="#b9c7b6" stroke-width="3" stroke-dasharray="9 10"/>
<g transform="translate(287 176) rotate(-5 255 155)"><rect x="0" y="0" width="527" height="333" rx="23" fill="#1e4441"/><rect x="14" y="15" width="499" height="300" rx="13" fill="url(#screen)"/><path d="M14 60h499" stroke="#c3d3c4" stroke-width="2"/><circle cx="40" cy="38" r="6" fill="#eab184"/><circle cx="62" cy="38" r="6" fill="#a4beb1"/><circle cx="84" cy="38" r="6" fill="#54867a"/>
<rect x="36" y="83" width="170" height="204" rx="12" fill="#fbfaf4"/><path d="m96 121-24 24 24 24m44-48 24 24-24 24m-10-60-20 86" fill="none" stroke="#2b8173" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/><path d="M60 223h120M60 244h76M60 264h101" stroke="#d4ddcf" stroke-width="8" stroke-linecap="round"/>
<rect x="224" y="83" width="263" height="204" rx="12" fill="#fbfaf4"/><path d="M254 124h91M254 141h148" stroke="#cad9cb" stroke-width="7" stroke-linecap="round"/><rect x="255" y="215" width="36" height="42" rx="5" fill="#b4d0c1"/><rect x="311" y="184" width="36" height="73" rx="5" fill="#83b7a3"/><rect x="367" y="163" width="36" height="94" rx="5" fill="#2c8978"/><path d="m423 219 15 15 28-35" fill="none" stroke="#cf8657" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M-29 333h585l43 48q5 15-18 15H-47q-23 0-19-15Z" fill="#b3c5b7" stroke="#74998b" stroke-width="2"/><path d="M182 334h174l17 25H168Z" fill="#dce5d8"/></g>
<g transform="translate(102 240) rotate(-11)"><rect x="8" y="8" width="182" height="218" rx="17" fill="#d7dfd0"/><rect width="182" height="218" rx="17" fill="#fffdf6" stroke="#c7d5c5" stroke-width="2"/><path d="M27 43h100M27 64h65" stroke="#b8cec0" stroke-width="7" stroke-linecap="round"/><path d="M31 112h120M31 140h120M31 168h120" stroke="#e5eadd" stroke-width="3"/><path d="m33 155 29-36 29 12 30-43 26 12" fill="none" stroke="#318373" stroke-width="6" stroke-linecap="round"/><circle cx="121" cy="88" r="8" fill="#dfa06e"/></g>
<g transform="translate(791 80) rotate(11)"><rect x="0" y="0" width="177" height="172" rx="25" fill="#fffdf6" stroke="#c8d6c6" stroke-width="2"/><ellipse cx="89" cy="52" rx="44" ry="15" fill="#d9e6d5" stroke="#588f7e" stroke-width="3"/><path d="M45 53v67c0 20 88 20 88 0V53M45 85c0 20 88 20 88 0" fill="none" stroke="#588f7e" stroke-width="3"/></g>
<g transform="translate(799 435) rotate(8)"><rect width="183" height="116" rx="24" fill="#1e655c"/><circle cx="57" cy="59" r="29" fill="#d6e7c5"/><path d="m43 58 10 11 20-23" fill="none" stroke="#266b5d" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/><path d="M104 43h44m-44 18h35m-35 18h23" stroke="#d8e7d1" stroke-width="7" stroke-linecap="round"/></g>
<path d="m244 72 6 18 18 6-18 7-6 18-7-18-18-7 18-6Zm702 237 5 13 13 5-13 5-5 13-5-13-13-5 13-5Z" fill="#d49a68"/>
</svg>'''


def release_art(value):
    return f'''<svg viewBox="0 0 480 245" class="release-art" aria-hidden="true"><ellipse cx="245" cy="219" rx="190" ry="15" fill="#d6dfcf"/><rect x="26" y="18" width="266" height="165" rx="15" fill="#244b43"/><rect x="37" y="30" width="244" height="140" rx="8" fill="#e3eddb"/><path d="M53 50h212" stroke="#c6d4bf" stroke-width="2"/><circle cx="58" cy="41" r="3" fill="#e2a071"/><path d="m92 80-21 22 21 22m54-44 21 22-21 22m-20-51-15 64" fill="none" stroke="#458f78" stroke-width="5" stroke-linecap="round"/><path d="M193 85h62m-62 20h46m-46 20h54" stroke="#9fbea8" stroke-width="7" stroke-linecap="round"/><path d="M15 184h291l17 27H0Z" fill="#adbfaa"/>
<path d="m313 82 73-32 72 32v112l-71 33-74-33Z" fill="#e4a06f" stroke="#a66f4d" stroke-width="2"/><path d="m313 82 74 32 71-32M387 114v113" fill="none" stroke="#a66f4d" stroke-width="2"/><path d="m348 67 74 32v34l-20 9v-34l-74-32Z" fill="#f4d4a1"/><text x="350" y="174" text-anchor="middle" font-family="Arial,sans-serif" font-size="25" font-weight="700" fill="#714e37">{e(value)}</text></svg>'''


def gallery_art(count, secondary_count):
    sheets = []
    # These pages are illustrations, not a one-icon-per-file count chart.
    for i,rotation in enumerate((-12,-5,5)):
        x=50+i*97
        sheets.append(f'<g transform="translate({x} {30+i%2*15}) rotate({rotation} 70 80)"><rect x="5" y="8" width="142" height="180" rx="10" fill="#cfd8c8"/><rect width="142" height="180" rx="10" fill="#fffdf7" stroke="#bdcbb6" stroke-width="2"/><path d="M20 25h83M20 40h56" stroke="#c5d5ba" stroke-width="5" stroke-linecap="round"/>')
        if i==0:
            sheets.append('<path d="M24 130V70m0 60h96" stroke="#c6d4bf" stroke-width="2"/><path d="m28 120 21-25 21 9 20-34 25 12" fill="none" stroke="#52977b" stroke-width="5"/>')
        elif i==1:
            sheets.append('<circle cx="72" cy="98" r="35" fill="none" stroke="#e3eadb" stroke-width="15"/><circle cx="72" cy="98" r="35" fill="none" stroke="#82aa6f" stroke-width="15" stroke-dasharray="150 220" transform="rotate(-90 72 98)"/>')
        else:
            sheets.append('<rect x="25" y="104" width="20" height="27" rx="3" fill="#bbcfac"/><rect x="60" y="83" width="20" height="48" rx="3" fill="#96b585"/><rect x="95" y="65" width="20" height="66" rx="3" fill="#638d58"/>')
        sheets.append('<path d="M22 151h98m-98 13h64" stroke="#e0e6d6" stroke-width="4"/></g>')
    return '<svg viewBox="0 0 480 250" class="gallery-art" aria-hidden="true">'+''.join(sheets)+'</svg>'


def comparison(card):
    top = max(card['before'],card['after'],1)
    rows = []
    for key,label in [('before',card['before_label']),('after',card['after_label'])]:
        width=card[key]/top*100
        rows.append(f'<div class="comparison-row {key}"><span>{e(label)}</span><div class="bar-track"><i style="width:{width}%"></i></div><b>{card[key]:,}<small>{e(card["unit"])}</small></b></div>')
    return '<div class="comparison">'+''.join(rows)+'</div>'


def detail_card(card,index):
    t=card['type']
    if t=='milestone':
        if card['icon']=='code':
            art=release_art('✓')
        elif card['icon'] in ('chart','data'):
            art=gallery_art(0,0)
        else:
            art='<div class="status-illustration"><span>'+icon(card['icon'])+'</span><i>'+icon('check')+'</i></div>'
        body=f'<div class="detail-visual">{art}</div><div class="detail-copy"><div class="milestone-label">{e(card["status"])}</div><p>{e(card["note"])}</p></div>'
    elif t=='release':
        body=f'<div class="detail-visual">{release_art(card["value"])}</div><div class="detail-copy"><div class="release-label">{e(card["value"])}</div><p>{e(card["note"])}</p></div>'
    elif t=='comparison':
        delta=card['after']-card['before']
        body=comparison(card)+f'<div class="compare-bottom"><span><b>{"+" if delta>=0 else ""}{delta:,}</b> {e(card["delta_label"])}</span><p>{e(card["note"])}</p></div>'
    else:
        body=f'<div class="detail-visual">{gallery_art(card["count"],card["secondary_count"])}</div><div class="detail-copy gallery-copy"><b>{card["count"]}<small>{e(card["unit"])}</small></b><span><strong>{card["secondary_count"]}</strong> {e(card["secondary_unit"])}</span></div>'
    symbol=card['icon'] if t=='milestone' else {"release":"code","comparison":"check","gallery":"chart"}[t]
    return f'<article class="detail-card detail-{t}" data-fit><header><span class="card-index">0{index+1}</span><h2>{e(card["title"])}</h2>{icon(symbol)}</header><div class="detail-body">{body}</div></article>'


def render_social(data, count=3):
    start,end=data['period']['start'],data['period']['end']
    period=start.replace('-','.')+' — '+(end[5:].replace('-','.') if start[:4]==end[:4] else end.replace('-','.'))
    def top(label):
        return f'<header class="topline"><span class="series"><i></i>{e(data["series"])}</span><span class="date">{period}</span></header><div class="page-kicker">{e(label)}</div>'
    def title(lines):
        return '<h1 data-fit>'+''.join(f'<span>{e(x)}</span>' for x in lines)+'</h1>'
    def foot(index):
        return f'<footer class="bottomline"><span>{e(data["identity"])}</span><span class="page-no">{index:02d} <i>/</i> {count:02d}</span></footer>'
    cover=data['cover']
    badges=''.join(f'<div class="highlight" data-fit>{icon(x["icon"])}<span class="highlight-label">{e(x["label"])}</span><b>{e(x["value"])}<small>{e(x["unit"])}</small></b>'+'<span class="highlight-note">'+e(x['note'])+'</span></div>' for x in cover['highlights'])
    first=f'<section class="sheet cover" data-slide="01" aria-label="封面">{top("WEEKLY FIELD NOTES")}{title(cover["title"])}<p class="cover-subtitle">{e(cover["subtitle"])}</p><div class="hero-wrap">{hero_art()}</div><div class="highlights" style="--items:{len(cover["highlights"])}">{badges}</div><p class="cover-takeaway">{icon("spark")}<span>{e(cover["takeaway"])}</span></p>{foot(1)}</section>'
    detail=data['achievements']
    second=f'<section class="sheet achievements" data-slide="02" aria-label="成果">{top("PROGRESS / 本周进展")}{title(detail["title"])}<p class="section-subtitle">{e(detail["subtitle"])}</p><div class="detail-grid" style="--items:{len(detail["cards"])}">'+''.join(detail_card(card,i) for i,card in enumerate(detail['cards']))+f'</div>{foot(2)}</section>'
    pages=[first,second]
    if count==3:
        review=data['review']
        lessons=''.join(f'<article class="lesson-card" data-fit><div class="lesson-symbol">{icon(x["icon"])}<span>0{i+1}</span></div><div class="lesson-copy"><h2>{e(x["title"])}</h2><p>{e(x["text"])}</p></div></article>' for i,x in enumerate(review['lessons']))
        last=f'<section class="sheet review" data-slide="03" aria-label="复盘">{top("NOTES / 本周复盘")}{title(review["title"])}<p class="section-subtitle">{e(review["subtitle"])}</p><div class="lesson-stack">{lessons}</div><div class="takeaway-band">{icon("spark")}<p>{e(review["takeaway"])}</p><span>{e(review["closing"])}</span></div>{foot(3)}</section>'
        pages.append(last)
    css=(ROOT/'social_theme.css').read_text(encoding='utf-8')
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>周报分享图 · '+period+'</title><style>'+css+'</style></head><body>'+''.join(pages)+'</body></html>'
