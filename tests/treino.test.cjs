const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('jsdom');
const html=fs.readFileSync('frontend/laboratorio.html','utf8'),code=fs.readFileSync('frontend/amber.js','utf8'),portal=fs.readFileSync('frontend/portal.html','utf8');
for(const [id,expected] of [['CIV-001','Audiência agendada'],['CON-002','Nova versão do contrato'],['TRA-003','data de referência não informada']])test('treino guiado do exemplo '+id,async()=>{
 const dom=new JSDOM(html,{url:'http://127.0.0.1:8093/laboratorio.html?treino=1',runScripts:'outside-only',pretendToBeVisual:true});
 try{
  const w=dom.window,d=w.document;
  w.HTMLElement.prototype.scrollIntoView=function(){};
  w.scrollTo=function(){};
  w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  w.HTMLDialogElement.prototype.close=function(){this.open=false;};
  w.fetch=async()=>({ok:true,status:200,text:async()=>portal});
  w.eval(code);
  assert.equal(d.getElementById('start-dialog').open,true);
  d.getElementById('training-case-choice').value=id;d.getElementById('start-training').click();
  d.getElementById('open-catalog').click();
  const selected=d.querySelector(`[data-add="${id}"]`);assert.equal(selected.disabled,false);selected.click();
  d.querySelector(`[data-select="${id}"]`).click();
  d.getElementById('source-open').click();
  for(let i=0;i<100&&!d.getElementById('source-preview').children.length;i++)await new Promise(r=>setTimeout(r,5));
  assert.equal(d.querySelectorAll('#source iframe').length,0);
  assert.equal(d.querySelectorAll('#source-preview article').length,3);
  assert.match(d.querySelector('#source-preview .selected-source').textContent,new RegExp(id));
  d.getElementById('source-back').click();
  d.getElementById('consult').click();
  for(let i=0;i<100&&d.getElementById('consult').disabled;i++)await new Promise(r=>setTimeout(r,5));
  assert.match(d.querySelector('.movement>span').textContent,new RegExp(expected));
  d.querySelector(`[data-detail="${id}"]`).click();d.getElementById('mark-reviewed').click();
  assert.match(d.getElementById('case-rows').textContent,/Conferido por você/);
  if(id==='TRA-003')assert.match(d.getElementById('detail-content').textContent,/incompleta/);
 }finally{dom.window.close();}
});

test('fonte com falha mostra recuperação e permite tentar novamente',async()=>{
 const dom=new JSDOM(html,{url:'http://127.0.0.1:8093/laboratorio.html',runScripts:'outside-only',pretendToBeVisual:true});
 try{
  const w=dom.window,d=w.document;w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};
  w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};
  let tentativa=0;w.fetch=async()=>++tentativa===1?{ok:false,status:503}:{ok:true,status:200,text:async()=>portal};
  w.eval(code);d.getElementById('source-open').click();
  for(let i=0;i<100&&d.getElementById('source-retry').hidden;i++)await new Promise(r=>setTimeout(r,5));
  assert.equal(d.getElementById('source-retry').hidden,false);
  assert.match(d.getElementById('source-status').textContent,/Não foi possível/);
  d.getElementById('source-retry').click();
  for(let i=0;i<100&&!d.getElementById('source-preview').children.length;i++)await new Promise(r=>setTimeout(r,5));
  assert.equal(d.getElementById('source-preview').children.length,3);
  d.getElementById('source-back').click();assert.equal(d.getElementById('source').open,false);
 }finally{dom.window.close();}
});
