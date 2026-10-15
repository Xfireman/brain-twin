"""Exercise the installed app with temporary synthetic data. No real model calls."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect


def main():
    with tempfile.TemporaryDirectory(prefix='brain-twin-ui-') as directory:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port=sock.getsockname()[1]
        env={**os.environ,'BRAIN_TWIN_DATA_DIR':directory,'BRAIN_MODEL_URL':'','BRAIN_MODEL_NAME':'','BRAIN_MODEL_KEY':''}
        server=subprocess.Popen([sys.executable,'-m','brain_twin.app','--port',str(port)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        url=f'http://127.0.0.1:{port}'
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen(url+'/health',timeout=.5).close()
                    break
                except OSError:time.sleep(.1)
            else:raise RuntimeError('App did not start')
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True)
                page=browser.new_page(viewport={'width':1280,'height':900})
                page.add_init_script("localStorage.setItem('twin-lang','en')")
                errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(url)
                expect(page.locator('#profile-heading')).to_contain_text('Field Notes')
                page.locator('#example-question').click();page.locator('#ask-submit').click()
                expect(page.locator('#answer .bt-source-card')).to_have_count(1)
                expect(page.locator('#answer')).to_contain_text('Remote meetings')
                page.locator('#answer .bt-link').click()
                expect(page.locator('#source-dialog')).to_be_visible()
                page.keyboard.press('Escape')
                expect(page.locator('#source-dialog')).not_to_be_visible()
                for theme in ('dark','light'):
                    page.locator('#theme').click()
                    assert page.locator('html').get_attribute('data-theme')==theme
                    page.set_viewport_size({'width':390,'height':844})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.locator('#language').click()
                page.locator('#question').fill('木星的卫星有多少颗？');page.locator('#ask-submit').click()
                expect(page.locator('#answer')).to_contain_text('资料不足')
                expect(page.locator('#answer .bt-source-card')).to_have_count(0)
                page.locator('[data-view="sources"]').click();page.locator('#add-source').click()
                source=page.locator('#source-editors .bt-panel').last
                source.locator('input').fill('观星计划 <img src=x onerror="window.pwned=1">')
                source.locator('textarea').fill('观星活动在星期六。<script>window.pwned=1</script>')
                page.locator('#save-profile').click();expect(page.locator('#save-status')).to_contain_text('已保存')
                page.locator('[data-view="ask"]').click();page.locator('#question').fill('观星活动安排哪天？');page.locator('#ask-submit').click()
                expect(page.locator('#answer')).to_contain_text('观星计划')
                assert page.evaluate('window.pwned') is None
                assert page.locator('#answer img').count()==0
                page.locator('[data-view="share"]').click()
                checks=page.locator('#share-sources input')
                for index in range(checks.count()):checks.nth(index).uncheck()
                checks.last.check();page.locator('#preview-export').click()
                expect(page.locator('#export-json')).to_be_visible()
                payload=json.loads(page.locator('#export-json').inner_text())
                assert len(payload['sources'])==1
                with page.expect_download() as event:page.locator('#download-export').click()
                downloaded=Path(directory)/'shared.json';event.value.save_as(downloaded)
                page.locator('#import-file').set_input_files(downloaded)
                expect(page.locator('#import-preview')).to_be_visible();page.locator('#confirm-import').click()
                expect(page.locator('#source-count')).to_have_text('1 条来源')
                page.locator('#question').fill('观星活动安排哪天？');page.locator('#ask-submit').click()
                expect(page.locator('#answer')).to_contain_text('观星计划')
                page.on('dialog',lambda dialog:dialog.accept())
                page.locator('[data-view="sources"]').click();page.locator('#source-editors button').click();page.locator('#save-profile').click()
                expect(page.locator('#source-count')).to_have_text('0 条来源')
                page.locator('[data-view="ask"]').click();page.locator('#ask-submit').click()
                expect(page.locator('#answer')).to_contain_text('资料不足')
                assert not errors,errors
                browser.close()
        finally:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill();server.wait()
    print('Browser flow passed: excerpts, Chinese refusal, source CRUD, XSS, themes, mobile and sharing roundtrip.')


if __name__=='__main__':main()
