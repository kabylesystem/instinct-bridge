// Independent test-only encoder using Node/OpenSSL, never real accounts.
// Requires Node >=24.7 (crypto.argon2Sync). Fixed IVs are ONLY for synthetic fixtures.
import {pbkdf2Sync, argon2Sync, createHash, createHmac, createCipheriv} from 'node:crypto';
import {writeFileSync} from 'node:fs';
const root = new URL('../tests/fixtures/', import.meta.url);
const password='SYNTHETIC-export-password';
const data={encrypted:false,items:[{id:'00000000-0000-4000-8000-000000000002',type:1,name:'Instinct Bridge encrypted TEST',login:{username:'bridge@example.invalid',password:'SYNTHETIC-account-password'}}]};
const b64=x=>x.toString('base64');
const hmac=(key,x)=>createHmac('sha256',key).update(x).digest();
function encrypt(text,key,iv){const c=createCipheriv('aes-256-cbc',key,iv);return Buffer.concat([c.update(text),c.final()]);}
for(const type of [0,1]){
 const salt=b64(Buffer.from('SYNTHETIC-salt-32-bytes-0000000000'));
 const key=type===0?pbkdf2Sync(password,salt,600000,32,'sha256'):argon2Sync('argon2id',{message:password,nonce:createHash('sha256').update(salt).digest(),parallelism:4,tagLength:32,memory:65536,passes:3});
 const enc=hmac(key,Buffer.from('enc\x01')), mac=hmac(key,Buffer.from('mac\x01'));
 const seal=text=>{const iv=Buffer.alloc(16,7);const ct=encrypt(text,enc,iv);return '2.'+[iv,ct,hmac(mac,Buffer.concat([iv,ct]))].map(b64).join('|');};
 const out={encrypted:true,passwordProtected:true,salt,kdfType:type,kdfIterations:type===0?600000:3,...(type?{kdfMemory:64,kdfParallelism:4}:{}),encKeyValidation_DO_NOT_EDIT:seal('00000000-0000-4000-8000-000000000001'),data:seal(JSON.stringify(data))};
 writeFileSync(new URL(`bitwarden-${type?'argon2':'pbkdf2'}-synthetic.json`,root),JSON.stringify(out,null,2)+'\n');
}
for(const zero of [false,true]){
 const iv=Buffer.alloc(16,zero?0:9),salt='SYNTHETIC-authy-salt';
 const out={authenticator_tokens:[{unique_id:'synthetic-authy-1',name:'bridge@example.invalid',issuer:data.items[0].name,digits:6,salt,key_derivation_iterations:100000,unique_iv:zero?'':iv.toString('hex'),encrypted_seed:b64(encrypt('GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ',pbkdf2Sync(password,salt,100000,32,'sha1'),iv))}]};
 writeFileSync(new URL(`authy-${zero?'zero-iv':'encrypted'}-synthetic.json`,root),JSON.stringify(out,null,2)+'\n');
}
