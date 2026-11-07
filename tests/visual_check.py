"""Local browser QA; screenshots and print preview. Does not collect new work data."""
import argparse
import json
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright


def run(html,out,chrome):
    out.mkdir(parents=True,exist_ok=True)
    results,errors=[],[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=chrome,headless=True)
        page=browser.new_page(viewport={'width':1366,'height':768},device_scale_factor=1)
        page.on('pageerror',lambda error:errors.append(str(error)))
        network=[]
        page.on('request',lambda req:network.append(req.url) if req.url.startswith(('http:','https:')) else None)
        page.goto(html.as_uri())
        count=page.locator('.scene').count()
        for width,height in [(1366,768),(390,844),(320,700)]:
            page.set_viewport_size({'width':width,'height':height})
            for i in range(count):
                page.locator('.chapter-link').nth(i).click()
                page.screenshot(path=str(out/f'{width}-page-{i+1}.png'),full_page=True)
                measurement=page.locator('.scene.current').evaluate('(el)=>({width:document.documentElement.scrollWidth,viewport:innerWidth,height:el.clientHeight})')
                assert measurement['width']<=width+1,(width,i,measurement)
                results.append({'width':width,'page':i+1,**measurement})
        page.set_viewport_size({'width':1366,'height':768})
        page.locator('.records-button').click()
        assert page.locator('#record-dialog').evaluate('(el)=>el.open')
        for button in page.locator('.record-menu button').all():
            button.click()
            assert page.locator('.record:not([hidden])').count()==1
        page.keyboard.press('Escape')
        assert not page.locator('#record-dialog').evaluate('(el)=>el.open')
        page.locator('.chapter-link').filter(has_text='投入节奏').click()
        page.locator('[data-chart="token"]').click()
        assert page.locator('#chart-token').is_visible()
        page.locator('[data-chart="turns"]').click()
        assert page.locator('#chart-turns').is_visible()
        if page.locator('.share-key').count():
            share=page.locator('.share-key').last
            share.click()
            assert page.locator('#share-label').text_content()==share.get_attribute('data-label')
        page.locator('.heat-cell').first.focus()
        page.keyboard.press('ArrowDown')
        assert page.locator('.heat-cell').nth(24).evaluate('(el)=>el===document.activeElement') if page.locator('.heat-cell').count()>24 else True
        page.locator('#view-toggle').click()
        assert page.locator('.scene:visible').count()==count
        page.locator('#view-toggle').click()
        page.locator('.chapter-link').first.click()
        page.keyboard.press('ArrowRight')
        assert page.locator('#page-count').inner_text().startswith('02')
        page.locator('.chapter-link').last.click()
        assert page.locator('#next-page').is_disabled()
        page.reload()
        page.pdf(path=str(out/'print.pdf'),prefer_css_page_size=True,print_background=True)
        browser.close()
    assert not errors,errors
    assert not network,network
    summary={'html':str(html),'scene_count':count,'browser_errors':errors,'external_requests':network,'viewports':[1366,390,320],'checks':results}
    (out/'result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ('scene_count','browser_errors','external_requests','viewports')},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--html',required=True)
    parser.add_argument('--out',required=True)
    parser.add_argument('--chrome',default=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
    args=parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    run(Path(args.html).resolve(),Path(args.out).resolve(),args.chrome)
