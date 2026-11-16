/* Explicit staging build only. Never modifies repository root or live data. */
const fs=require('fs'),path=require('path'),crypto=require('crypto'),cp=require('child_process');
const root=path.resolve(__dirname,'..'),src=path.join(root,'prototypes/field-edition');
const target=process.argv[2];if(!target)throw Error('Provide a new staging directory');const out=path.resolve(target);
if(fs.existsSync(out))throw Error('Refusing to overwrite an existing directory');
if(out===root||root.startsWith(out+path.sep))throw Error('Invalid output');
cp.execFileSync('python3',['-I',path.join(root,'tools/check_public.py')],{cwd:root,stdio:'inherit'});
cp.execFileSync('python3',['-I',path.join(root,'tools/validate_feed.py'),'-q'],{cwd:root,stdio:'inherit'});
fs.mkdirSync(out,{recursive:true});
for(const name of ['style.css','app.js','canonical.js','migration.js','retention.js','document-health.js','positions.json','documents.json',...['en','pt','es','fr','ru','zh','ar'].map(l=>'explore-'+l+'.json')])fs.copyFileSync(path.join(src,name),path.join(out,name));
let html=fs.readFileSync(path.join(src,'live-preview.html'),'utf8');fs.writeFileSync(path.join(out,'index.html'),html);
fs.copyFileSync(path.join(root,'index.html'),path.join(out,'classic.html'));
fs.writeFileSync(path.join(out,'live-config.js'),'window.COP31_DATA={briefing:"data/briefing.json",pulse:"data/feed.json",feed:"data/feed.json",today:"data/today.json"};\nwindow.COP31_CLASSIC="classic.html";\n');
fs.mkdirSync(path.join(out,'data'));for(const f of ['feed.json','briefing.json','today.json','pulse.json','newsletter.json'])fs.copyFileSync(path.join(root,'data',f),path.join(out,'data',f));
for(const folder of ['i18n','data/articles'])if(fs.existsSync(path.join(root,folder)))fs.cpSync(path.join(root,folder),path.join(out,folder),{recursive:true});
for(const f of ['CNAME','LICENSE'])if(fs.existsSync(path.join(root,f)))fs.copyFileSync(path.join(root,f),path.join(out,f));
const sha=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
fs.writeFileSync(path.join(out,'build-manifest.json'),JSON.stringify({source_commit:cp.execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),built_at:new Date().toISOString(),classic_sha256:sha(path.join(out,'classic.html')),feed_sha256:sha(path.join(out,'data/feed.json')),document_mode:'saved catalog; collector not connected',deployment:'NOT DEPLOYED'},null,2));
console.log('Staged (not deployed): '+out);
