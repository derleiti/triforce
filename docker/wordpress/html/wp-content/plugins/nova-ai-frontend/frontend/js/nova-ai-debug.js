/**
 * Nova AI v3.2 - DEBUG VERSION
 * Extensive logging for troubleshooting model loading issues
 */
(function(){
'use strict';

// ========== DEBUG LOGGING SYSTEM ==========
const DEBUG = {
    enabled: true,
    prefix: '[Nova Debug]',
    
    log(...args) {
        if (!this.enabled) return;
        console.log(this.prefix, ...args);
    },
    
    warn(...args) {
        if (!this.enabled) return;
        console.warn(this.prefix + ' ⚠️', ...args);
    },
    
    error(...args) {
        console.error(this.prefix + ' ❌', ...args);
    },
    
    group(label) {
        if (!this.enabled) return;
        console.group(this.prefix + ' ' + label);
    },
    
    groupEnd() {
        if (!this.enabled) return;
        console.groupEnd();
    },
    
    table(data) {
        if (!this.enabled) return;
        console.table(data);
    },
    
    panel: null,
    
    initPanel() {
        if (this.panel) return;
        this.panel = document.createElement('div');
        this.panel.id = 'nova-debug-panel';
        this.panel.style.cssText = 'position:fixed;bottom:10px;right:10px;width:400px;max-height:300px;overflow-y:auto;background:#1a1a2e;border:2px solid #00ff9d;border-radius:8px;padding:10px;font-family:monospace;font-size:11px;color:#00ff9d;z-index:99999;box-shadow:0 4px 20px rgba(0,255,157,0.3);';
        this.panel.innerHTML = '<div style="display:flex;justify-content:space-between;margin-bottom:8px;border-bottom:1px solid #333;padding-bottom:5px;"><strong>🔍 Nova Debug Panel</strong><button onclick="this.parentElement.parentElement.remove()" style="background:#ff4757;color:#fff;border:none;border-radius:3px;padding:2px 8px;cursor:pointer;">×</button></div><div id="nova-debug-log"></div>';
        document.body.appendChild(this.panel);
    },
    
    addToPanel(type, msg) {
        if (!this.panel) this.initPanel();
        const log = document.getElementById('nova-debug-log');
        if (!log) return;
        const colors = {info:'#00ff9d',warn:'#ffc048',error:'#ff4757',success:'#2ed573'};
        const entry = document.createElement('div');
        entry.style.cssText = 'margin:3px 0;padding:3px;border-left:3px solid '+(colors[type]||colors.info)+';padding-left:8px;';
        entry.innerHTML = '<span style="color:#888">['+new Date().toLocaleTimeString()+']</span> '+msg;
        log.appendChild(entry);
        log.scrollTop = log.scrollHeight;
    }
};

const $=s=>document.querySelector(s),$$=s=>document.querySelectorAll(s);
const ajax=window.novAiConfig?.ajaxUrl||'/wp-admin/admin-ajax.php';

DEBUG.log('🚀 Nova AI Debug Version Loaded');
DEBUG.log('Ajax URL:', ajax);

const md=t=>{if(!t)return'';let h=t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');h=h.replace(/```(\w*)\n?([\s\S]*?)```/g,(_,l,c)=>{const id='c'+Math.random().toString(36).substr(2,6);return'<div class="nova-code"><div class="nova-code-h"><span>'+(l||'code')+'</span><button onclick="NovAI.copy(\''+id+'\')">Copy</button></div><pre id="'+id+'"><code>'+c.trim()+'</code></pre></div>';});h=h.replace(/`([^`]+)`/g,'<code>$1</code>');h=h.replace(/^### (.+)$/gm,'<h4>$1</h4>').replace(/^## (.+)$/gm,'<h3>$1</h3>').replace(/^# (.+)$/gm,'<h2>$1</h2>');h=h.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/\*([^*]+)\*/g,'<em>$1</em>');h=h.replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2" target="_blank">$1</a>');h=h.replace(/^[\-\*] (.+)$/gm,'<li>$1</li>').replace(/(<li>.*<\/li>\n?)+/g,m=>'<ul>'+m+'</ul>');h=h.replace(/\n\n+/g,'</p><p>');return'<p>'+h+'</p>';};
const esc=t=>{const d=document.createElement('div');d.textContent=t;return d.innerHTML};

const loadChoices=()=>new Promise((resolve, reject)=>{
    DEBUG.group('📦 Loading Choices.js');
    if(window.Choices){DEBUG.log('✅ Already loaded');DEBUG.groupEnd();return resolve();}
    const css=document.createElement('link');css.rel='stylesheet';css.href='https://cdn.jsdelivr.net/npm/choices.js@10.2.0/public/assets/styles/choices.min.css';css.onload=()=>DEBUG.log('✅ CSS loaded');css.onerror=e=>DEBUG.error('❌ CSS failed:',e);document.head.appendChild(css);
    const js=document.createElement('script');js.src='https://cdn.jsdelivr.net/npm/choices.js@10.2.0/public/assets/scripts/choices.min.js';js.onload=()=>{DEBUG.log('✅ JS loaded');DEBUG.groupEnd();resolve();};js.onerror=e=>{DEBUG.error('❌ JS failed:',e);DEBUG.groupEnd();reject(e);};document.head.appendChild(js);
});

function initTabs(){DEBUG.log('🔧 Tabs init');$$('.nova-tab').forEach(tab=>{tab.onclick=()=>{$$('.nova-tab').forEach(t=>t.classList.remove('on'));$$('.nova-box').forEach(b=>b.classList.remove('on'));tab.classList.add('on');$('#'+tab.dataset.t+'-box')?.classList.add('on');};});}

const Chat={
    log:null,input:null,sel:null,choices:null,history:[],busy:false,
    init(){DEBUG.group('💬 Chat.init()');this.log=$('#chat-log');this.input=$('#chat-in');this.sel=$('#nova-model');DEBUG.log('Elements:',{log:!!this.log,input:!!this.input,sel:!!this.sel});$('#chat-send')?.addEventListener('click',()=>this.send());$('#nova-new')?.addEventListener('click',()=>this.reset());this.input?.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();this.send()}});this.input?.addEventListener('input',()=>{this.input.style.height='auto';this.input.style.height=Math.min(this.input.scrollHeight,120)+'px';});DEBUG.groupEnd();this.loadModels();},
    async loadModels(){
        DEBUG.group('📋 loadModels()');DEBUG.addToPanel('info','Starting model load...');
        if(!this.sel){DEBUG.error('Select not found!');DEBUG.addToPanel('error','#nova-model missing');DEBUG.groupEnd();return;}
        try{
            DEBUG.log('Step 1: Choices.js');DEBUG.addToPanel('info','Loading Choices.js...');await loadChoices();DEBUG.addToPanel('success','Choices.js OK');
            const url=ajax+'?action=nov_ai_models';DEBUG.log('Step 2: Fetch',url);DEBUG.addToPanel('info','Fetching models...');
            const t0=performance.now();const res=await fetch(url);const ms=(performance.now()-t0).toFixed(0);
            DEBUG.log('Status:',res.status,res.statusText,'in',ms+'ms');DEBUG.addToPanel('info','HTTP '+res.status+' ('+ms+'ms)');
            if(!res.ok)throw new Error('HTTP '+res.status);
            const raw=await res.text();DEBUG.log('Response length:',raw.length);DEBUG.log('Preview:',raw.substring(0,300));
            let data;try{data=JSON.parse(raw);}catch(pe){DEBUG.error('Parse error:',pe);DEBUG.error('Raw:',raw.substring(0,500));DEBUG.addToPanel('error','JSON parse fail');throw pe;}
            DEBUG.log('Keys:',Object.keys(data));DEBUG.log('models type:',typeof data.models,'isArray:',Array.isArray(data.models),'length:',data.models?.length);
            if(!data.models){DEBUG.error('No models key!');DEBUG.log('Full data:',data);DEBUG.addToPanel('error','No models in response');throw new Error('No models');}
            if(!Array.isArray(data.models)){DEBUG.error('Not array!');throw new Error('models not array');}
            if(!data.models.length){DEBUG.warn('Empty array!');throw new Error('Empty models');}
            DEBUG.addToPanel('success','Got '+data.models.length+' models');
            const g={};data.models.forEach(m=>{const p=m.provider||'Other';if(!g[p])g[p]=[];g[p].push(m);});
            DEBUG.log('Providers:',Object.keys(g));DEBUG.table(Object.entries(g).map(([k,v])=>({provider:k,count:v.length})));
            const c=Object.keys(g).sort().map(p=>({label:p+' ('+g[p].length+')',id:p,choices:g[p].map(m=>({value:m.id,label:m.name,selected:m.id==='groq/llama-3.3-70b-versatile'}))}));
            if(this.choices)this.choices.destroy();
            this.choices=new Choices(this.sel,{searchEnabled:true,searchPlaceholderValue:'Search '+data.models.length+' models...',itemSelectText:'',shouldSort:false,searchResultLimit:50});
            this.choices.setChoices(c,'value','label',true);
            DEBUG.log('✅ Models ready!');DEBUG.addToPanel('success','✅ '+data.models.length+' models loaded');
        }catch(e){DEBUG.error('loadModels FAILED:',e);DEBUG.addToPanel('error','FAIL: '+e.message);this.sel.innerHTML='<option value="groq/llama-3.3-70b-versatile">Llama 3.3 70B (Fallback)</option>';}
        DEBUG.groupEnd();
    },
    model(){return this.choices?.getValue(true)||this.sel?.value||'groq/llama-3.3-70b-versatile'},
    reset(){this.history=[];if(this.log)this.log.innerHTML='';},
    async send(){const msg=this.input?.value.trim();if(!msg||this.busy)return;this.busy=true;this.input.value='';this.input.style.height='auto';this.add(msg,'user');this.history.push({role:'user',content:msg});const ld=this.loading();try{const res=await fetch(ajax+'?action=nov_ai_chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:this.model(),messages:this.history,temperature:0.7,max_tokens:8192})});const d=await res.json();const r=d.content||d.response||d.data?.content||'No response';this.history.push({role:'assistant',content:r});ld?.remove();this.add(r,'ai');}catch(e){ld?.remove();this.add('Error: '+e.message,'ai');}this.busy=false;this.input?.focus();},
    add(txt,role){const d=document.createElement('div');d.className='nova-msg '+role;d.innerHTML='<div class="nova-av">'+(role==='user'?'👤':'✨')+'</div><div class="nova-txt">'+(role==='user'?esc(txt):md(txt))+'</div>';this.log?.appendChild(d);this.log.scrollTop=this.log.scrollHeight;},
    loading(){const d=document.createElement('div');d.className='nova-msg ai';d.innerHTML='<div class="nova-av">✨</div><div class="nova-dots"><span></span><span></span><span></span></div>';this.log?.appendChild(d);this.log.scrollTop=this.log.scrollHeight;return d;}
};

const Vision={log:null,file:null,url:null,b64:null,busy:false,init(){DEBUG.log('👁️ Vision.init()');this.log=$('#vision-log');$('#vision-file')?.addEventListener('change',e=>{if(e.target.files[0])this.handleFile(e.target.files[0])});$('#vision-url')?.addEventListener('keydown',e=>{if(e.key==='Enter')this.loadUrl()});$('#vision-url')?.addEventListener('blur',()=>{if($('#vision-url').value.trim())this.loadUrl()});$('#vision-go')?.addEventListener('click',()=>this.analyze());this.loadModels();},async loadModels(){const sel=$('#vision-model');if(!sel)return;try{const res=await fetch(ajax+'?action=nov_ai_models');const data=await res.json();const kw=['vision','flash','pro','gpt-4o','claude-3','gemini-2','gemini-1.5','pixtral','llava'];const models=data.models?.filter(m=>kw.some(k=>m.id.toLowerCase().includes(k)))||[];DEBUG.log('Vision models:',models.length);const g={};models.forEach(m=>{const p=m.provider||'Other';if(!g[p])g[p]=[];g[p].push(m);});sel.innerHTML='';Object.keys(g).sort().forEach(p=>{const og=document.createElement('optgroup');og.label=p;g[p].forEach(m=>{const o=document.createElement('option');o.value=m.id;o.textContent=m.name;if(m.id==='gemini/gemini-2.0-flash')o.selected=true;og.appendChild(o);});sel.appendChild(og);});}catch(e){DEBUG.error('Vision loadModels:',e);}},handleFile(f){if(f.size>20*1024*1024)return alert('Max 20MB');this.file=f;this.url=null;const r=new FileReader();r.onload=e=>{this.b64=e.target.result;this.preview(e.target.result)};r.readAsDataURL(f);},loadUrl(){const u=$('#vision-url')?.value.trim();if(!u)return;this.url=u;this.file=null;this.b64=null;this.preview(u);},preview(src){const p=$('#vision-preview');if(p)p.innerHTML='<div style="position:relative;display:inline-block"><img src="'+src+'"><button class="rm" onclick="NovAI.clearVision()">×</button></div>';},clear(){this.file=null;this.url=null;this.b64=null;const p=$('#vision-preview');if(p)p.innerHTML='';const u=$('#vision-url');if(u)u.value='';},add(role,txt,img,model){const d=document.createElement('div');d.className='nova-msg '+role;let h='<div class="nova-av">'+(role==='user'?'👤':'✨')+'</div><div class="nova-txt">';if(model)h+='<div class="nova-model">'+model+'</div>';if(img)h+='<img class="nova-img" src="'+img+'">';h+='<div>'+(role==='user'?esc(txt):md(txt))+'</div></div>';d.innerHTML=h;this.log?.appendChild(d);this.log.scrollTop=this.log.scrollHeight;},async analyze(){if(this.busy||(!this.file&&!this.url))return alert('Upload or paste image URL first');const model=$('#vision-model')?.value||'gemini/gemini-2.0-flash';const prompt=$('#vision-prompt')?.value||'Describe this image.';const btn=$('#vision-go');this.busy=true;if(btn){btn.disabled=true;btn.textContent='Analyzing...';}this.add('user',prompt,this.b64||this.url);const ld=document.createElement('div');ld.className='nova-msg ai';ld.innerHTML='<div class="nova-av">✨</div><div class="nova-dots"><span></span><span></span><span></span></div>';this.log?.appendChild(ld);try{let res;if(this.file){const fd=new FormData();fd.append('model',model);fd.append('prompt',prompt);fd.append('image_file',this.file);res=await fetch(ajax+'?action=nov_ai_vision_upload',{method:'POST',body:fd});}else{res=await fetch(ajax+'?action=nov_ai_vision_url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model,prompt,image_url:this.url})});}const d=await res.json();ld.remove();const txt=d.text||d.content||d.response||d.error||'No response';this.add('ai',txt,null,model);}catch(e){ld.remove();this.add('ai','Error: '+e.message,null,model);}this.busy=false;if(btn){btn.disabled=false;btn.textContent='Analyze';}}};

const Discuss={overlay:null,chat:null,input:null,sel:null,choices:null,history:[],ctx:'',init(){DEBUG.log('💭 Discuss.init()');this.overlay=$('#nov-discuss-overlay');if(!this.overlay)return;this.chat=$('#nov-discuss-chat');this.input=$('#nov-discuss-input');this.sel=$('#nov-discuss-model');$('#nov-discuss-close')?.addEventListener('click',()=>this.close());$('#nov-discuss-send')?.addEventListener('click',()=>this.send());this.input?.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();this.send();}});document.addEventListener('keydown',e=>{if(e.key==='Escape')this.close();});$$('.nov-discuss-btn').forEach(b=>b.addEventListener('click',e=>{e.preventDefault();this.open();}));this.loadModels();},async loadModels(){if(!this.sel)return;try{await loadChoices();const res=await fetch(ajax+'?action=nov_ai_models');const data=await res.json();if(!data.models?.length)return;const g={};data.models.forEach(m=>{const p=m.provider||'Other';if(!g[p])g[p]=[];g[p].push(m);});const c=Object.keys(g).sort().map(p=>({label:p,id:p,choices:g[p].map(m=>({value:m.id,label:m.name,selected:m.id==='groq/llama-3.3-70b-versatile'}))}));if(this.choices)this.choices.destroy();this.choices=new Choices(this.sel,{searchEnabled:true,itemSelectText:'',shouldSort:false});this.choices.setChoices(c,'value','label',true);}catch(e){DEBUG.error('Discuss loadModels:',e);}},open(){const c=$('.entry-content, .post-content, article, main');if(c)this.ctx=c.innerText.substring(0,6000);this.overlay.classList.add('active');document.body.style.overflow='hidden';this.input?.focus();},close(){this.overlay.classList.remove('active');document.body.style.overflow='';},async send(){const msg=this.input?.value.trim();if(!msg)return;this.input.value='';this.add(msg,'user');const messages=[];if(this.ctx&&!this.history.length)messages.push({role:'system',content:'Context:\n'+this.ctx});this.history.forEach(m=>messages.push(m));messages.push({role:'user',content:msg});this.history.push({role:'user',content:msg});const ld=document.createElement('div');ld.className='nova-msg ai';ld.innerHTML='<div class="nova-av">✨</div><div class="nova-dots"><span></span><span></span><span></span></div>';this.chat?.appendChild(ld);try{const res=await fetch(ajax+'?action=nov_ai_chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:this.choices?.getValue(true)||'groq/llama-3.3-70b-versatile',messages,temperature:0.7,max_tokens:4096})});const d=await res.json();const r=d.content||d.data?.content||'No response';this.history.push({role:'assistant',content:r});ld.remove();this.add(r,'ai');}catch(e){ld.remove();this.add('Error: '+e.message,'ai');}},add(txt,role){const d=document.createElement('div');d.className='nova-msg '+role;d.innerHTML='<div class="nova-av">'+(role==='user'?'👤':'✨')+'</div><div class="nova-txt">'+(role==='user'?esc(txt):md(txt))+'</div>';this.chat?.appendChild(d);this.chat.scrollTop=this.chat.scrollHeight;}};

const Downloads={el:null,init(){DEBUG.log('📥 Downloads.init()');this.el=$('.nov-downloads');if(!this.el)return;this.el.addEventListener('click',e=>{const f=e.target.closest('.nov-item.is-folder');if(f){e.preventDefault();this.nav(f.dataset.path);}const c=e.target.closest('.nov-crumb a');if(c){e.preventDefault();this.nav(c.dataset.path);}});},async nav(path){const list=this.el.querySelector('.nov-list');list.innerHTML='<li class="nov-item">Loading...</li>';try{const fd=new FormData();fd.append('action','nov_ai_browse');fd.append('path',path);const res=await fetch(ajax,{method:'POST',body:fd});const d=await res.json();if(d.success)this.render(d.data);}catch(e){list.innerHTML='<li class="nov-item">Error</li>';}},render(d){const list=this.el.querySelector('.nov-list');if(!d.files?.length){list.innerHTML='<li class="nov-item">Empty</li>';return;}list.innerHTML=d.files.map(f=>'<li class="nov-item '+(f.type==='folder'?'is-folder':'')+'" data-path="'+f.path+'"><span class="nov-icon">'+f.icon+'</span><span class="nov-name">'+(f.type==='folder'?f.name:'<a href="'+f.url+'" download>'+f.name+'</a>')+'</span><span class="nov-size">'+f.size+'</span></li>').join('');}};

window.NovAI={copy(id){const el=document.getElementById(id);if(el)navigator.clipboard.writeText(el.textContent).then(()=>{const btn=el.closest('.nova-code')?.querySelector('button');if(btn){btn.textContent='Copied!';setTimeout(()=>btn.textContent='Copy',2000);}});},clearVision:()=>Vision.clear(),openDiscuss:()=>Discuss.open(),closeDiscuss:()=>Discuss.close(),debug:DEBUG,reloadModels:()=>Chat.loadModels(),testApi:async()=>{DEBUG.group('🧪 API Test');try{const res=await fetch(ajax+'?action=nov_ai_models');const text=await res.text();DEBUG.log('Status:',res.status);DEBUG.log('Response:',text.substring(0,2000));DEBUG.addToPanel('info','API test done - see console');}catch(e){DEBUG.error('Test failed:',e);}DEBUG.groupEnd();}};

function init(){DEBUG.group('🎬 Nova AI Init');DEBUG.initPanel();DEBUG.addToPanel('info','Nova Debug v3.2 starting...');initTabs();Chat.init();Vision.init();Discuss.init();Downloads.init();DEBUG.log('✅ All modules init');DEBUG.addToPanel('success','Init complete');DEBUG.groupEnd();}
document.readyState==='loading'?document.addEventListener('DOMContentLoaded',init):init();
})();
