'use strict';
const $ = id => document.getElementById(id);
const token = location.hash.slice(1);
history.replaceState(null, '', '/');
let preview = null, connected = false, busy = false, captureReady = false, captureTimer = null;

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
function mapping(){const result={};for(const el of document.querySelectorAll('.authy-select'))if(el.value!=='')result[el.dataset.id]=Number(el.value);return result;}
function update(){
  const paired=new Set(Object.values(mapping()));
  for(const a of preview?.accounts||[]){const cell=$('pair-'+a.index);if(cell)cell.textContent=a.has_totp?'Saved in Bitwarden':paired.has(a.index)?'Authy key paired':'Not paired';}
  const count=selected().length;$('selection-count').textContent=`${count} account${count===1?'':'s'} selected`;$('transfer').disabled=busy||!count||Boolean(preview?.demo);}
function render(data){
  preview=data;connected=false;$('review').hidden=false;$('sources').hidden=true;$('demo-label').hidden=!data.demo;$('account-rows').replaceChildren();$('authy-rows').replaceChildren();$('issue-list').replaceChildren();
  $('counts').textContent=`${noun(data.accounts.length,'account')} available · ${noun(data.report.source_items,'source item')} · ${noun(data.authy.length,'Authy key')}`;
  for(const a of data.accounts){
    const row=elem('tr');const check=elem('input');check.type='checkbox';check.className='account-select';check.value=a.index;check.checked=true;check.setAttribute('aria-label',`Select ${a.name}`);check.addEventListener('change',update);
    const cell=elem('td');cell.append(check);row.append(cell,elem('td',a.name,'account-name'),elem('td',a.username||'No username','username'),elem('td',a.has_totp?'Saved in Bitwarden':'Not paired','badge'));
    row.lastElementChild.id='pair-'+a.index;
    const status=elem('td','Not transferred','status');status.id='result-'+a.index;row.append(status);$('account-rows').append(row);
  }
  $('issues').hidden=!data.report.issues.length;
  for(const issue of data.report.issues.slice(0,30))$('issue-list').append(elem('li',`Source item ${issue.index+1}: ${issue.reason}`));
  if(data.report.issues.length>30)$('issue-list').append(elem('li',`${data.report.issues.length-30} more items need review. They remain in your source export.`));
  $('pairing').hidden=!data.authy.length;
  for(const a of data.authy){
    const row=elem('div',undefined,'authy-row');const name=elem('div',a.issuer||a.name);name.append(elem('small',a.name));const select=elem('select');select.className='authy-select';select.addEventListener('change',update);select.dataset.id=a.id;select.setAttribute('aria-label',`Pair Authy key ${a.name}`);select.append(new Option('Leave unpaired',''));
    for(const account of data.accounts)select.append(new Option(`${account.name} — ${account.username||'no username'}`,account.index));
    // One suggestion can be preselected, but the user reviews and confirms the complete transfer.
    if(a.suggestions.length===1)select.value=String(a.suggestions[0]);
    row.append(name,elem('span','→','arrow'),select);$('authy-rows').append(row);
  }
  $('allow-unmapped').checked=false;$('select-all').checked=true;$('connection-state').textContent=data.demo?'Sample data only. No connection or transfer is made.':'Uses your existing Instinct sign-in in Brave, through a separate background browser.';
  $('connect').disabled=data.demo;$('stage1').classList.remove('active');$('stage2').classList.add('active');$('stage3').classList.remove('active');update();
}
async function fileText(id, required){const file=$(id).files[0];if(!file){if(required)throw Error('Choose a Bitwarden export.');return '';}if(file.size>25*1024*1024)throw Error('Exports must be no larger than 25 MiB.');return file.text();}
$('load-form').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
  notice('Unlocking your exports locally…');
  const data=await api('preview',{bitwarden:await fileText('bitwarden-file',false),authy:await fileText('authy-file',false),bitwarden_password:$('bitwarden-password').value,authy_password:$('authy-password').value,use_capture:captureReady});
  render(data);captureReady=false;stopCapturePolling();$('iphone-panel').hidden=true;$('load-form').reset();notice('Exports unlocked. Review your accounts and Authy pairings.','success');
});});
$('demo').addEventListener('click',()=>action(async()=>{render(await api('demo'));$('load-form').reset();notice('Sample data loaded. This preview cannot send anything to Instinct.');}));
$('clear').addEventListener('click',()=>action(async()=>{const result=await api('clear');preview=null;connected=false;captureReady=false;stopCapturePolling();$('iphone-panel').hidden=true;$('review').hidden=true;$('sources').hidden=false;$('load-form').reset();$('account-rows').replaceChildren();$('authy-rows').replaceChildren();$('stage1').classList.add('active');$('stage2').classList.remove('active');$('stage3').classList.remove('active');notice('Loaded data has been released from the app. Your source files are unchanged.');}));
$('connect').addEventListener('click',()=>action(async()=>{notice('Checking your Instinct session in the background…');const result=await api('connect');connected=result.connected;$('connection-state').textContent=`Connected to your Instinct session in Brave. ${noun(result.entries,'existing vault entry','existing vault entries')}; conflicting accounts will be left unchanged.`;notice('Connected. Confirm the selected accounts before transferring.','success');}));
$('transfer').addEventListener('click',()=>action(async()=>{
  if(!connected){notice('Connecting to your Instinct session…');const connection=await api('connect');connected=connection.connected;}
  const selection=selected();notice(`Transferring and verifying ${selection.length} selected accounts…`);$('stage2').classList.remove('active');$('stage3').classList.add('active');
  const result=await api('transfer',{revision:preview.revision,selected:selection,mapping:mapping(),acknowledge_scope:true,acknowledge_unmapped:$('allow-unmapped').checked});
  const labels={created:'Transferred & verified',already_present:'Already present · verified',conflict:'Conflict · unchanged',uncertain:'Uncertain · check before retry',verification_failed:'Verification failed'};
  for(const row of result.results){$('result-'+row.index).textContent=labels[row.status]||row.status;$('result-'+row.index).classList.toggle('ready',row.verified);}
  notice(result.verified?`${noun(result.results.length,'selected account')} verified in Instinct.`:`Transfer stopped for review. ${result.not_attempted} selected accounts were not attempted.`,result.verified?'success':'error');
}));
$('select-all').addEventListener('change',()=>{for(const e of document.querySelectorAll('.account-select'))e.checked=$('select-all').checked;update();});

for(const [input,label,fallback] of [['bitwarden-file','bw-name','Password-protected exports supported'],['authy-file','authy-name','Encrypted token JSON or decrypted export']])$(input).addEventListener('change',()=>{$(label).textContent=$(input).files[0]?.name||fallback;});
if(!token)notice('Start instinct-bridge-ui, then open the private link printed in your terminal.','error');

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
  const result=await api('quit');stopCapturePolling();preview=null;connected=false;captureReady=false;
  $('load-form').reset();$('account-rows').replaceChildren();$('authy-rows').replaceChildren();
  $('sources').hidden=true;$('review').hidden=true;$('demo').disabled=true;$('quit').disabled=true;
  notice(result.phone_cleanup_required?'App closed. Turn the iPhone Wi-Fi proxy Off and remove its temporary Instinct Bridge profile.':'App closed. You can close this tab.','success');
}));
