/* Explicit staging build only. Never modifies repository root or live data. */
const fs=require('fs'),path=require('path'),crypto=require('crypto'),cp=require('child_process');
const root=path.resolve(__dirname,'..'),src=path.join(root,'prototypes/field-edition');
const args=process.argv.slice(2),release=args.includes('--release'),positions=args.filter(x=>x!=='--release');
const target=positions[0];if(!target)throw Error('Provide a new staging directory');const out=path.resolve(target);
if(fs.existsSync(out))throw Error('Refusing to overwrite an existing directory');
if(out===root||root.startsWith(out+path.sep))throw Error('Invalid output');
cp.execFileSync('python3',['-I',path.join(root,'tools/check_public.py')],{cwd:root,stdio:'inherit'});
cp.execFileSync('python3',['-I',path.join(root,'tools/validate_feed.py'),'-q'],{cwd:root,stdio:'inherit'});
fs.mkdirSync(out,{recursive:true});
for(const name of ['style.css','app.js','canonical.js','migration.js','retention.js','document-health.js','positions.json','documents.json',...['en','pt','es','fr','ru','zh','ar'].map(l=>'explore-'+l+'.json')])fs.copyFileSync(path.join(src,name),path.join(out,name));
let html=fs.readFileSync(path.join(src,'live-preview.html'),'utf8');fs.writeFileSync(path.join(out,'index.html'),html);
fs.copyFileSync(path.join(root,'index.html'),path.join(out,'classic.html'));
cp.execFileSync(process.execPath,[path.join(src,'build-migration.cjs')],{cwd:root,env:{...process.env,COP31_REFERENCE_SOURCE:path.join(root,'index.html'),COP31_REFERENCE_OUTPUT:out},stdio:'inherit'});
fs.writeFileSync(path.join(out,'live-config.js'),'window.COP31_DATA={briefing:"data/briefing.json",pulse:"data/feed.json",feed:"data/feed.json",today:"data/today.json"};\nwindow.COP31_CLASSIC="classic.html";\n');
if(release)fs.appendFileSync(path.join(out,'live-config.js'),'window.COP31_RELEASE=true;\n');
fs.mkdirSync(path.join(out,'data'));for(const f of ['feed.json','briefing.json','today.json','pulse.json','newsletter.json'])fs.copyFileSync(path.join(root,'data',f),path.join(out,'data',f));
// Optional dedicated PUBLIC projection. Reject private checkpoint/raw metadata shapes.
const docInput=positions[1]||path.join(root,'data/negotiating-texts.json');
if(fs.existsSync(docInput)){
 const d=JSON.parse(fs.readFileSync(docInput,'utf8'));
 const top=new Set(['schema','documents','changes','checked_at','last_success','last_attempt','degraded','sources','history_count','error','verification_mode']);
 const fields=new Set(['id','title','body','session','agenda','document_code','published_at','modified_at','metadata_version','status','withdrawn','attachments','topic','source_url']);
 const official=u=>{try{const v=new URL(u);return v.protocol==='https:'&&['docs.unfccc.int','unfccc.int'].includes(v.hostname)&&!v.username&&!v.password&&(!v.port||v.port==='443')}catch{return false}};
 if(d.schema!==1||!Array.isArray(d.documents)||!Array.isArray(d.changes)||Object.keys(d).some(k=>!top.has(k)))throw Error('Not a public document projection');
 for(const r of d.documents){if(Object.keys(r).some(k=>!fields.has(k))||!r.id||!r.title||!Array.isArray(r.attachments)||!official(r.source_url)||r.attachments.some(a=>Object.keys(a).some(k=>!['url','sha256','language'].includes(k))||!official(a.url)))throw Error('Unsafe document projection')}
 fs.copyFileSync(docInput,path.join(out,'data/negotiating-texts.json'));
 fs.appendFileSync(path.join(out,'live-config.js'),'window.COP31_DATA.documents="data/negotiating-texts.json";\n');
}
for(const folder of ['i18n','data/articles'])if(fs.existsSync(path.join(root,folder)))fs.cpSync(path.join(root,folder),path.join(out,folder),{recursive:true});
for(const f of ['CNAME','LICENSE'])if(fs.existsSync(path.join(root,f)))fs.copyFileSync(path.join(root,f),path.join(out,f));
const sha=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
fs.writeFileSync(path.join(out,'build-manifest.json'),JSON.stringify({source_commit:cp.execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),source_tree_dirty:!!cp.execFileSync('git',['status','--porcelain','--untracked-files=no'],{cwd:root,encoding:'utf8'}).trim(),built_at:new Date().toISOString(),classic_sha256:sha(path.join(out,'classic.html')),feed_sha256:sha(path.join(out,'data/feed.json')),document_mode:fs.existsSync(docInput)?'public DACS projection':'saved catalog; collector not connected',scheduler_status:'not certified by build',artifact_mode:release?'release':'preview',deployment_status:'not asserted by build',workflow_run:process.env.GITHUB_RUN_ID||null},null,2));
console.log('Staged (not deployed): '+out);
