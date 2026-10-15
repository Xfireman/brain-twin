(function () {
  'use strict';
  const $=id=>document.getElementById(id), t=key=>window.TwinI18n.t(key);
  let profiles=[], current=null, draft=null, csrf='', mode='extracts', dirty=false, exportData=null, importData=null, asking=false, view='ask';
  const clone=value=>JSON.parse(JSON.stringify(value));
  function el(tag,cls,content){const node=document.createElement(tag);if(cls)node.className=cls;if(content!==undefined)node.textContent=content;return node;}
  function error(id,message){$(id).hidden=!message;$(id).textContent=message||'';}
  async function api(path,method='GET',body){
    let response;
    try {response=await fetch(path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(30000)});}
    catch(e){throw new Error(t('networkError'));}
    let data;try{data=await response.json();}catch(e){throw new Error(t('networkError'));}
    if(!response.ok)throw new Error(data.error||('HTTP '+response.status));return data;
  }
  function markDirty(){dirty=true;$('dirty-state').textContent=t('unsaved');$('save-status').textContent='';exportData=null;$('export-preview').hidden=true;}
  function setView(next){view=next;document.querySelectorAll('.bt-view').forEach(node=>{node.hidden=node.id!=='view-'+next;});document.querySelectorAll('[data-view]').forEach(node=>{const active=node.dataset.view===next;node.classList.toggle('active',active);node.setAttribute('aria-current',active?'page':'false');});if(next==='share')renderShare();}
  function syncFields(){if(!draft)return;draft.name=$('profile-name').value;draft.description=$('profile-description-input').value;draft.instructions=$('profile-instructions').value;}
  function renderMeta(){
    $('profile-heading').textContent=current?current.name:'Brain Twin';$('profile-description').textContent=current?current.description:t('noProfiles');
    $('mode-label').textContent=t(mode==='extracts'?'extractMode':'modelMode');$('mode-description').textContent=t(mode==='extracts'?'extractDesc':'modelDesc');
    $('ask-submit').textContent=t(asking?'busy':mode==='extracts'?'askSubmit':'askModel');$('source-count').textContent=(current?current.sources.length:0)+' '+t('sourcesCount');
    $('dirty-state').textContent=dirty?t('unsaved'):'';
    for(const id of ['ask-submit','save-profile','add-source','delete-profile','preview-export'])$(id).disabled=!current||(id==='ask-submit'&&asking);
  }
  function renderProfiles(){const select=$('profile-select');select.replaceChildren();if(!profiles.length){select.append(el('option','',t('selectProfile')));}for(const p of profiles){const option=el('option','',p.name);option.value=p.id;select.append(option);}if(current)select.value=current.id;}
  function renderEditors(){
    const container=$('source-editors');container.replaceChildren();
    if(!draft||!draft.sources.length){container.append(el('p','bt-note',t('emptySources')));return;}
    draft.sources.forEach((source,index)=>{
      const panel=el('div','bt-panel'),head=el('div','bt-ph'),body=el('div','bt-pb');head.append(el('span','bt-mono',t('source')+' '+String(index+1).padStart(2,'0')));
      const remove=el('button','bt-btn ghost danger',t('removeSource'));remove.type='button';remove.addEventListener('click',()=>{if(confirm(t('confirmRemove'))){syncFields();draft.sources=draft.sources.filter(item=>item.id!==source.id);markDirty();renderEditors();}});head.append(remove);
      const titleId='title-'+source.id,textId='text-'+source.id;
      const titleLabel=el('label','',t('sourceTitle'));titleLabel.htmlFor=titleId;
      const title=el('input','bt-input');title.id=titleId;title.value=source.title;title.required=true;title.maxLength=160;title.setAttribute('aria-describedby','profile-error');title.addEventListener('input',()=>{source.title=title.value;markDirty();});
      const bodyLabel=el('label','',t('sourceText'));bodyLabel.htmlFor=textId;
      const area=el('textarea','bt-input');area.id=textId;area.rows=7;area.value=source.text;area.required=true;area.maxLength=30000;area.setAttribute('aria-describedby','profile-error');area.addEventListener('input',()=>{source.text=area.value;markDirty();});
      body.append(titleLabel,title,bodyLabel,area);panel.append(head,body);container.append(panel);
    });
  }
  function selectProfile(id){
    current=profiles.find(p=>p.id===id)||profiles[0]||null;draft=current?clone(current):null;dirty=false;
    $('profile-name').value=draft?draft.name:'';$('profile-description-input').value=draft?draft.description:'';$('profile-instructions').value=draft?draft.instructions:'';
    for(const id of ['ask-error','profile-error','export-error'])error(id,'');$('save-status').textContent='';exportData=null;$('export-preview').hidden=true;
    renderProfiles();renderMeta();renderEditors();renderShare();
  }
  function renderShare(){
    const box=$('share-sources');box.replaceChildren(el('legend','',t('selectedSources')));
    if(!current)return;
    for(const source of current.sources){const label=el('label','bt-check'),input=el('input');input.type='checkbox';input.value=source.id;input.checked=true;input.addEventListener('change',()=>{exportData=null;$('export-preview').hidden=true;});label.append(input,el('span','',source.title+' · '+source.text.length+' '+t('chars')));box.append(label);}
  }
  function openSource(sourceId,profileId,original){
    const profile=profiles.find(p=>p.id===profileId),source=profile&&profile.sources.find(s=>s.id===sourceId);
    if(!source||source.text!==original.text){error('ask-error',t('sourceMissing'));return;}
    $('source-dialog-title').textContent=source.title;$('source-dialog-text').textContent=source.text;$('source-dialog').showModal();
  }
  function renderAnswer(result,profile){
    const container=$('answer');container.replaceChildren();
    const head=el('div','bt-section-head');head.append(el('h2','',t(result.status==='insufficient'?'insufficient':result.mode==='extracts'?'extractsTitle':'answerTitle')),el('span','bt-badge',t(result.mode==='extracts'?'extractMode':'modelMode')));container.append(head,el('p','bt-answer-body',result.answer));
    if(result.status==='insufficient')container.append(el('p','bt-note',t('noEvidence')));
    result.citations.forEach((citation,index)=>{
      const source=profile.sources.find(s=>s.id===citation.source_id),card=el('article','bt-source-card');
      card.append(el('div','bt-eyebrow',t('source')+' '+String(index+1).padStart(2,'0')),el('h3','',source?source.title:citation.source_id),el('blockquote','',citation.quote));
      const button=el('button','bt-link',t('viewSource'));button.type='button';button.addEventListener('click',()=>openSource(citation.source_id,profile.id,source));card.append(button);container.append(card);
    });
    if(result.citations.length)container.append(el('p','bt-note',t('citationNotice')));
  }
  document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>setView(button.dataset.view)));
  $('profile-select').addEventListener('change',()=>{if(dirty&&!confirm(t('discard'))){$('profile-select').value=current.id;return;}selectProfile($('profile-select').value);$('answer').replaceChildren(el('p','bt-note',t('emptyHint')));});
  ['profile-name','profile-description-input','profile-instructions'].forEach(id=>$(id).addEventListener('input',markDirty));
  $('add-source').addEventListener('click',()=>{if(!draft)return;syncFields();draft.sources.push({id:'source-'+crypto.randomUUID(),title:'',text:''});markDirty();renderEditors();$('source-editors').lastElementChild.querySelector('input').focus();});
  $('new-profile').addEventListener('click',async()=>{if(dirty&&!confirm(t('discard')))return;try{const created=await api('/api/profiles','POST',{name:t('newName'),description:'',instructions:'',sources:[]});profiles.push(created);selectProfile(created.id);setView('sources');$('profile-name').focus();}catch(e){error('global-error',e.message);}});
  $('delete-profile').addEventListener('click',async()=>{if(!current||!confirm(t('confirmDelete')))return;try{await api('/api/profiles/'+current.id,'DELETE',{});profiles=profiles.filter(p=>p.id!==current.id);selectProfile();$('answer').replaceChildren(el('p','bt-note',t('emptyHint')));}catch(e){error('global-error',e.message);}});
  $('profile-form').addEventListener('submit',async event=>{event.preventDefault();if(!draft)return;syncFields();error('profile-error','');$('save-profile').disabled=true;try{const saved=await api('/api/profiles/'+draft.id,'PUT',draft);profiles=profiles.map(p=>p.id===saved.id?saved:p);selectProfile(saved.id);$('save-status').textContent=t('saved');$('profile-name').removeAttribute('aria-invalid');}catch(e){error('profile-error',t('requestFailed')+e.message);$('profile-name').setAttribute('aria-invalid','true');}finally{$('save-profile').disabled=false;}});
  $('example-question').addEventListener('click',()=>{$('question').value=t('exampleQuestion');$('question').focus();});
  $('ask-form').addEventListener('submit',async event=>{
    event.preventDefault();if(!current||asking)return;error('ask-error','');if(dirty){error('ask-error',t('needSave'));return;}
    asking=true;renderMeta();$('ask-status').hidden=false;$('ask-status').textContent=t('queued');const profile=clone(current);
    try{
      const task=await api('/api/ask','POST',{profile_id:current.id,question:$('question').value,lang:window.TwinI18n.lang});let done=false;
      for(let attempt=0;attempt<120;attempt++){
        const job=await api('/api/jobs/'+task.task_id);$('ask-status').textContent=t(job.status==='queued'?'queued':'running');
        if(job.status==='failed')throw new Error(job.error);
        if(job.status==='succeeded'){if(current&&current.id===profile.id)renderAnswer(job.result,profile);done=true;break;}
        await new Promise(resolve=>setTimeout(resolve,500));
      }
      if(!done)throw new Error(t('timeout'));$('question').removeAttribute('aria-invalid');
    }catch(e){error('ask-error',t('requestFailed')+e.message);$('question').setAttribute('aria-invalid','true');}
    finally{asking=false;$('ask-status').hidden=true;renderMeta();}
  });
  $('preview-export').addEventListener('click',async()=>{error('export-error','');exportData=null;$('export-preview').hidden=true;if(dirty){error('export-error',t('needSave'));return;}const ids=Array.from($('share-sources').querySelectorAll('input:checked')).map(input=>input.value);if(!ids.length){error('export-error',t('noSelection'));return;}try{exportData=await api('/api/export','POST',{profile_id:current.id,source_ids:ids});$('export-json').textContent=JSON.stringify(exportData,null,2);$('export-preview').hidden=false;}catch(e){error('export-error',e.message);}});
  $('download-export').addEventListener('click',()=>{if(!exportData)return;const blob=new Blob([JSON.stringify(exportData,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='brain-twin-profile.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  $('import-file').addEventListener('change',async()=>{error('import-error','');importData=null;$('import-preview').hidden=true;const file=$('import-file').files[0];if(!file)return;try{if(file.size>2*1024*1024)throw new Error(t('importSize'));const parsed=JSON.parse(await file.text());if(!parsed||parsed.schema_version!==1||!Array.isArray(parsed.sources))throw new Error(t('importInvalid'));importData=parsed;$('import-json').textContent=JSON.stringify(parsed,null,2);$('import-preview').hidden=false;}catch(e){error('import-error',e.message);}});
  $('confirm-import').addEventListener('click',async()=>{if(!importData||(dirty&&!confirm(t('discard'))))return;$('confirm-import').disabled=true;try{const imported=await api('/api/import','POST',importData);profiles.push(imported);selectProfile(imported.id);importData=null;$('import-preview').hidden=true;$('import-file').value='';setView('ask');$('answer').replaceChildren(el('p','bt-note',t('emptyHint')));}catch(e){error('import-error',e.message);}finally{$('confirm-import').disabled=false;}});
  window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
  document.addEventListener('languagechange',()=>{syncFields();renderMeta();renderEditors();renderShare();});
  api('/api/bootstrap').then(data=>{csrf=data.csrf_token;profiles=data.profiles;mode=data.mode;selectProfile();}).catch(e=>error('global-error',e.message));
}());
