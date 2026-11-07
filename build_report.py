"""Build a standalone graphic report from validated period data. No collection or AI calls."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile

from report_model import load_report, ReportError, file_hash
from report_layout import render_report

ROOT = Path(__file__).resolve().parent


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, suffix='.tmp', delete=False) as f:
        tmp = Path(f.name)
        f.write(text)
    try:
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def dump_json(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n'


def markdown_record(data, metrics):
    p = data['period']
    lines = [f'# 工作周报 {p["start"]} — {p["end"]}', '', data['headline'], '',
             f'{metrics["session_count"]} 个会话 · {metrics["total_turns"]} 轮 · {metrics["total_tokens"]:,} token（非工时）', '', '## 成果', '']
    lines += [f'- **{x["label"]}**：{x["description"]}\n  - 依据：{x["evidence"]}' for x in data['outputs']]
    for s in data['workstreams']:
        lines += ['', '## '+s['title'], '', s['summary'], '', s['body']]
    lines += ['', '## 关键决策']
    for x in data['decisions']:
        lines += ['', '### '+x['title'], '', x['body']]
    lines += ['', '## 下周计划']
    for p in data['priorities']:
        lines += ['', f'### {p["level"]} · {p["label"]}', '']
        lines += [f'#### {item["title"]}\n\n{item["detail"]}\n' for item in p['items']]
    lines += ['', '## 反思', '', data['reflection']]
    return '\n'.join(lines)+'\n'


def build(data_path, output=None, validate_only=False):
    data, metrics, provenance = load_report(data_path)
    slug = data['period']['start'].replace('-','')+'-'+data['period']['end'].replace('-','')
    if validate_only:
        return {'valid':True,'period':slug,'sessions':metrics['session_count'],'turns':metrics['total_turns'],'token':metrics['total_tokens']}
    html, pages = render_report(data,metrics,provenance)
    output = Path(output).resolve() if output else ROOT/f'周报_{slug}.html'
    if output.suffix.lower() != '.html':
        raise ReportError('输出文件必须使用 .html 扩展名')
    # All validation and rendering precede writes. Previous deliverables survive errors.
    atomic_write(output,html)
    atomic_write(output.with_suffix('.md'),markdown_record(data,metrics))
    manifest = {'schema_version':1,'generated_at':datetime.now(timezone.utc).isoformat(),
                'period':data['period'],'pages':pages,'output':str(output),**provenance,
                'html_sha256':file_hash(output),'sources':data['sources'],
                'statistics':{k:metrics[k] for k in ('session_count','total_turns','total_tokens','output_tokens','daily_tokens','daily_turns','carry_tokens','carry_turns')},
                'engine_sha256':{name:file_hash(ROOT/name) for name in ('build_report.py','report_layout.py','report_model.py','report.schema.json','report_theme.css','report_interactions.js')}}
    atomic_write(output.with_suffix('.manifest.json'),dump_json(manifest))
    return {'output':str(output),'pages':pages,'sessions':metrics['session_count'],'turns':metrics['total_turns']}


def main():
    parser = argparse.ArgumentParser(description='从每期 report.json 生成固定风格的图解周报')
    parser.add_argument('--data',required=True,help='本期 report.json 路径')
    parser.add_argument('--output',help='输出 HTML 路径；默认保存到方案目录')
    parser.add_argument('--validate-only',action='store_true',help='只校验，不写任何输出文件')
    parser.add_argument('--social',action='store_true',help='同时导出同目录 social.json 的竖版分享图')
    parser.add_argument('--social-pages',type=int,choices=(2,3),default=3,help='分享图张数，默认 3 张')
    parser.add_argument('--social-output-dir',help='分享图目录；默认 分享图/<周期>')
    args = parser.parse_args()
    try:
        if args.social:
            from build_social import load_social, build_social
            social_path=Path(args.data).resolve().with_name('social.json')
            social_data,_=load_social(social_path)
            if (social_path.parent/social_data['source_report']).resolve()!=Path(args.data).resolve():
                raise ReportError('social.json 引用的源周报不是本次生成的 report.json')
        result=build(args.data,args.output,args.validate_only)
        if args.social:
            result['social']=build_social(social_path,args.social_output_dir,args.social_pages,validate_only=args.validate_only)
        print(dump_json(result))
    except (ReportError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f'生成未完成：{exc}',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
