"""Local-only Flask assembly and HTTP contracts."""
import argparse
import hashlib
import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit
from flask import Flask, jsonify, render_template, request, session, url_for, g
from werkzeug.exceptions import HTTPException
from .storage import Store
from .model_client import ModelClient
from .jobs import Jobs
from .retrieval import retrieve
from .twin import export_profile, new_id, profile_version, text, validate_answer, validate_profile


def create_app(config=None):
    app=Flask(__name__)
    app.config.update(SECRET_KEY=secrets.token_hex(32),MAX_CONTENT_LENGTH=2*1024*1024,
        SESSION_COOKIE_NAME='brain_twin_session',SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Strict',
        TRUSTED_HOSTS=['localhost','127.0.0.1','[::1]'],
        DATA_DIR=os.environ.get('BRAIN_TWIN_DATA_DIR',str(Path.home()/'.local/share/brain-twin')),
        MODEL_ENDPOINT=os.environ.get('BRAIN_MODEL_URL',''),MODEL_NAME=os.environ.get('BRAIN_MODEL_NAME',''),MODEL_KEY=os.environ.get('BRAIN_MODEL_KEY',''))
    if config:
        app.config.update(config)
    store=Store(app.config['DATA_DIR'])
    model=ModelClient(app.config['MODEL_ENDPOINT'],app.config['MODEL_NAME'],app.config['MODEL_KEY'])
    jobs=Jobs()
    app.extensions.update(twin_store=store,twin_jobs=jobs,twin_model=model)

    @app.before_request
    def security():
        g.nonce=secrets.token_urlsafe(24)
        if request.method in ('POST','PUT','PATCH','DELETE'):
            if request.headers.get('Sec-Fetch-Site')=='cross-site':
                return jsonify(error='Cross-site writes are not allowed'),403
            origin=request.headers.get('Origin')
            if origin:
                target=urlsplit(request.host_url)
                supplied=urlsplit(origin)
                if (supplied.scheme,supplied.netloc)!=(target.scheme,target.netloc):
                    return jsonify(error='Origin does not match this application'),403
            token=request.headers.get('X-CSRF-Token','')
            expected=session.get('csrf','')
            if not expected or not secrets.compare_digest(token,expected):
                return jsonify(error='Missing or invalid CSRF token; reload this page'),403
            if not request.is_json:
                return jsonify(error='Use application/json'),415

    @app.after_request
    def headers(response):
        response.headers['Content-Security-Policy']=(f"default-src 'self'; script-src 'self' 'nonce-{getattr(g,'nonce','')}'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Cache-Control']='public, max-age=31536000, immutable' if request.path.startswith('/static/') and request.args.get('v') else 'no-store'
        return response

    @app.context_processor
    def context():
        def asset(name):
            path=Path(app.static_folder)/name
            return url_for('static',filename=name,v=hashlib.sha256(path.read_bytes()).hexdigest()[:10])
        return {'asset':asset,'nonce':g.nonce}

    @app.errorhandler(ValueError)
    def invalid(exc):
        return jsonify(error=str(exc)),400

    @app.errorhandler(KeyError)
    def missing(exc):
        return jsonify(error='Profile or task not found; it may have been deleted or expired'),404

    @app.errorhandler(HTTPException)
    def http_error(exc):
        return jsonify(error=exc.description),exc.code

    @app.errorhandler(OSError)
    def storage_error(exc):
        return jsonify(error='Local storage could not be written; check disk space and permissions'),500

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get('/styleguide')
    def styleguide():
        return render_template('styleguide.html')

    @app.get('/health')
    def health():
        return {'status':'ok'}

    @app.get('/api/bootstrap')
    def bootstrap():
        session.setdefault('csrf',secrets.token_urlsafe(32))
        return {'csrf_token':session['csrf'],'profiles':store.all(),'mode':'configured_provider' if model.configured else 'extracts'}

    @app.post('/api/profiles')
    def create_profile():
        data=request.get_json()
        if not isinstance(data,dict):
            raise ValueError('profile: expected a JSON object')
        return jsonify(store.save({**data,'id':new_id(),'schema_version':1},create=True)),201

    @app.put('/api/profiles/<profile_id>')
    def save_profile(profile_id):
        data=validate_profile(request.get_json())
        if data['id']!=profile_id:
            raise ValueError('profile.id does not match the URL')
        return store.save(data)

    @app.delete('/api/profiles/<profile_id>')
    def delete_profile(profile_id):
        store.delete(profile_id)
        return {'deleted':profile_id}

    @app.post('/api/import')
    def import_profile():
        profile=validate_profile(request.get_json())
        profile['id']=new_id()
        return jsonify(store.save(profile,create=True)),201

    @app.post('/api/export')
    def export():
        data=request.get_json()
        if not isinstance(data,dict):
            raise ValueError('export: expected a JSON object')
        return export_profile(store.get(data.get('profile_id')),data.get('source_ids'))

    @app.post('/api/ask')
    def ask():
        data=request.get_json()
        if not isinstance(data,dict) or set(data)-{'profile_id','question','lang','profile_version'}:
            raise ValueError('question: expected profile_id, question and optional lang/profile_version')
        question=text(data.get('question'),'question',4000,True)
        lang=data.get('lang','en')
        if lang not in ('zh','en'):
            raise ValueError('lang: expected zh or en')
        profile=store.get(data.get('profile_id'))
        version=profile_version(profile)
        expected_version=data.get('profile_version')
        if expected_version is not None:
            text(expected_version,'profile_version',64,True)
            if expected_version!=version:
                return jsonify(error='The saved library changed; reload this page before asking again'),409
        def answer():
            hits=retrieve(question,profile['sources'])
            mode='configured_provider' if model.configured else 'extracts'
            if not hits:
                result={'status':'insufficient','answer':'资料不足：没有找到足以回答此问题的相关来源。' if lang=='zh' else 'Insufficient sources: no relevant evidence was found for this question.','citations':[]}
            elif model.configured:
                result=validate_answer(model.answer(profile,question,hits,lang),hits)
            else:
                result={'status':'excerpts','answer':'以下是匹配的原文摘录，没有生成模型回答；请核对原文是否回答了问题。' if lang=='zh' else 'Matching source excerpts, without a generated answer. Check whether these passages answer your question.',
                    'citations':[{'source_id':hit['id'],'quote':hit['excerpt']} for hit in hits]}
            try:
                unchanged=store.get(profile['id'])==profile
            except KeyError:
                unchanged=False
            if not unchanged:
                raise ValueError('Sources changed while this task ran; ask again using the saved profile')
            return {**result,'mode':mode,'profile_version':version,'sources':[{'id':h['id'],'title':h['title'],'excerpt':h['excerpt']} for h in hits],
                    'notice':'Citation checks verify IDs and exact quotes, not the truth of the generated claims.'}
        try:
            task_id=jobs.submit(answer)
        except RuntimeError as exc:
            return jsonify(error=str(exc)),503,{'Retry-After':'2'}
        return jsonify(task_id=task_id,status='queued'),202

    @app.get('/api/jobs/<task_id>')
    def job(task_id):
        return jobs.get(task_id)

    return app


def main():
    parser=argparse.ArgumentParser(description='Run Brain Twin on the local loopback interface')
    parser.add_argument('--port',type=int,default=5043)
    args=parser.parse_args()
    create_app().run(host='127.0.0.1',port=args.port,debug=False,threaded=True)


if __name__=='__main__':
    main()
