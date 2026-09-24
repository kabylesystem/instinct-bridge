'use strict';
const $ = id => document.getElementById(id);
const token = location.hash.slice(1);
history.replaceState(null, '', '/');
let preview = null, connected = false, busy = false, captureReady = false, captureTimer = null, progressTimer = null, progressGeneration = 0, transferCompleted = false;

function noun(n, singular, plural=singular+'s'){return `${n} ${n===1?singular:plural}`;}
function notice(text, kind='') { $('notice').textContent=text; $('notice').className=kind; $('notice').hidden=false; }
async function api(path, data={}) {
  if (!token) throw Error('Open the private launch link printed by instinct-bridge-ui in your terminal.');
  const response = await fetch('/api/'+path, {method:'POST',headers:{'Content-Type':'application/json','X-Bridge-Token':token},body:JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw Error(result.error || 'The operation stopped.');
  return result;
}
async function action(work) {
  if(busy) return;
  busy=true; document.body.classList.add('busy'); document.body.setAttribute('aria-busy','true');
  try {await work();} catch(error) {notice(error.message,'error');}
  finally {busy=false;document.body.classList.remove('busy');document.body.removeAttribute('aria-busy');update();}
}
function elem(tag,text,className) {const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el;}
function selected(){return [...document.querySelectorAll('.account-select:checked')].map(e=>Number(e.value));}
function filterAccounts(){const query=$('account-search').value.trim().toLocaleLowerCase();let visible=0;for(const row of $('account-rows').children){row.hidden=Boolean(query)&&!row.dataset.search.includes(query);if(!row.hidden)visible++;}$('account-empty').hidden=visible>0;}
function mapping(){const result={};for(const el of document.querySelectorAll('.authy-select'))if(el.value!=='')result[el.dataset.id]=Number(el.value);return result;}
function update(){
  const paired=new Set(Object.values(mapping()));
  for(const a of preview?.accounts||[]){const cell=$('pair-'+a.index);if(cell)cell.textContent=a.has_totp?'Saved in Bitwarden':paired.has(a.index)?'Authy key paired':'Not paired';}
  const count=selected().length;$('selection-count').textContent=`${noun(count,'account')} selected`;
  $('select-all').checked=Boolean(preview?.accounts.length)&&count===preview.accounts.length;
  $('select-all').indeterminate=count>0&&count<(preview?.accounts.length||0);
  $('accounts-summary').textContent=preview?`${noun(preview.accounts.length,'login')} · ${count} selected`:'';
  $('transfer-label').textContent=transferCompleted?'Transfer complete':count?`Transfer ${noun(count,'account')}`:'Select accounts to transfer';
  $('transfer').disabled=busy||!count||Boolean(preview?.demo)||transferCompleted;
  $('preview').disabled=busy||!($('bitwarden-file').files.length||$('authy-file').files.length||captureReady);
}
function showProgress(data){
  $('transfer-progress').hidden=false;
  $('transfer-meter').max=Math.max(1,data.total||1);
  $('transfer-meter').value=data.done||0;
  $('transfer-progress-text').textContent=data.phase==='connecting'?'Connecting to Instinct…':
    `${data.done} / ${data.total} checked · ${noun(data.created,'new account')} · ${data.already_present} already present${data.conflict?` · ${noun(data.conflict,'conflict')}`:''}`;
}
function stopProgressPolling(){progressGeneration++;if(progressTimer)clearInterval(progressTimer);progressTimer=null;}
function render(data){
  preview=data;connected=false;transferCompleted=false;$('review').hidden=false;$('sources').hidden=true;$('demo-label').hidden=!data.demo;$('account-rows').replaceChildren();$('authy-rows').replaceChildren();$('issue-list').replaceChildren();
  $('accounts-details').open=data.accounts.length<=8;$('account-search').value='';$('account-empty').hidden=true;$('transfer-progress').hidden=true;stopProgressPolling();
  $('counts').textContent=`${noun(data.accounts.length,'login')} ready · ${data.report.with_password===undefined?'':noun(data.report.with_password,'password')+' · '}${noun(data.report.with_site,'site')} identified · ${noun(data.report.withheld,'item')} withheld · ${noun(data.authy.length,'Authy key')}`;
  for(const a of data.accounts){
    const row=elem('tr');row.dataset.search=`${a.name} ${a.site} ${a.username}`.toLocaleLowerCase();const check=elem('input');check.type='checkbox';check.className='account-select';check.value=a.index;check.checked=true;check.setAttribute('aria-label',`Select ${a.name}`);check.addEventListener('change',()=>{transferCompleted=false;update();});
    const cell=elem('td');cell.append(check);const account=elem('td',a.name,'account-name');account.title=`Instinct name: ${a.destination_name}`;
    if(a.has_password!==undefined)account.append(elem('small',a.has_password?'Password saved':'No password in export','password-state'));
    row.append(cell,account,elem('td',a.site||'—','site'),elem('td',a.username||'No username','username'),elem('td',a.has_totp?'Saved in Bitwarden':'Not paired','badge'));
    row.lastElementChild.id='pair-'+a.index;
    const status=elem('td','Not transferred','status');status.id='result-'+a.index;row.append(status);$('account-rows').append(row);
  }
  $('issues').hidden=!data.report.issues.length;
  if(data.report.partial)$('issue-list').append(elem('li',`${noun(data.report.partial,'login')} contain extra Bitwarden fields. Their credentials can move; extra fields remain in Bitwarden.`));
  const withheld=data.report.issues.filter(issue=>!issue.partial);
  for(const issue of withheld.slice(0,20))$('issue-list').append(elem('li',`Source item ${issue.index+1}: ${issue.reason}`));
  if(withheld.length>20)$('issue-list').append(elem('li',`${withheld.length-20} more source items were withheld.`));
  $('pairing').hidden=!data.authy.length;
  for(const a of data.authy){
    const row=elem('div',undefined,'authy-row');const name=elem('div',a.issuer||a.name);name.append(elem('small',a.name));const select=elem('select');select.className='authy-select';select.addEventListener('change',()=>{transferCompleted=false;update();});select.dataset.id=a.id;select.setAttribute('aria-label',`Pair Authy key ${a.name}`);select.append(new Option('Leave unpaired',''));
    for(const account of data.accounts)select.append(new Option(`${account.name} — ${account.username||'no username'}`,account.index));
    // One suggestion can be preselected, but the user reviews and confirms the complete transfer.
    if(a.suggestions.length===1)select.value=String(a.suggestions[0]);
    row.append(name,elem('span','→','arrow'),select);$('authy-rows').append(row);
  }
  $('allow-unmapped').checked=false;$('select-all').checked=true;$('connection-state').textContent=data.demo?'Sample data only. No connection or transfer is made.':'Sign in to Instinct in Brave first. The bridge connects automatically when you transfer.';
  $('stage1').classList.remove('active');$('stage2').classList.add('active');$('stage3').classList.remove('active');update();
}
async function fileText(id, required){const file=$(id).files[0];if(!file){if(required)throw Error('Choose a Bitwarden export.');return '';}if(file.size>25*1024*1024)throw Error('Exports must be no larger than 25 MiB.');return file.text();}
$('load-form').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
  notice('Unlocking your exports locally…');
  const data=await api('preview',{bitwarden:await fileText('bitwarden-file',false),authy:await fileText('authy-file',false),bitwarden_password:$('bitwarden-password').value,authy_password:$('authy-password').value,use_capture:captureReady});
  render(data);captureReady=false;stopCapturePolling();$('iphone-panel').hidden=true;$('load-form').reset();notice('Export ready. Check the summary, then transfer when you are ready.','success');
});});
$('demo').addEventListener('click',()=>action(async()=>{render(await api('demo'));$('load-form').reset();notice('Sample data loaded. This preview cannot send anything to Instinct.');}));
$('clear').addEventListener('click',()=>action(async()=>{await api('clear');preview=null;connected=false;captureReady=false;transferCompleted=false;stopCapturePolling();stopProgressPolling();$('iphone-panel').hidden=true;$('review').hidden=true;$('sources').hidden=false;$('load-form').reset();$('account-rows').replaceChildren();$('authy-rows').replaceChildren();$('stage1').classList.add('active');$('stage2').classList.remove('active');$('stage3').classList.remove('active');notice('Ready for another export. Your source file is unchanged.');}));
$('transfer').addEventListener('click',()=>action(async()=>{
  if(!connected){notice('Connecting to your Instinct session…');const connection=await api('connect');connected=connection.connected;$('connection-state').textContent='Connected to your Instinct vault.';}
  const selection=selected();notice(`Transferring and verifying ${selection.length} selected accounts…`);$('stage2').classList.remove('active');$('stage3').classList.add('active');
  showProgress({phase:'connecting',done:0,total:selection.length,created:0,already_present:0,conflict:0});
  const generation=++progressGeneration;
  progressTimer=setInterval(async()=>{try{const progress=await api('progress');if(generation===progressGeneration)showProgress(progress);}catch(_error){/* Transfer response handles errors. */}},1500);
  let result;
  try{result=await api('transfer',{revision:preview.revision,selected:selection,mapping:mapping(),acknowledge_scope:true,acknowledge_unmapped:$('allow-unmapped').checked});}
  finally{stopProgressPolling();}
  const labels={created:'Transferred & verified',already_present:'Already present · verified',conflict:'Conflict · unchanged',uncertain:'Uncertain · check before retry',verification_failed:'Verification failed'};
  for(const row of result.results){$('result-'+row.index).textContent=labels[row.status]||row.status;$('result-'+row.index).classList.toggle('ready',row.verified);}
  const conflicts=result.results.filter(row=>row.status==='conflict').length;
  showProgress({phase:'complete',done:result.results.length,total:selection.length,
    created:result.results.filter(row=>row.status==='created').length,
    already_present:result.results.filter(row=>row.status==='already_present').length,conflict:conflicts});
  if(!result.verified)$('accounts-details').open=true;
  if(result.verified)transferCompleted=true;
  notice(result.verified?`${noun(result.results.length,'account')} verified in Instinct.`:result.not_attempted?`Transfer stopped for review. ${result.not_attempted} selected accounts were not attempted.`:`Transfer finished. ${noun(conflicts,'conflict')} need review; other accounts were verified.`,result.verified?'success':'error');
}));
$('select-all').addEventListener('change',()=>{for(const e of document.querySelectorAll('.account-select'))e.checked=$('select-all').checked;transferCompleted=false;update();});
$('account-search').addEventListener('input',filterAccounts);

