/* Carte météo des aéroports du Journal — observations réelles uniquement. */
(()=>{'use strict';
let map,layer,loading=false;
const $=id=>document.getElementById(id);
const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function conditions(a){
 const raw=String(a.raw||'').toUpperCase().split(/\s+RMK\b/)[0];
 const tokens=raw.split(/\s+/);
 const has=re=>tokens.some(t=>re.test(t));
 const storm=has(/^(\+|-)?(VC)?TS/),snow=has(/^(\+|-)?(VC)?(SH|BL|DR|FZ)?SN|^RASN/);
 const rain=has(/^(\+|-)?(VC)?(SH|FZ)?RA|^(\+|-)?DZ|^RASN/);
 const fog=has(/^(\+|-)?(VC)?(FZ)?FG$/),mist=has(/^BR$/);
 const windToken=tokens.find(t=>/^(?:\d{3}|VRB)\d{2,3}(?:G\d{2,3})?KT$/.test(t));
 const speed=windToken?Number(windToken.match(/(?:\d{3}|VRB)(\d{2,3})/)[1]):0;
 const gust=windToken?.match(/G(\d{2,3})KT/);
 const windy=speed>=25||(gust&&Number(gust[1])>=25);
 const ceiling=has(/^OVC\d{3}/)?'overcast':has(/^BKN\d{3}/)?'cloudy':has(/^SCT\d{3}/)?'scattered':has(/^FEW\d{3}/)?'few':'clear';
 return {storm,snow,rain,fog,mist,windy,ceiling};
}
function weatherIcon(a){
 const c=conditions(a),dark=c.storm||c.ceiling==='overcast';
 const cloud=dark?'#71859b':'#d8e8f6',shadow=dark?'#344b66':'#89a7c3';
 const hasCloud=c.storm||c.snow||c.rain||c.fog||c.mist||c.ceiling!=='clear';
 const sun=!c.storm&&!c.snow&&!c.rain&&!c.fog&&!c.mist&&(c.ceiling==='clear'||c.ceiling==='few'||c.ceiling==='scattered');
 const parts=[];
 if(sun){
  parts.push('<g stroke="#ffce35" stroke-width="3.2" stroke-linecap="round">');
  for(let i=0;i<8;i++){const t=i*Math.PI/4;parts.push('<path d="M'+(32+Math.cos(t)*16).toFixed(1)+' '+(22+Math.sin(t)*16).toFixed(1)+' L'+(32+Math.cos(t)*21).toFixed(1)+' '+(22+Math.sin(t)*21).toFixed(1)+'"/>')}
  parts.push('</g><circle cx="32" cy="22" r="12" fill="#ffcf2d" stroke="#ffac15" stroke-width="1.5"/>');
 }
 if(hasCloud){
  const x=sun?32:13;
  parts.push('<g><path d="M'+x+' 40 C'+(x-6)+' 40 '+(x-7)+' 28 '+(x+2)+' 26 C'+(x+4)+' 14 '+(x+20)+' 13 '+(x+26)+' 24 C'+(x+40)+' 19 '+(x+48)+' 31 '+(x+42)+' 40 Z" fill="'+shadow+'"/><path d="M'+x+' 37 C'+(x-6)+' 37 '+(x-5)+' 28 '+(x+4)+' 28 C'+(x+8)+' 17 '+(x+21)+' 18 '+(x+26)+' 28 C'+(x+39)+' 24 '+(x+43)+' 33 '+(x+40)+' 37 Z" fill="'+cloud+'"/></g>');
 }
 if(c.rain||c.storm)parts.push('<g stroke="#31b8ff" stroke-width="3.5" stroke-linecap="round"><path d="M24 45l-5 9 M37 45l-5 9 M50 45l-5 9"/></g>');
 if(c.snow)parts.push('<g stroke="#effaff" stroke-width="2" stroke-linecap="round"><path d="M39 44v13 M33 50.5h12 M34.5 46l9 9 M43.5 46l-9 9"/></g>');
 if(c.storm)parts.push('<path d="M40 37L31 48h8l-5 12 17-17h-9l5-6z" fill="#ffd22f" stroke="#e89d0c" stroke-width="1"/>');
 if(c.fog||c.mist){
  const op=c.fog?'0.96':'0.62';
  parts.push('<g stroke="#eef7ff" stroke-width="'+(c.fog?'4':'3')+'" opacity="'+op+'" stroke-linecap="round"><path d="M13 43h45 M8 50h49 M17 57h38"/></g>');
 }
 if(c.windy)parts.push('<g fill="none" stroke="#e9f7ff" stroke-width="2.9" stroke-linecap="round"><path d="M49 12h14q8 0 6-6 M51 19h17q9 0 7 8 M54 26h9q7 0 5 6"/></g>');
 const desc=[c.storm?'orage':null,c.snow?'neige':null,c.rain?'pluie':null,c.fog?'brouillard':c.mist?'brume':null,c.windy?'vent fort':null].filter(Boolean);
 if(!desc.length)desc.push(({clear:'ciel dégagé',few:'peu nuageux',scattered:'nuageux',cloudy:'nuageux',overcast:'couvert'})[c.ceiling]);
 return {html:'<svg class="wx-art" viewBox="0 0 82 64" width="66" height="52" role="img" aria-label="'+safe(desc.join(', '))+'">'+parts.join('')+'</svg>',label:desc.join(' + ')};
}
function decode(raw){
 const s=String(raw||'').toUpperCase(),lines=[];
 const w=s.match(/\b(\d{3}|VRB)(\d{2,3})(?:G(\d{2,3}))?KT\b/);
 if(w)lines.push('Vent : '+(w[1]==='VRB'?'variable':w[1]+'°')+' à '+Number(w[2])+' kt'+(w[3]?', rafales '+Number(w[3])+' kt':''));
 const v=s.match(/\b(9999|\d{4})\b/);
 if(v)lines.push('Visibilité : '+(v[1]==='9999'?'10 km ou plus':Number(v[1])+' m'));
 const clouds=[...s.matchAll(/\b(FEW|SCT|BKN|OVC)(\d{3})(?:CB|TCU)?\b/g)];
 const labels={FEW:'quelques nuages',SCT:'nuages épars',BKN:'nuageux',OVC:'couvert'};
 if(clouds.length)lines.push('Nuages : '+clouds.map(c=>labels[c[1]]+' à '+Number(c[2])*100+' ft').join(' ; '));
 else if(/\b(CAVOK|SKC|CLR|NSC|NCD)\b/.test(s))lines.push('Ciel : dégagé ou sans nuage significatif signalé');
 const t=s.match(/\b(M?\d{2})\/(M?\d{2})\b/);
 if(t){const n=x=>x[0]==='M'?'-'+Number(x.slice(1)):String(Number(x));lines.push('Température : '+n(t[1])+' °C · point de rosée : '+n(t[2])+' °C')}
 const q=s.match(/\bQ(\d{4})\b/);if(q)lines.push('QNH : '+Number(q[1])+' hPa');
 if(/\bTS/.test(s))lines.push('Phénomène : orage signalé');
 if(/\b(?:FG|BR)\b/.test(s))lines.push('Phénomène : brouillard ou brume');
 if(/\b(?:RA|SHRA|DZ)\b/.test(s))lines.push('Phénomène : précipitations liquides');
 if(/\bSN\b/.test(s))lines.push('Phénomène : neige');
 return lines.length?lines.map(x=>'<div>'+safe(x)+'</div>').join(''):'Décodage automatique partiel indisponible : consulter le METAR brut.';
}
async function load(){
 if(map||loading)return;loading=true;
 const el=$('weather-map');if(!el)return;
 try{
  if(!window.L){await new Promise((ok,no)=>{const s=document.createElement('script');s.src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';s.onload=ok;s.onerror=no;document.head.appendChild(s)})}
  const [wr,cr,ar]=await Promise.all([fetch('weather_all.json',{cache:'no-store'}).then(async r=>r.ok?r:fetch('status.json',{cache:'no-store'})),fetch('airport_coordinates.json',{cache:'no-store'}),fetch('airports.json',{cache:'no-store'})]);
  if(!wr.ok||!cr.ok||!ar.ok)throw Error('Les données météo complètes ne sont pas encore publiées.');
  const [weather,coords,airports]=await Promise.all([wr.json(),cr.json(),ar.json()]);if(!weather.stations&&Array.isArray(weather.weather))weather.stations=weather.weather;
  const names=new Map(airports.map(a=>[a.icao,a.name]));
  map=L.map(el,{worldCopyJump:true}).setView([35,10],3);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© OpenStreetMap'}).addTo(map);
  layer=L.layerGroup().addTo(map);
  const valid=new Set(),bounds=[];
  for(const a of weather.stations||[]){
   const c=coords[a.icao];if(!c||!Number.isFinite(Number(c.lat))||!Number.isFinite(Number(c.lon)))continue;
   valid.add(a.icao);
   const symbol=weatherIcon(a),label=safe(a.icao);
   const marker=L.marker([Number(c.lat),Number(c.lon)],{icon:L.divIcon({className:'wx-marker',html:'<span class="wx-symbol">'+symbol.html+'</span><span class="wx-icao">'+label+'</span>',iconSize:[82,80],iconAnchor:[41,40]})});
   marker.bindPopup('<div class="wx-popup"><h3>'+symbol.html+' '+label+' — '+safe(names.get(a.icao)||a.name||'')+'</h3><p><strong>Observation :</strong> '+safe(a.observed_at||'')+'</p><pre>'+safe(a.raw||'METAR absent')+'</pre><h4>Décodage du METAR</h4>'+decode(a.raw)+'</div>',{maxWidth:380,minWidth:260});
   marker.addTo(layer);bounds.push([Number(c.lat),Number(c.lon)]);
  }
  // Les stations sans METAR récent restent visibles, sans météo inventée.
  for(const [icao,c] of Object.entries(coords)){
   if(valid.has(icao)||!names.has(icao)||!Number.isFinite(Number(c.lat))||!Number.isFinite(Number(c.lon)))continue;
   L.marker([Number(c.lat),Number(c.lon)],{icon:L.divIcon({className:'wx-marker wx-missing',html:'<span class="wx-symbol">❔</span><span class="wx-icao">'+safe(icao)+'</span>',iconSize:[65,58],iconAnchor:[32,29]})}).bindPopup('<strong>'+safe(icao)+'</strong><p>Aucun METAR récent disponible dans la dernière collecte.</p>').addTo(layer);
  }
  if(bounds.length)map.fitBounds(bounds,{padding:[28,28],maxZoom:4});
  $('weather-map-count').textContent=valid.size+' stations avec METAR récent · '+names.size+' scènes dans l’inventaire';
 }catch(e){el.innerHTML='<p class="error">'+safe(e.message)+'</p>'}finally{loading=false}
}
document.addEventListener('click',e=>{if(e.target.closest('[data-view="meteo"],[data-goto="meteo"]'))setTimeout(()=>{load();map?.invalidateSize()},120)});
window.addEventListener('hashchange',()=>{if(location.hash==='#meteo')setTimeout(()=>{load();map?.invalidateSize()},120)});
document.addEventListener('DOMContentLoaded',()=>{if(location.hash==='#meteo')setTimeout(load,250)});
})();
