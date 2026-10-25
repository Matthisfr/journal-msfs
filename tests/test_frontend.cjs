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
  assert.match(fs.readFileSync(path.join(root,'public/app.js'),'utf8'),/airport_coordinates\.json/,'Carte interactive reliée aux coordonnées');
  assert.match(elem('#airport-count').textContent,new RegExp('\\b'+airports.length+' scènes\\b'));
  console.log('OK :',rows,'scènes et carte interactive configurée.');
},100);