for(const [input,label,fallback] of [['bitwarden-file','bw-name','Password-protected exports supported'],['authy-file','authy-name','Encrypted token JSON or decrypted export']])$(input).addEventListener('change',()=>{$(label).textContent=$(input).files[0]?.name||fallback;update();});
if(!token)notice('Start instinct-bridge-ui, then open the private link printed in your terminal.','error');
update();

function stopCapturePolling(){if(captureTimer)clearInterval(captureTimer);captureTimer=null;}
function captureStatus(data){
  $('iphone-panel').hidden=false;
  $('iphone-state').textContent=data.error||(!data.active&&!data.count?'Capture ended. Remove the iPhone proxy and temporary certificate.':`${noun(data.count,'encrypted key')} received · ${data.tls_seen?'Authy connection verified':data.phone_paired?'Phone paired · complete trust and proxy setup':'Waiting for your iPhone'}`);
  $('iphone-qr').hidden=!data.qr;if(data.qr)$('iphone-qr').src=data.qr;
  $('iphone-address').textContent=data.active?`Proxy server: ${data.server} · Port: ${data.port}`:'';
  $('iphone-finish').disabled=!data.active||!data.count;
  if(!data.active)stopCapturePolling();
}
$('iphone-start').addEventListener('click',()=>action(async()=>{
  notice('Starting a temporary local capture. Your iPhone will ask you to approve certificate trust.');
  const data=await api('iphone/start',{acknowledge_capture:true});captureReady=false;
  $('iphone-cleanup').hidden=true;$('iphone-finish-row').hidden=false;
  captureStatus(data);stopCapturePolling();
  captureTimer=setInterval(async()=>{try{captureStatus(await api('iphone/status'));}catch(error){stopCapturePolling();notice(error.message,'error');}},2000);
}));
$('iphone-finish').addEventListener('click',()=>action(async()=>{
  const data=await api('iphone/finish',{expected_count:Number($('iphone-count').value)});
  captureReady=true;captureStatus(data);$('iphone-cleanup').hidden=false;$('iphone-finish-row').hidden=true;
  notice('Keys received. Turn the iPhone proxy Off, remove the temporary profile, then unlock your keys locally.','success');
}));
$('iphone-cancel').addEventListener('click',()=>action(async()=>{
  await api('iphone/discard');captureReady=false;stopCapturePolling();$('iphone-qr').hidden=true;$('iphone-finish-row').hidden=true;
  $('iphone-state').textContent='Capture stopped; received data cleared.';$('iphone-cleanup').hidden=false;
  notice('Turn the iPhone Wi-Fi proxy Off and remove the temporary Instinct Bridge profile.');
}));

$('quit').addEventListener('click',()=>action(async()=>{
  const result=await api('quit');stopCapturePolling();stopProgressPolling();preview=null;connected=false;captureReady=false;
  $('load-form').reset();$('account-rows').replaceChildren();$('authy-rows').replaceChildren();
  $('sources').hidden=true;$('review').hidden=true;$('demo').disabled=true;$('quit').disabled=true;
  notice(result.phone_cleanup_required?'App closed. Turn the iPhone Wi-Fi proxy Off and remove its temporary Instinct Bridge profile.':'App closed. You can close this tab.','success');
}));
