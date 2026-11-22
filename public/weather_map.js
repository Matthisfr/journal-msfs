/* Carte météo des aéroports du Journal — observations réelles uniquement. */
(()=>{'use strict';
let map,layer,loading=false;
const $=id=>document.getElementById(id);
const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function icon(a){
 const s=(a.raw||'').toUpperCase();
 if(/(?:^| )(?:TS|VCTS|\+TS|TSRA|TSGR)/.test(s))return '⛈️';
 if(/(?:^| )(?:SN|SHSN|BLSN|RASN)/.test(s))return '🌨️';
 if(/(?:^| )(?:FG|FZFG|BR|HZ)/.test(s))return '🌫️';
 if(/(?:^| )(?:RA|SHRA|DZ|FZRA)/.test(s))return '🌧️';
 if(/(?:^| )(?:[0-9]{3}([2-9][0-9]|1[89])G[0-9]{2,3}KT)/.test(s))return '💨';
 if(/(?:^| )OVC[0-9]{3}/.test(s))return '☁️';
 if(/(?:^| )(?:BKN|SCT)[0-9]{3}/.test(s))return '🌥️';
 if(/(?:^| )FEW[0-9]{3}/.test(s))return '🌤️';
 if(/(?:^| )(?:CAVOK|SKC|CLR|NSC|NCD)/.test(s))return '☀️';
 return a.icon||'☁️';
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
   const symbol=icon(a),label=safe(a.icao);
   const marker=L.marker([Number(c.lat),Number(c.lon)],{icon:L.divIcon({className:'wx-marker',html:'<span class="wx-symbol">'+symbol+'</span><span class="wx-icao">'+label+'</span>',iconSize:[65,58],iconAnchor:[32,29]})});
   marker.bindPopup('<div class="wx-popup"><h3>'+symbol+' '+label+' — '+safe(names.get(a.icao)||a.name||'')+'</h3><p><strong>Observation :</strong> '+safe(a.observed_at||'')+'</p><pre>'+safe(a.raw||'METAR absent')+'</pre><h4>Décodage du METAR</h4>'+decode(a.raw)+'</div>',{maxWidth:380,minWidth:260});
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
