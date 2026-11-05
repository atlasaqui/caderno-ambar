const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('jsdom');

test('apresentação separa treino, acesso e proposta do produto',()=>{
 const dom=new JSDOM(fs.readFileSync('frontend/index.html','utf8'));
 try{
  const d=dom.window.document;
  assert.equal(d.querySelectorAll('#case-rows,#auth-form,#coach').length,0);
  assert.ok(d.querySelector('a[href="laboratorio.html?treino=1"]'));
  assert.ok(d.querySelector('a[href="acesso.html?modo=cadastro"]'));
  assert.ok(d.querySelector('a[href="acesso.html?modo=entrar"]'));
  assert.equal(d.querySelectorAll('.path-grid article').length,4);
 }finally{dom.window.close();}
});

test('acesso mostra um modo por vez e explica os campos sem salvar senha',()=>{
 const dom=new JSDOM(fs.readFileSync('frontend/acesso.html','utf8'),{url:'http://127.0.0.1:8093/acesso.html?modo=cadastro',runScripts:'outside-only'});
 try{
  const w=dom.window,d=w.document;w.eval(fs.readFileSync('frontend/acesso.js','utf8'));
  assert.equal(d.getElementById('access-register').getAttribute('aria-selected'),'true');
  d.getElementById('access-login').click();
  assert.equal(d.getElementById('access-login').getAttribute('aria-selected'),'true');
  assert.equal(d.getElementById('access-password').autocomplete,'current-password');
  d.getElementById('access-password').focus();assert.match(d.getElementById('access-guidance').textContent,/senha do tribunal/);
  assert.equal(w.localStorage.length,0);
 }finally{dom.window.close();}
});
