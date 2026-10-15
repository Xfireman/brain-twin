"""Validated profile and answer contracts. Export is an explicit field allowlist."""
import re
import uuid
import hashlib
import json


def text(value, field, maximum, required=False):
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise ValueError(f'{field}: expected {"non-empty " if required else ""}text, at most {maximum} characters')
    return value.strip()


def identifier(value, field):
    if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', value):
        raise ValueError(f'{field}: use 1–64 letters, digits, hyphens or underscores')
    return value


def validate_profile(data):
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise ValueError('profile: schema_version must be 1')
    if set(data) - {'schema_version','id','name','description','instructions','sources'}:
        raise ValueError('profile: unexpected fields (history and credentials are not accepted)')
    sources = data.get('sources')
    if not isinstance(sources, list) or len(sources) > 50:
        raise ValueError('sources: expected a list with at most 50 text sources')
    cleaned = []
    seen = set()
    total = 0
    for source in sources:
        if not isinstance(source, dict) or set(source) != {'id','title','text'}:
            raise ValueError('source: expected exactly id, title and text')
        sid = identifier(source['id'], 'source.id')
        if sid in seen:
            raise ValueError('source.id: duplicate identifier')
        seen.add(sid)
        body = text(source['text'], 'source.text', 30000, True)
        total += len(body)
        cleaned.append({'id':sid,'title':text(source['title'],'source.title',160,True),'text':body})
    if total > 200000:
        raise ValueError('sources: combined text exceeds 200000 characters')
    return {'schema_version':1,'id':identifier(data.get('id'),'profile.id'),
            'name':text(data.get('name'),'name',120,True),
            'description':text(data.get('description',''),'description',2000),
            'instructions':text(data.get('instructions',''),'instructions',2000),
            'sources':cleaned}


def new_id():
    return uuid.uuid4().hex


def profile_version(profile):
    canonical=json.dumps(profile,sort_keys=True,ensure_ascii=False,separators=(',',':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def export_profile(profile, source_ids):
    if not isinstance(source_ids, list) or any(not isinstance(s, str) for s in source_ids):
        raise ValueError('source_ids: expected a list of selected IDs')
    allowed = {s['id'] for s in profile['sources']}
    if not source_ids or len(set(source_ids)) != len(source_ids) or not set(source_ids) <= allowed:
        raise ValueError('source_ids: select at least one existing source; duplicates are not allowed')
    return validate_profile({**profile,'sources':[s for s in profile['sources'] if s['id'] in source_ids]})


def validate_answer(answer, allowed_sources):
    if not isinstance(answer, dict) or set(answer) != {'status','answer','citations'}:
        raise ValueError('answer: expected status, answer and citations')
    status = answer['status']
    if status not in ('answered','insufficient'):
        raise ValueError('answer.status: expected answered or insufficient')
    body = text(answer['answer'],'answer',12000,True)
    citations = answer['citations']
    if not isinstance(citations,list) or len(citations)>12:
        raise ValueError('citations: expected at most 12 citations')
    lookup = {s['id']:s.get('excerpt',s.get('text','')) for s in allowed_sources}
    clean = []
    for citation in citations:
        if not isinstance(citation,dict) or set(citation) != {'source_id','quote'} or citation.get('source_id') not in lookup:
            raise ValueError('citation: unknown or malformed source ID')
        quote = text(citation['quote'],'quote',900,True)
        if quote not in lookup[citation['source_id']]:
            raise ValueError('quote: not present in the retrieved source excerpt')
        clean.append({'source_id':citation['source_id'],'quote':quote})
    if status == 'answered' and not clean:
        raise ValueError('citations: an answer requires at least one real source')
    if status == 'insufficient' and clean:
        raise ValueError('citations: insufficient answer must not claim supporting sources')
    return {'status':status,'answer':body,'citations':clean}
