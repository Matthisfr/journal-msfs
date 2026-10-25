'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const airports=JSON.parse(fs.readFileSync(path.join(root,'public/airports.json'),'utf8'));
const status=JSON.parse(fs.readFileSync(path.join(root,'public/status.json'),'utf8'));
const editorial=JSON.parse(fs.readFileSync(path.join(root,'public/editorial.json'),'utf8'));
const elements=new Map();
function elem(id){if(!elements.has(id))elements.set(id,{id,value:'',textContent:'',innerHTML:'',dataset:{},classList:{toggle(){},add(){},remove(){}},setAttribute(){},removeAttribute(){},addEventListener(){}});return elements.get(id)}
const document={
  querySelector:selector=>elem(selector),
  querySelectorAll:()=>[],
  getElementById:id=>elem('#'+id)
};
const context={
  document,window:{scrollTo(){}},history:{replaceState(){}},
  location:{hash:'#aeroports'},URL,Date,Intl,console,setTimeout,clearTimeout,
  fetch:async name=>({ok:true,json:async()=>name.includes('airports')?airports:name.includes('status')?status:editorial})
};
vm.runInNewContext(fs.readFileSync(path.join(root,'public/app.js'),'utf8'),context,{filename:'app.js'});
setTimeout(()=>{
  const html=elem('#airport-body').innerHTML;
  const rows=(html.match(/<tr>/g)||[]).length;
  assert.equal(rows,airports.length,'Toutes les scènes doivent être affichées');
  assert.match(elem('#google-map').innerHTML,/google\.com\/maps\/d\/embed/,'Carte intégrée');
  assert.match(elem('#airport-count').textContent,/171 scènes/);
  console.log('OK :',rows,'scènes et carte Google My Maps visibles.');
},100);
