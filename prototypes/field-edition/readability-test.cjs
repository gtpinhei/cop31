const fs=require('fs'),assert=require('assert'),{execFileSync}=require('child_process'),{JSDOM}=require('../../tools/node_modules/jsdom'),{improve}=require('./readability.cjs');
for(const lang of ['en','pt','es','fr','ru','zh','ar']){
 const file='prototypes/field-edition/explore-'+lang+'.json',before=JSON.parse(execFileSync('git',['show','b046e85:'+file])),after=JSON.parse(fs.readFileSync(__dirname+'/explore-'+lang+'.json'));
 for(const key of Object.keys(before.sections)){
  const a=new JSDOM(before.sections[key]).window.document,b=new JSDOM(after.sections[key]).window.document;
  assert.equal(b.body.textContent,a.body.textContent,lang+'/'+key+' text changed');
  for(const selector of ['a','[id]'])assert.deepEqual([...b.querySelectorAll(selector)].map(n=>[n.id,n.getAttribute('href'),n.textContent]),[...a.querySelectorAll(selector)].map(n=>[n.id,n.getAttribute('href'),n.textContent]),lang+'/'+key+' anchors changed');
  if(key==='thinktanks'){
   assert.equal(b.querySelectorAll('.report-tests>li').length,3);
   assert.equal(b.querySelectorAll('.report-lede>p').length,5);
   improve(a,lang);assert.equal(a.body.innerHTML,b.body.innerHTML,'reproducible '+lang);
   const html=b.body.innerHTML;improve(b,lang);assert.equal(b.body.innerHTML,html,'idempotent '+lang);
  }
 }
}
console.log('PASS: 105 sections retain every character and link/anchor; 7 locales each have 3 editorial test bullets and 5 thematic paragraphs; reproducible and idempotent.');
