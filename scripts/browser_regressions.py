"""Real browser regressions for answer identity and cross-port cookie isolation.

Uses temporary synthetic profiles and a local in-process model stand-in only.
"""
from contextlib import contextmanager
import json
import tempfile
import sys
import threading
import traceback
from flask import Flask, session
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server, WSGIRequestHandler
from brain_twin.app import create_app


class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs):
        pass


@contextmanager
def running_app(app):
    server=make_server('127.0.0.1',0,app,threaded=True,request_handler=QuietHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown();server.server_close();thread.join()


@contextmanager
def scenario(browser):
    with tempfile.TemporaryDirectory(prefix='twin-regression-') as directory:
        app=create_app({'DATA_DIR':directory,'MODEL_ENDPOINT':'http://127.0.0.1:1/chat/completions','MODEL_NAME':'synthetic','MODEL_KEY':''})
        state={'fail':False}
        def answer(profile,question,hits,lang):
            if state['fail']:
                raise RuntimeError('Synthetic provider failure')
            return {'status':'answered','answer':'ANSWER: '+question,'citations':[{'source_id':hits[0]['id'],'quote':hits[0]['excerpt']}]}
        app.extensions['twin_model'].answer=answer
        with running_app(app) as url:
            context=browser.new_context()
            page=context.new_page()
            page.add_init_script("localStorage.setItem('twin-lang','en')")
            page.on('dialog',lambda dialog:dialog.accept())
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(url)
            expect(page.locator('#profile-heading')).to_contain_text('Field Notes')
            try:
                yield page,state,context,url
                assert not errors,errors
            finally:
                context.close()
        app.extensions['twin_jobs'].executor.shutdown()


def ask(page, question='How should a remote team record decisions?'):
    page.locator('[data-view="ask"]').click()
    page.locator('#question').fill(question)
    page.locator('#ask-submit').click()


def answered(page):
    expect(page.locator('#answer .bt-source-card')).to_have_count(1)
    expect(page.locator('#ask-submit')).to_be_enabled()


def no_answer(page):
    expect(page.locator('#answer .bt-source-card')).to_have_count(0)
    assert 'ANSWER:' not in page.locator('#answer').inner_text()


def hold_next_result(page):
    held=[]
    captured=False
    def intercept(route):
        nonlocal captured
        response=route.fetch()
        if not captured and response.json()['status'] in ('succeeded','failed'):
            captured=True
            held.append((route,response))
        else:
            route.fulfill(response=response)
    page.route('**/api/jobs/*',intercept)
    return held


def wait_held(page,held):
    # Pump Playwright while waiting for an actual terminal job response.
    for _ in range(100):
        if held:return
        page.wait_for_timeout(20)
    raise AssertionError('No terminal job response was captured')


def release_result(page,held):
    route,response=held.pop(0)
    with page.expect_response('**/api/jobs/*'):
        route.fulfill(response=response)
    page.unroute('**/api/jobs/*')
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')


def test_new_profile_invalidates_answer(browser):
    with scenario(browser) as (page,_,__,___):
        ask(page);answered(page)
        page.locator('#new-profile').click()
        expect(page.locator('#source-count')).to_have_text('0 sources')
        page.locator('[data-view="ask"]').click()
        no_answer(page)


def test_delete_cited_source_invalidates_answer(browser):
    with scenario(browser) as (page,_,__,___):
        ask(page);answered(page)
        page.locator('[data-view="sources"]').click()
        page.locator('#source-editors .bt-panel').first.locator('button').click()
        page.locator('#save-profile').click()
        expect(page.locator('#save-status')).to_have_text('Saved locally')
        page.locator('[data-view="ask"]').click()
        no_answer(page)


def test_save_modified_source_invalidates_answer(browser):
    with scenario(browser) as (page,_,__,___):
        ask(page);answered(page)
        page.locator('[data-view="sources"]').click()
        page.locator('#source-editors textarea').first.fill('Remote meeting decisions are written in a new notebook.')
        page.locator('#save-profile').click()
        expect(page.locator('#save-status')).to_have_text('Saved locally')
        page.locator('[data-view="ask"]').click()
        no_answer(page)


def test_new_request_and_failure_remove_old_answer(browser):
    with scenario(browser) as (page,state,_,__):
        ask(page);answered(page)
        held=hold_next_result(page)
        state['fail']=True
        page.locator('#ask-submit').click()
        wait_held(page,held)
        try:
            no_answer(page)
        finally:
            release_result(page,held)
        expect(page.locator('#ask-error')).to_contain_text('Synthetic provider failure')
        no_answer(page)


def test_switch_away_and_back_rejects_old_inflight_result(browser):
    with scenario(browser) as (page,_,__,___):
        original=page.locator('#profile-select').input_value()
        page.locator('#new-profile').click()
        expect(page.locator('#profile-heading')).to_have_text('Untitled profile')
        other=page.locator('#profile-select').input_value()
        page.locator('#profile-select').select_option(original)
        held=hold_next_result(page)
        ask(page);wait_held(page,held)
        page.locator('#profile-select').select_option(other)
        page.locator('#profile-select').select_option(original)
        release_result(page,held)
        no_answer(page)


def test_save_same_profile_rejects_old_inflight_result(browser):
    with scenario(browser) as (page,_,__,___):
        held=hold_next_result(page)
        ask(page);wait_held(page,held)
        page.locator('[data-view="sources"]').click()
        page.locator('#source-editors textarea').first.fill('Remote meeting decisions now have a revised owner policy.')
        page.locator('#save-profile').click()
        expect(page.locator('#save-status')).to_have_text('Saved locally')
        page.locator('[data-view="ask"]').click()
        release_result(page,held)
        no_answer(page)


def test_newer_question_wins_over_old_inflight_result(browser):
    with scenario(browser) as (page,_,__,___):
        held=hold_next_result(page)
        ask(page,'Earlier question: how should a remote team record decisions?')
        wait_held(page,held)
        page.locator('#question').fill('Latest question: how should a remote team record a decision owner?')
        try:
            expect(page.locator('#ask-submit')).to_be_enabled()
            page.locator('#ask-submit').click()
            answered(page)
            expect(page.locator('#answer')).to_contain_text('Latest question:')
        finally:
            release_result(page,held)
        expect(page.locator('#answer')).to_contain_text('Latest question:')
        assert 'Earlier question:' not in page.locator('#answer').inner_text()


def test_other_port_session_cookie_does_not_break_writes(browser):
    neighbor=Flask('synthetic_neighbor')
    neighbor.secret_key='synthetic-neighbor-session-key'
    @neighbor.get('/')
    def home():
        session['sentinel']='another local application'
        return 'Synthetic neighboring application'
    with scenario(browser) as (page,_,context,url),running_app(neighbor) as neighbor_url:
        bootstrap=page.evaluate('() => fetch("/api/bootstrap").then(r=>r.json())')
        other=context.new_page();other.goto(neighbor_url)
        status=page.evaluate('''data => fetch('/api/profiles/'+data.profiles[0].id,{method:'PUT',headers:{'Content-Type':'application/json','X-CSRF-Token':data.csrf_token},body:JSON.stringify(data.profiles[0])}).then(r=>r.status)''',bootstrap)
        assert status==200,f'Write failed after another port set its default session cookie: {status}'
        assert 'brain_twin_session' in {cookie['name'] for cookie in context.cookies(url)}


def main():
    cases=[value for name,value in globals().items() if name.startswith('test_') and (not sys.argv[1:] or name in sys.argv[1:])]
    results=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        for case in cases:
            try:
                case(browser)
                results.append({'case':case.__name__,'status':'passed'})
            except Exception as exc:
                results.append({'case':case.__name__,'status':'failed','error':str(exc)})
                traceback.print_exc()
        browser.close()
    print(json.dumps(results,indent=2))
    if any(result['status']=='failed' for result in results):
        raise SystemExit(1)
    print(f'{len(results)} browser regressions passed.')


if __name__=='__main__':
    main()
