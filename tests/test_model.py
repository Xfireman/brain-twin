import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from brain_twin.model_client import ModelClient
from brain_twin.app import create_app
from test_app import bootstrap, wait_job

@pytest.fixture
def provider():
    received=[]
    state={'code':200,'body':{'choices':[{'message':{'content':json.dumps({'status':'answered','answer':'每条决定写明负责人。','citations':[{'source_id':'meeting-notes','quote':'每条决定写明负责人'}]},ensure_ascii=False)}}]}}
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append({'path':self.path,'authorization':self.headers.get('Authorization'),'body':json.loads(self.rfile.read(int(self.headers['Content-Length'])))})
            self.send_response(state['code'])
            self.send_header('Content-Type','application/json')
            if state['code']==302:
                self.send_header('Location','/leaked')
            self.end_headers()
            self.wfile.write(json.dumps(state['body']).encode())
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}/v1/chat/completions',received,state
    server.shutdown();server.server_close();thread.join()

def test_actual_provider_request_and_structured_result(provider):
    url,received,state=provider
    client=ModelClient(url,'synthetic-model','synthetic-key')
    result=client.answer({'instructions':'Be concise.'},'谁负责记录？',[{'id':'meeting-notes','title':'会议','excerpt':'每条决定写明负责人。'}],'zh')
    assert result['citations'][0]['source_id']=='meeting-notes'
    wire=received[0]
    assert wire['path']=='/v1/chat/completions'
    assert wire['authorization']=='Bearer synthetic-key'
    assert wire['body']['model']=='synthetic-model'
    assert wire['body']['response_format']=={'type':'json_object'}
    assert wire['body']['stream'] is False
    assert '谁负责记录？' in wire['body']['messages'][1]['content']
    assert '每条决定写明负责人。' in wire['body']['messages'][1]['content']
    assert 'synthetic-key' not in json.dumps(wire['body'])

@pytest.mark.parametrize('url',['http://example.com/completions','https://u:p@example.com/x','https://example.com/x?key=secret','file:///tmp/file'])
def test_unsafe_endpoint_rejected(url):
    with pytest.raises(ValueError): ModelClient(url,'model','')

def test_provider_failure_is_visible_and_no_redirect(provider):
    url,received,state=provider
    state.update(code=302,body={'secret':'synthetic-key'})
    with pytest.raises(RuntimeError) as error:
        ModelClient(url,'model','synthetic-key').answer({'instructions':''},'question',[])
    assert 'synthetic-key' not in str(error.value)
    assert len(received)==1

def test_configured_model_failure_stays_failed(tmp_path,provider):
    url,received,state=provider
    state.update(code=500,body={'error':'secret synthetic-key'})
    client=create_app({'TESTING':True,'DATA_DIR':str(tmp_path),'MODEL_ENDPOINT':url,'MODEL_NAME':'test','MODEL_KEY':'synthetic-key'}).test_client()
    data,headers=bootstrap(client)
    r=client.post('/api/ask',json={'profile_id':data['profiles'][0]['id'],'question':'远程会议记录决定'},headers=headers)
    job=wait_job(client,r.json['task_id'])
    assert job['status']=='failed'
    assert 'result' not in job
    assert 'synthetic-key' not in json.dumps(job)
    assert len(received)==1

def test_forged_provider_citation_fails_job(tmp_path,provider):
    url,received,state=provider
    state['body']['choices'][0]['message']['content']=json.dumps({'status':'answered','answer':'Made up','citations':[{'source_id':'missing','quote':'Made up'}]})
    client=create_app({'TESTING':True,'DATA_DIR':str(tmp_path),'MODEL_ENDPOINT':url,'MODEL_NAME':'test','MODEL_KEY':''}).test_client()
    data,headers=bootstrap(client)
    r=client.post('/api/ask',json={'profile_id':data['profiles'][0]['id'],'question':'远程会议记录决定'},headers=headers)
    job=wait_job(client,r.json['task_id'])
    assert job['status']=='failed'
    assert 'citation' in job['error']
