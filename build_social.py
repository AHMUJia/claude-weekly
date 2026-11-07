"""Generate 2–3 curated 3:4 PNG cards from a weekly report, without publishing."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

from jsonschema import Draft202012Validator, FormatChecker
from build_report import atomic_write, dump_json
from report_model import ReportError, read_json, file_hash, validate_data
from social_layout import render_social, e

ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1200, 1600
IMAGE_NAMES = ['01_封面.png','02_成果.png','03_复盘.png']


def public_copy(data):
    """Only human-visible copy; dates, citations and provenance stay outside this scan."""
    fields=[data['series'],data['identity']]
    for name in ('cover','achievements','review','caption'):
        def walk(value):
            if isinstance(value,str):fields.append(value)
            elif isinstance(value,list):
                for item in value:walk(item)
            elif isinstance(value,dict):
                for key,item in value.items():
                    if key not in ('references','icon','type'):walk(item)
        walk(data[name])
    return '\n'.join(fields)


def check_shareable_details(data):
    """Allow useful, curated facts; flag direct internal identifiers, not all numbers."""
    if data.get('disclosure')!='balanced':
        raise ReportError('分享稿请按 balanced 口径整理：保留有依据的成果与数字，省去敏感细节')
    text=public_copy(data)
    patterns=[r'[A-Za-z]:[\\/]',r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',
              r'住院号|病历号|身份证|登录口令|访问令牌',
              r'https?://(?:localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)(?=[:/\s]|$)',
              r'https?://[^\s/]+\.(?:internal|local)(?=[:/\s]|$)',
              r'(?:api[_-]?key|access[_-]?token|password)\s*[:=]\s*\S+']
    if any(re.search(pattern,text,re.I) for pattern in patterns):
        raise ReportError('分享文案含本地路径、联系方式、内网地址或内部标识，请移到内部记录')


def load_social(path):
    path=Path(path).resolve()
    data=read_json(path)
    if data.get('status')!='ready':
        raise ReportError('分享内容仍是草稿；核对公开文案与来源后再设为 ready')
    schema=read_json(ROOT/'social.schema.json')
    errors=list(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(data))
    if errors:
        raise ReportError('\n'.join(f'{".".join(map(str,x.path))}：{x.message}' for x in errors[:8]))
    report_path=(path.parent/data['source_report']).resolve()
    report=read_json(report_path)
    validate_data(report)
    if data['source_report_sha256']!=file_hash(report_path):
        raise ReportError('源周报已更新。请重新核对分享文案和指标，再更新来源指纹；不能沿用旧图')
    if any(data['period'][key]!=report['period'][key] for key in ('start','end')):
        raise ReportError('分享图日期与源周报不一致')
    allowed={'output:'+x['id'] for x in report['outputs']} | {'workstream:'+x['id'] for x in report['workstreams']}
    allowed |= {'decision:'+str(i+1) for i in range(len(report['decisions']))}
    allowed |= {'lesson:'+str(i+1) for i in range(len(report['lessons']))}
    items=data['cover']['highlights']+data['achievements']['cards']+data['review']['lessons']
    for item in items:
        missing=set(item['references'])-allowed
        if missing:
            raise ReportError('分享内容引用不存在的本期依据：'+', '.join(sorted(missing)))
    check_shareable_details(data)
    return data,{'data_sha256':file_hash(path),'report_sha256':file_hash(report_path)}


def prepare_social(report_path):
    report_path=Path(report_path).resolve()
    report=read_json(report_path)
    validate_data(report)
    path=report_path.with_name('social.json')
    digest=file_hash(report_path)
    if path.exists():
        data=read_json(path)
        if data.get('source_report_sha256')==digest and data.get('disclosure')=='balanced':
            return {'data':str(path),'status':data.get('status'),'message':'沿用现有分享内容，未覆盖'}
        period={k:report['period'][k] for k in ('start','end')}
        if data.get('period')!=period:
            raise ReportError('现有分享稿属于另一周期，不能覆盖')
        backup=path.parent/'history'/('social-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
        atomic_write(backup,dump_json(data))
        data.update(status='draft',disclosure='balanced',source_report=report_path.name,source_report_sha256=digest)
    else:
        data={'schema_version':1,'status':'draft','disclosure':'balanced','source_report':report_path.name,'source_report_sha256':digest,
              'period':{k:report['period'][k] for k in ('start','end')},'series':'工作周记','identity':'',
              'cover':{'title':[],'subtitle':'','takeaway':'','highlights':[]},
              'achievements':{'title':[],'subtitle':'','cards':[]},
              'review':{'title':[],'subtitle':'','lessons':[],'takeaway':'','closing':''},
              'caption':{'title':'','body':'','hashtags':[]}}
    atomic_write(path,dump_json(data))
    return {'data':str(path),'status':'draft','message':'按本期事实精选具体成果、适当数字和经验，省去客户、病历、未公开研究细节等敏感信息'}


def find_browser(requested=None):
    if requested:
        path=Path(requested)
        if not path.is_file():raise ReportError('指定的浏览器程序不存在：'+str(path))
        return str(path)
    candidates=[r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
    candidates += [shutil.which(x) for x in ('google-chrome','chromium','chromium-browser')]
    return next((x for x in candidates if x and Path(x).is_file()),None)


def caption_markdown(data):
    caption=data['caption']
    return '# '+caption['title']+'\n\n'+caption['body']+'\n\n'+' '.join('#'+x.lstrip('#') for x in caption['hashtags'])+'\n'


def preview_html(data,names):
    title=e(data['series'])+' · '+data['period']['start']+' — '+data['period']['end']
    images=''.join(f'<figure><img src="{name}" width="1200" height="1600" alt="{e(name[3:-4])}"><figcaption>{e(name)}</figcaption></figure>' for name in names)
    return f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>body{{margin:0;background:#eeeee9;color:#29493d;font:16px/1.6 "Microsoft YaHei",sans-serif;padding:32px}}h1{{font-size:24px}}main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:24px;max-width:1500px}}figure{{margin:0}}img{{width:100%;height:auto;border-radius:12px;box-shadow:0 8px 30px #273b3012}}figcaption{{color:#718075;font-size:13px;margin:10px 0}}a{{color:#267764}}</style><h1>{title}</h1><p>{len(names)} 张竖版分享图 · 1200 × 1600 · 宽高比 3:4 · <a href="分享文案.md">配套文案</a></p><main>{images}</main></html>'


def build_social(data_path,output_dir=None,pages=3,browser=None,validate_only=False):
    if pages not in (2,3):raise ReportError('分享图仅支持 2 或 3 张')
    data,provenance=load_social(data_path)
    slug=data['period']['start'].replace('-','')+'-'+data['period']['end'].replace('-','')
    if validate_only:return {'valid':True,'pages':pages,'width':WIDTH,'height':HEIGHT}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ReportError('导出图片需要 Playwright：python -m pip install -r requirements-dev.txt') from exc
    output_dir=Path(output_dir).resolve() if output_dir else ROOT/'分享图'/slug
    output_dir.parent.mkdir(parents=True,exist_ok=True)
    names=IMAGE_NAMES[:pages]
    html=render_social(data,pages)
    # Render all pages and check their layout before replacing any delivered files.
    with tempfile.TemporaryDirectory(prefix='.social-',dir=output_dir.parent) as temp:
        stage=Path(temp).resolve()
        assert output_dir.parent in stage.parents
        source=stage/'社交图布局.html'
        source.write_text(html,encoding='utf-8')
        with sync_playwright() as pw:
            chromium=pw.chromium.launch(executable_path=find_browser(browser),headless=True)
            page=chromium.new_page(viewport={'width':1280,'height':1680},device_scale_factor=1)
            errors,requests=[],[]
            page.on('pageerror',lambda err:errors.append(str(err)))
            page.on('request',lambda req:requests.append(req.url) if req.url.startswith(('http:','https:')) else None)
            page.goto(source.as_uri())
            page.evaluate('document.fonts.ready')
            for i,name in enumerate(names):
                sheet=page.locator('.sheet').nth(i)
                failures=sheet.evaluate('''el=>{
                  const failures=[];
                  for(const node of el.querySelectorAll('[data-fit]')){
                    if(node.scrollWidth>node.clientWidth+2||node.scrollHeight>node.clientHeight+2) failures.push(node.innerText.slice(0,50));
                  }
                  const limit=el.querySelector('.bottomline').getBoundingClientRect().top;
                  for(const node of el.children){if(!node.classList.contains('bottomline')&&node.getBoundingClientRect().bottom>limit-12) failures.push('正文与页脚过近：'+node.className);}
                  return failures;
                }''')
                if failures:raise ReportError(f'第 {i+1} 张内容过长，请缩短文案：'+str(failures))
                box=sheet.bounding_box()
                if round(box['width'])!=WIDTH or round(box['height'])!=HEIGHT:
                    raise ReportError('分享图画布尺寸异常')
                sheet.screenshot(path=str(stage/name))
            chromium.close()
            if errors or requests:raise ReportError('页面检查未通过：'+str(errors+requests))
        (stage/'分享文案.md').write_text(caption_markdown(data),encoding='utf-8')
        (stage/'分享图预览.html').write_text(preview_html(data,names),encoding='utf-8')
        manifest={'schema_version':1,'generated_at':datetime.now(timezone.utc).isoformat(),
                  'period':data['period'],'disclosure':data['disclosure'],'pages':pages,'width':WIDTH,'height':HEIGHT,'aspect_ratio':'3:4',
                  **provenance,'images':{name:file_hash(stage/name) for name in names},
                  'engine_sha256':{name:file_hash(ROOT/name) for name in ('build_social.py','social_layout.py','social_theme.css','social.schema.json')}}
        (stage/'manifest.json').write_text(dump_json(manifest),encoding='utf-8')
        archive_name=f'小红书分享图_{slug}.zip'
        with zipfile.ZipFile(stage/archive_name,'w',zipfile.ZIP_DEFLATED) as archive:
            for name in names+['分享文案.md','分享图预览.html']:
                archive.write(stage/name,name)
        output_dir.mkdir(parents=True,exist_ok=True)
        for path in stage.iterdir():os.replace(path,output_dir/path.name)
        if pages==2:(output_dir/IMAGE_NAMES[2]).unlink(missing_ok=True)
    return {'output_dir':str(output_dir),'images':[str(output_dir/name) for name in names],
            'preview':str(output_dir/'分享图预览.html'),'archive':str(output_dir/archive_name),
            'width':WIDTH,'height':HEIGHT,'pages':pages}


def main():
    parser=argparse.ArgumentParser(description='导出 2–3 张小红书竖版分享图（宽 3、高 4）')
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--data',help='本期 social.json')
    source.add_argument('--prepare',help='从本期 report.json 准备空白分享草稿')
    parser.add_argument('--pages',type=int,choices=(2,3),default=3)
    parser.add_argument('--output-dir')
    parser.add_argument('--browser',help='Chrome/Edge 可执行文件；未指定时自动查找')
    parser.add_argument('--validate-only',action='store_true')
    args=parser.parse_args()
    try:
        result=prepare_social(args.prepare) if args.prepare else build_social(args.data,args.output_dir,args.pages,args.browser,args.validate_only)
        print(dump_json(result))
    except (ReportError,OSError,ValueError,KeyError,TypeError) as exc:
        print('分享图未生成：'+str(exc),file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
