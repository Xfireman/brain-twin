import json
import time
import pytest
from brain_twin.app import create_app

@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATA_DIR": str(tmp_path), "MODEL_ENDPOINT": "", "MODEL_NAME": "", "MODEL_KEY": ""})

@pytest.fixture
def client(app):
    return app.test_client()

def bootstrap(client):
    response = client.get('/api/bootstrap')
    assert response.status_code == 200
    data = response.get_json()
    return data, {'X-CSRF-Token': data['csrf_token']}

def wait_job(client, task):
    for _ in range(100):
        r = client.get('/api/jobs/' + task).get_json()
        if r['status'] in ('succeeded', 'failed'):
            return r
        time.sleep(.01)
    pytest.fail('job did not finish')

def test_example_chinese_excerpts_and_unrelated_refusal(client):
    data, headers = bootstrap(client)
    pid = data['profiles'][0]['id']
    r = client.post('/api/ask', json={'profile_id':pid,'question':'远程会议如何记录决定？','lang':'zh'}, headers=headers)
    assert r.status_code == 202
    result = wait_job(client,r.json['task_id'])
    assert result['status'] == 'succeeded'
    assert result['result']['mode'] == 'extracts'
    assert result['result']['citations'][0]['source_id'] == 'meeting-notes'
    r = client.post('/api/ask', json={'profile_id':pid,'question':'木星的卫星有多少颗？','lang':'zh'}, headers=headers)
    result = wait_job(client,r.json['task_id'])['result']
    assert result['status'] == 'insufficient'
    assert result['citations'] == []

def test_save_edit_delete_and_restart(app,client):
    data, headers = bootstrap(client)
    profile = data['profiles'][0]
    profile['sources'].append({'id':'stargazing','title':'观星计划','text':'观星活动安排在星期五。'})
    assert client.put('/api/profiles/'+profile['id'],json=profile,headers=headers).status_code == 200
    profile['sources'][-1]['text'] = '观星活动安排在星期六。'
    client.put('/api/profiles/'+profile['id'],json=profile,headers=headers)
    again = create_app({'TESTING':True,'DATA_DIR':app.config['DATA_DIR'],'MODEL_ENDPOINT':'','MODEL_NAME':'','MODEL_KEY':''}).test_client()
    saved,_=bootstrap(again)
    assert saved['profiles'][0]['sources'][-1]['text'] == '观星活动安排在星期六。'
    profile['sources'] = [s for s in profile['sources'] if s['id']!='stargazing']
    client.put('/api/profiles/'+profile['id'],json=profile,headers=headers)
    r=client.post('/api/ask',json={'profile_id':profile['id'],'question':'观星活动安排哪天？'},headers=headers)
    assert wait_job(client,r.json['task_id'])['result']['status']=='insufficient'

def test_export_selection_import_roundtrip_and_no_secrets(client):
    data,headers=bootstrap(client)
    profile=data['profiles'][0]
    r=client.post('/api/export',json={'profile_id':profile['id'],'source_ids':['meeting-notes']},headers=headers)
    assert r.status_code==200
    exported=r.json
    assert [s['id'] for s in exported['sources']]==['meeting-notes']
    assert set(exported)=={'schema_version','id','name','description','instructions','sources'}
    restored=client.post('/api/import',json=exported,headers=headers)
    assert restored.status_code==201
    assert restored.json['sources']==exported['sources']
    assert restored.json['id']!=profile['id']
    assert 'csrf' not in json.dumps(exported)

def test_cross_site_and_missing_csrf_rejected(client):
    data,headers=bootstrap(client)
    profile=data['profiles'][0]
    path='/api/profiles/'+profile['id']
    assert client.put(path,json=profile).status_code==403
    assert client.put(path,json=profile,headers={**headers,'Origin':'https://evil.example'}).status_code==403
    assert client.put(path,json=profile,headers={**headers,'Sec-Fetch-Site':'cross-site'}).status_code==403
    assert client.get('/api/bootstrap',headers={'Host':'evil.example'}).status_code==400

def test_validation_errors_not_500(client):
    data,headers=bootstrap(client)
    assert client.post('/api/import',data='no-json',content_type='application/json',headers=headers).status_code==400
    assert client.post('/api/ask',json={'profile_id':data['profiles'][0]['id'],'question':'x'*4001},headers=headers).status_code==400
    assert client.post('/api/import',json={'schema_version':55},headers=headers).status_code==400

def test_no_external_resources_and_xss_is_data(client):
    data,headers=bootstrap(client)
    profile=data['profiles'][0]
    profile['name']='<img src=x onerror=alert(1)>'
    profile['sources'][0]['text']='<script>window.pwned=true</script> 远程会议记录'
    assert client.put('/api/profiles/'+profile['id'],json=profile,headers=headers).status_code==200
    page=client.get('/')
    assert page.status_code==200
    assert '<img src=x' not in page.text
    assert "default-src 'self'" in page.headers['Content-Security-Policy']
    assert client.get('/styleguide').status_code==200


def test_shared_package_works_in_another_users_empty_data_directory(client,tmp_path):
    data,headers=bootstrap(client)
    new_profile=client.post('/api/profiles',json={'name':'海龟调查','description':'Synthetic field notes','instructions':'','sources':[{'id':'turtles','title':'海龟调查时间','text':'海龟调查每天清晨六点开始。'}]},headers=headers).json
    package=client.post('/api/export',json={'profile_id':new_profile['id'],'source_ids':['turtles']},headers=headers).json
    other=create_app({'TESTING':True,'DATA_DIR':str(tmp_path/'another-user'),'MODEL_ENDPOINT':'','MODEL_NAME':'','MODEL_KEY':''}).test_client()
    _,other_headers=bootstrap(other)
    imported=other.post('/api/import',json=package,headers=other_headers)
    assert imported.status_code==201
    assert imported.json['id']!=new_profile['id']
    question=other.post('/api/ask',json={'profile_id':imported.json['id'],'question':'海龟调查几点开始？','lang':'zh'},headers=other_headers)
    result=wait_job(other,question.json['task_id'])['result']
    assert result['citations']==[{'source_id':'turtles','quote':'海龟调查每天清晨六点开始。'}]
