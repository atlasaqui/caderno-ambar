'use strict';
(() => {
  const get=id=>document.getElementById(id);
  let mode=new URLSearchParams(location.search).get('modo')==='entrar'?'entrar':'cadastro';
  let submitting=false;
  function showMode(next){
    mode=next;
    const register=mode==='cadastro';
    get('access-register').setAttribute('aria-selected',String(register));
    get('access-login').setAttribute('aria-selected',String(!register));
    get('access-title').textContent=register?'Crie sua conta':'Bem-vindo de volta';
    get('access-description').textContent=register?'Use seu e-mail e escolha uma senha de 10 a 128 caracteres.':'Informe o e-mail e a senha que você cadastrou.';
    get('access-password').autocomplete=register?'new-password':'current-password';
    get('access-submit').textContent=register?'Criar conta e continuar →':'Entrar no meu escritório →';
    get('access-password').value='';get('access-status').hidden=true;
  }
  get('access-register').onclick=()=>{if(!submitting)showMode('cadastro');};
  get('access-login').onclick=()=>{if(!submitting)showMode('entrar');};
  for(const [id,message] of [['access-email','Informe um e-mail que você usa para o trabalho. Ele identifica sua conta e os convites recebidos.'],['access-password','Escolha uma senha de pelo menos 10 caracteres. Não use a senha do tribunal; este acesso pertence somente ao Caderno Âmbar.']]){
    get(id).onfocus=()=>{get('access-guidance').textContent=message;};
  }
  get('access-form').onsubmit=async event=>{
    event.preventDefault();if(submitting)return;
    submitting=true;get('access-submit').disabled=true;get('access-status').hidden=false;
    get('access-status').textContent=mode==='cadastro'?'Criando seu acesso…':'Verificando seu acesso…';
    try{
      const r=await fetch('/api/conta/'+(mode==='entrar'?'login':'cadastro'),{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({email:get('access-email').value,senha:get('access-password').value}),signal:AbortSignal.timeout(20000)
      });
      if(!r.headers.get('content-type')?.includes('application/json'))throw Error('O acesso precisa do servidor da aplicação. Abra a versão local na porta 8093.');
      const data=await r.json();if(!r.ok)throw Error(data.error||'Não foi possível entrar.');
      get('access-password').value='';
      location.assign('acompanhamento.html'+(get('access-guided').checked?'?guia=1':''));
    }catch(error){get('access-status').textContent=error.message;get('access-status').dataset.kind='error';}
    finally{submitting=false;get('access-submit').disabled=false;}
  };
  showMode(mode);
})();
