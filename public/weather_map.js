/* Carte météo des aéroports du Journal — observations réelles uniquement. */
(()=>{'use strict';
let map,layer,loading=false,rangeCircle=null,routeLine=null,routeTimeMarker=null,coordinates={};const weatherMarkers=[];const missingMarkers=[];
const $=id=>document.getElementById(id);
const ANIMATION_KEY='msfs-weather-icons-animated';
function iconAnimationEnabled(){try{return localStorage.getItem(ANIMATION_KEY)!=='off'}catch{return true}}
function updateIconAnimation(){
 const enabled=iconAnimationEnabled();
 document.documentElement.classList.toggle('wx-icons-paused',!enabled);
 const checkbox=$('wx-animate-icons');
 if(checkbox)checkbox.checked=enabled;
}
document.addEventListener('change',e=>{
 if(e.target?.id==='wx-animate-icons'){
  try{localStorage.setItem(ANIMATION_KEY,e.target.checked?'on':'off')}catch(_){}
  updateIconAnimation();
 }
});
updateIconAnimation();

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
  parts.push('<g class="wx-rays" stroke="#ffce35" stroke-width="3.2" stroke-linecap="round">');
  for(let i=0;i<8;i++){const t=i*Math.PI/4;parts.push('<path d="M'+(32+Math.cos(t)*16).toFixed(1)+' '+(22+Math.sin(t)*16).toFixed(1)+' L'+(32+Math.cos(t)*21).toFixed(1)+' '+(22+Math.sin(t)*21).toFixed(1)+'"/>')}
  parts.push('</g><circle class="wx-sun" cx="32" cy="22" r="12" fill="#ffcf2d" stroke="#ffac15" stroke-width="1.5"/>');
 }
 if(hasCloud){
  const x=sun?32:13;
  parts.push('<g class="wx-cloud"><path d="M'+x+' 40 C'+(x-6)+' 40 '+(x-7)+' 28 '+(x+2)+' 26 C'+(x+4)+' 14 '+(x+20)+' 13 '+(x+26)+' 24 C'+(x+40)+' 19 '+(x+48)+' 31 '+(x+42)+' 40 Z" fill="'+shadow+'"/><path d="M'+x+' 37 C'+(x-6)+' 37 '+(x-5)+' 28 '+(x+4)+' 28 C'+(x+8)+' 17 '+(x+21)+' 18 '+(x+26)+' 28 C'+(x+39)+' 24 '+(x+43)+' 33 '+(x+40)+' 37 Z" fill="'+cloud+'"/></g>');
 }
 if(c.rain||c.storm)parts.push('<g class="wx-rain" stroke="#31b8ff" stroke-width="3.5" stroke-linecap="round"><path d="M24 45l-5 9 M37 45l-5 9 M50 45l-5 9"/></g>');
 if(c.snow)parts.push('<g class="wx-snow" stroke="#effaff" stroke-width="2" stroke-linecap="round"><path d="M39 44v13 M33 50.5h12 M34.5 46l9 9 M43.5 46l-9 9"/></g>');
 if(c.storm)parts.push('<path class="wx-lightning" d="M40 37L31 48h8l-5 12 17-17h-9l5-6z" fill="#ffd22f" stroke="#e89d0c" stroke-width="1"/>');
 if(c.fog||c.mist){
  const op=c.fog?'0.96':'0.62';
  parts.push('<g class="wx-fog" stroke="#eef7ff" stroke-width="'+(c.fog?'4':'3')+'" opacity="'+op+'" stroke-linecap="round"><path d="M13 43h45 M8 50h49 M17 57h38"/></g>');
 }
 if(c.windy)parts.push('<g class="wx-wind" fill="none" stroke="#e9f7ff" stroke-width="2.9" stroke-linecap="round"><path d="M49 12h14q8 0 6-6 M51 19h17q9 0 7 8 M54 26h9q7 0 5 6"/></g>');
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
function flightCategory(a){
 const raw=String(a.raw||'').toUpperCase().split(/\s+RMK\b/)[0];
 const ceiling=[...raw.matchAll(/\b(?:BKN|OVC|VV)(\d{3})\b/g)].map(x=>Number(x[1])*100);
 const c=ceiling.length?Math.min(...ceiling):Infinity;
 let visibility=Infinity;
 if(/\bCAVOK\b/.test(raw))visibility=10/1.609344;
 const tokens=raw.split(/\s+/);const windIndex=tokens.findIndex(t=>/^(?:\d{3}|VRB)\d{2,3}(?:G\d{2,3})?KT$/.test(t));
 const visibilityToken=windIndex>=0?tokens.slice(windIndex+1,windIndex+4).find(t=>/^(?:9999|\d{4})(?:NDV)?$/.test(t)):null;
 const meters=visibilityToken?[Number(visibilityToken.slice(0,4))]:[];
 if(meters.length)visibility=Math.min(visibility,Math.min(...meters.map(x=>x===9999?10000:x))/1609.344);
 const sm=raw.match(/\b(?:(\d+)\s+)?(\d+\/\d+|\d+)SM\b/);
 if(sm){const frac=sm[2].includes('/')?sm[2].split('/').reduce((a,b)=>Number(a)/Number(b)):Number(sm[2]);visibility=Math.min(visibility,Number(sm[1]||0)+frac)}
 if(c<500||visibility<1)return 'LIFR';
 if(c<1000||visibility<3)return 'IFR';
 if(c<=3000||visibility<=5)return 'MVFR';
 return 'VFR';
}
function weatherKinds(a){
 const c=conditions(a),out=[];
 if(c.storm)out.push('storm');if(c.snow)out.push('snow');if(c.rain)out.push('rain');
 if(c.fog||c.mist)out.push('fog');if(c.windy)out.push('wind');
 if(c.ceiling==='clear'||c.ceiling==='few')out.push('sun');
 if(c.ceiling!=='clear')out.push('cloud');
 return out;
}
function applyFilters(){
 if(!layer)return;
 const wx=new Set([...document.querySelectorAll('#wx-phenomena input:checked')].map(x=>x.value));
 const fc=new Set([...document.querySelectorAll('#wx-flight input:checked')].map(x=>x.value));
 layer.clearLayers();let shown=0;
 for(const x of weatherMarkers)if(fc.has(x.flight)&&x.kinds.some(k=>wx.has(k))){layer.addLayer(x.marker);shown++}
 if(wx.size===7&&fc.size===4)for(const item of missingMarkers)layer.addLayer(item.marker);
 const count=$('weather-map-count');if(count)count.textContent=shown+' stations affichées sur '+weatherMarkers.length+' METAR récents · '+missingMarkers.length+' sans METAR';
}
document.addEventListener('change',e=>{if(e.target.closest('#wx-filters'))applyFilters()});
document.addEventListener('click',e=>{if(e.target.closest('#wx-reset')){document.querySelectorAll('#wx-filters input[type=checkbox]').forEach(x=>x.checked=true);applyFilters()}});

// Modèle exploratoire A320 non calibré sur des OFP SimBrief. Temps bloc indicatif.
// Estimation bloc A320 calibree sur trois OFP SimBrief (EIDW-LFPG, KSEA-KLAS, LFPG-LGMK).
// Ajustement indicatif : 52 min fixes + 0,12 min par NM orthodromique.
// Ne remplace pas un OFP : vents, routage, roulage et contraintes ATC non modelises.
const RANGE_FIXED_MIN=52;
const RANGE_MIN_PER_NM=0.12;
const distanceForMinutes=minutes=>Math.max(0,(minutes-RANGE_FIXED_MIN)/RANGE_MIN_PER_NM);
const minutesForDistance=nm=>Math.round(RANGE_FIXED_MIN+nm*RANGE_MIN_PER_NM);
function airportPoint(code){
 const c=coordinates[String(code||'').trim().toUpperCase()];
 return c&&Number.isFinite(Number(c.lat))&&Number.isFinite(Number(c.lon))?[Number(c.lat),Number(c.lon)]:null;
}
function haversineNm(a,b){
 const rad=Math.PI/180,lat1=a[0]*rad,lat2=b[0]*rad,dlat=(b[0]-a[0])*rad,dlon=(b[1]-a[1])*rad;
 const h=Math.sin(dlat/2)**2+Math.cos(lat1)*Math.cos(lat2)*Math.sin(dlon/2)**2;
 return 3440.065*2*Math.asin(Math.min(1,Math.sqrt(h)));
}
function flightMidpoint(a,b){
 const toRad=Math.PI/180,toDeg=180/Math.PI;
 const v=([lat,lon])=>[Math.cos(lat*toRad)*Math.cos(lon*toRad),Math.cos(lat*toRad)*Math.sin(lon*toRad),Math.sin(lat*toRad)];
 const x=v(a),y=v(b),m=x.map((n,i)=>n+y[i]),norm=Math.hypot(...m);
 if(norm<1e-8)return [(a[0]+b[0])/2,(a[1]+b[1])/2];
 return [Math.atan2(m[2],Math.hypot(m[0],m[1]))*toDeg,Math.atan2(m[1],m[0])*toDeg];
}
function updateAirportLabelColors(){
 const orig=$('simbrief-departure')?.value.trim().toUpperCase()||'';
 const dest=$('simbrief-arrival')?.value.trim().toUpperCase()||'';
 for(const item of weatherMarkers){
  const node=item.marker.getElement();if(!node)continue;
  node.classList.toggle('wx-is-departure',!!orig&&item.icao===orig);
  node.classList.toggle('wx-is-arrival',!!dest&&item.icao===dest);
 }
 for(const item of missingMarkers){
  const node=item.marker.getElement();if(!node)continue;
  node.classList.toggle('wx-is-departure',!!orig&&item.icao===orig);
  node.classList.toggle('wx-is-arrival',!!dest&&item.icao===dest);
 }
}
function updateFlightRange(){
 const info=$('flight-range-info'),orig=$('simbrief-departure')?.value.trim().toUpperCase()||'',dest=$('simbrief-arrival')?.value.trim().toUpperCase()||'';
 updateAirportLabelColors();
 const minutes=Number($('flight-duration')?.value||120),nm=distanceForMinutes(minutes);
 const forecast=$('simbrief-estimated-time');
 if(forecast){const from=airportPoint(orig),to=airportPoint(dest);if(from&&to){const estimate=minutesForDistance(haversineNm(from,to));forecast.textContent=Math.floor(estimate/60)+' h '+String(estimate%60).padStart(2,'0')}else forecast.textContent='—'}
 if(!info)return;
 if(map&&rangeCircle){map.removeLayer(rangeCircle);rangeCircle=null}
 if(map&&routeLine){map.removeLayer(routeLine);routeLine=null}
 if(map&&routeTimeMarker){map.removeLayer(routeTimeMarker);routeTimeMarker=null}
 const a=airportPoint(orig),b=airportPoint(dest);
 if(a&&b){
  const dist=haversineNm(a,b);
  if(map){
   routeLine=L.polyline([a,b],{color:'#20b6f3',weight:3,dashArray:'8 6'}).addTo(map);
   const duration=minutesForDistance(dist);
   const label=Math.floor(duration/60)+' h '+String(duration%60).padStart(2,'0');
   routeTimeMarker=L.marker(flightMidpoint(a,b),{interactive:false,keyboard:false,zIndexOffset:1000,icon:L.divIcon({className:'wx-route-time-marker',html:'<span class="wx-route-time-label" aria-label="Temps de vol estimé : '+label+'">'+label+'</span>',iconSize:[92,32],iconAnchor:[46,16]})}).addTo(map);
   map.fitBounds(routeLine.getBounds(),{padding:[60,60],maxZoom:7});
  }
  const estimate=minutesForDistance(dist);
  const fmt=m=>Math.floor(m/60)+' h '+String(m%60).padStart(2,'0');
  const uncertainty=Math.max(15,Math.round(estimate*.12));
  info.textContent=orig+' → '+dest+' : '+Math.round(dist).toLocaleString('fr-FR')+' NM à vol d’oiseau · temps bloc A320 indicatif : '+fmt(estimate)+' (fourchette '+fmt(Math.max(0,estimate-uncertainty))+' à '+fmt(estimate+uncertainty)+'). Seul un OFP SimBrief donne une durée calculée pour la route et la météo.';
 }else if((a&&!dest)||(b&&!orig)){
  const center=a||b,icao=a?orig:dest;
  if(map){rangeCircle=L.circle(center,{radius:nm*1852,color:'#3bc5ff',weight:2,fillColor:'#2b9cda',fillOpacity:.12,interactive:false}).addTo(map);map.fitBounds(rangeCircle.getBounds(),{padding:[35,35],maxZoom:6})}
  info.textContent='Rayon indicatif depuis '+icao+' : '+Math.round(nm).toLocaleString('fr-FR')+' NM ('+Math.round(nm*1.852).toLocaleString('fr-FR')+' km) pour '+Math.floor(minutes/60)+' h '+String(minutes%60).padStart(2,'0')+' min de temps bloc. Prévoir une marge : le cercle ne garantit pas le temps réel.';
 }else if((orig&&!a)||(dest&&!b)){
  info.textContent='Coordonnées indisponibles pour '+[orig&&!a?orig:null,dest&&!b?dest:null].filter(Boolean).join(' et ')+'. Sélectionnez un aéroport présent sur la carte.';
 }else info.textContent='Choisissez un aéroport de départ ou d’arrivée sur la carte pour afficher la portée estimée.';
}
function setAirportField(field,icao){
 const el=$(field==='departure'?'simbrief-departure':'simbrief-arrival');
 if(!el)return;
 el.value=icao;el.dispatchEvent(new Event('input',{bubbles:true}));
 map?.closePopup();
}
document.addEventListener('click',e=>{
 const btn=e.target.closest('[data-flight-airport]');
 if(btn){setAirportField(btn.dataset.flightField,btn.dataset.flightAirport)}
});
document.addEventListener('input',e=>{
 if(e.target?.id==='simbrief-departure'||e.target?.id==='simbrief-arrival')updateFlightRange();
});
document.addEventListener('change',e=>{if(e.target?.id==='flight-duration')updateFlightRange()});
function setWeatherMapFullscreen(expanded){
 const shell=$('weather-map-shell'),btn=$('weather-map-fullscreen');
 if(!shell||!btn)return;
 shell.classList.toggle('wx-map-expanded',expanded);
 document.body.classList.toggle('wx-map-open',expanded);
 btn.setAttribute('aria-pressed',String(expanded));
 btn.setAttribute('aria-label',expanded?'Quitter le plein écran':'Afficher la carte en plein écran');
 btn.title=expanded?'Quitter le plein écran':'Plein écran';
 btn.innerHTML=expanded?'✕ <span>Quitter le plein écran</span>':'⛶ <span>AGRANDIR LA CARTE</span>';
 if(map){requestAnimationFrame(()=>{map.invalidateSize();setTimeout(()=>map.invalidateSize(),180)})}
}
document.addEventListener('click',e=>{
 if(e.target.closest('#weather-map-fullscreen')){
  setWeatherMapFullscreen(!$('weather-map-shell')?.classList.contains('wx-map-expanded'));
 }
 if(e.target.closest('#simbrief-clear-airports')){
  for(const id of ['simbrief-departure','simbrief-arrival']){const el=$(id);if(el){el.value='';el.dispatchEvent(new Event('input',{bubbles:true}))}}
  map?.closePopup();
 }
});
document.addEventListener('keydown',e=>{
 if(e.key==='Escape'&&$('weather-map-shell')?.classList.contains('wx-map-expanded'))setWeatherMapFullscreen(false);
});

document.addEventListener('DOMContentLoaded',()=>{
 const sel=$('flight-duration');if(!sel)return;
 for(let m=90;m<=300;m+=15){const option=document.createElement('option');option.value=String(m);option.textContent=Math.floor(m/60)+' h '+String(m%60).padStart(2,'0');sel.appendChild(option)}
 sel.value='120';updateFlightRange();
});
function popupAirportActions(icao){
 const code=safe(icao);
 return '<div class="wx-popup-actions"><button type="button" data-flight-airport="'+code+'" data-flight-field="departure">✈ Départ</button><button type="button" data-flight-airport="'+code+'" data-flight-field="arrival">⌖ Arrivée</button></div>';
}

async function load(){
 if(map||loading)return;loading=true;
 const el=$('weather-map');if(!el)return;
 try{
  if(!window.L){await new Promise((ok,no)=>{const s=document.createElement('script');s.src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';s.onload=ok;s.onerror=no;document.head.appendChild(s)})}
  const [wr,cr,ar]=await Promise.all([fetch('weather_all.json',{cache:'no-store'}).then(async r=>r.ok?r:fetch('status.json',{cache:'no-store'})),fetch('airport_coordinates.json',{cache:'no-store'}),fetch('airports.json',{cache:'no-store'})]);
  if(!wr.ok||!cr.ok||!ar.ok)throw Error('Les données météo complètes ne sont pas encore publiées.');
  const [weather,coords,airports]=await Promise.all([wr.json(),cr.json(),ar.json()]);if(!weather.stations&&Array.isArray(weather.weather))weather.stations=weather.weather;
  coordinates=coords;
  const names=new Map(airports.map(a=>[a.icao,a.name]));
  map=L.map(el,{worldCopyJump:true}).setView([35,10],3);
  // Mêmes fonds que la carte des aéroports : raster immédiatement disponible,
  // fonds vectoriels ajoutés si MapLibre peut se charger.
  const baseMaps={
   'Plan':L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}),
   'Satellite':L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Tiles &copy; Esri and contributors'}),
   'Relief':L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',{maxZoom:17,attribution:'&copy; OpenTopoMap contributors &copy; OpenStreetMap'})
  };
  const selectedStyle=(()=>{try{return localStorage.getItem('msfs-weather-map-style')||'Plan'}catch{return 'Plan'}})();
  let mapStyles;
  const showMapStyles=()=>{if(mapStyles)map.removeControl(mapStyles);mapStyles=L.control.layers(baseMaps,null,{position:'topleft',collapsed:true}).addTo(map)};
  (baseMaps[selectedStyle]||baseMaps.Plan).addTo(map);
  showMapStyles();
  map.on('baselayerchange',e=>{try{localStorage.setItem('msfs-weather-map-style',e.name)}catch(_){}});
  // Les fonds vectoriels ne doivent jamais bloquer les METAR.
  (async()=>{
   try{
    const loadScript=src=>new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=src;script.onload=resolve;script.onerror=reject;document.head.appendChild(script)});
    if(!document.getElementById('maplibre-map-styles')){const css=document.createElement('link');css.id='maplibre-map-styles';css.rel='stylesheet';css.href='https://cdn.jsdelivr.net/npm/maplibre-gl@5.24.0/dist/maplibre-gl.css';document.head.appendChild(css)}
    if(!window.maplibregl)await loadScript('https://cdn.jsdelivr.net/npm/maplibre-gl@5.24.0/dist/maplibre-gl.js');
    if(!L.maplibreGL)await loadScript('https://cdn.jsdelivr.net/npm/@maplibre/maplibre-gl-leaflet@0.1.1/leaflet-maplibre-gl.js');
    if(!L.maplibreGL)return;
    for(const [name,style] of Object.entries({'Sombre':'dark','Fiord':'fiord','Positron':'positron','Liberty':'liberty','Bright':'bright'})){
     baseMaps[name]=L.maplibreGL({style:'https://tiles.openfreemap.org/styles/'+style,attribution:'&copy; OpenFreeMap &copy; OpenStreetMap contributors'});
    }
    showMapStyles();
    if(baseMaps[selectedStyle]&&['Sombre','Fiord','Positron','Liberty','Bright'].includes(selectedStyle)){
     map.eachLayer(layer=>{if(Object.values(baseMaps).includes(layer))map.removeLayer(layer)});
     baseMaps[selectedStyle].addTo(map);
    }
   }catch(e){console.warn('Fonds vectoriels météo indisponibles, fonds classiques conservés',e)}
  })();
  layer=L.layerGroup().addTo(map);
  const valid=new Set(),bounds=[];
  for(const a of weather.stations||[]){
   const c=coords[a.icao];if(!c||!Number.isFinite(Number(c.lat))||!Number.isFinite(Number(c.lon)))continue;
   valid.add(a.icao);
   const symbol=weatherIcon(a),label=safe(a.icao);
   const marker=L.marker([Number(c.lat),Number(c.lon)],{icon:L.divIcon({className:'wx-marker',html:'<span class="wx-symbol">'+symbol.html+'</span><span class="wx-icao">'+label+'</span>',iconSize:[82,80],iconAnchor:[41,40]})});
   marker.bindPopup('<div class="wx-popup"><h3>'+symbol.html+' '+label+' — '+safe(names.get(a.icao)||a.name||'')+'</h3>'+popupAirportActions(a.icao)+'<p><strong>Observation :</strong> '+safe(a.observed_at||'')+'</p><pre>'+safe(a.raw||'METAR absent')+'</pre><h4>Décodage du METAR</h4>'+decode(a.raw)+'</div>',{maxWidth:380,minWidth:260});
   weatherMarkers.push({marker,icao:String(a.icao||'').toUpperCase(),flight:flightCategory(a),kinds:weatherKinds(a)});marker.on('add',updateAirportLabelColors);bounds.push([Number(c.lat),Number(c.lon)]);
  }
  // Les stations sans METAR récent restent visibles, sans météo inventée.
  for(const [icao,c] of Object.entries(coords)){
   if(valid.has(icao)||!names.has(icao)||!Number.isFinite(Number(c.lat))||!Number.isFinite(Number(c.lon)))continue;
   const missingMarker=L.marker([Number(c.lat),Number(c.lon)],{icon:L.divIcon({className:'wx-marker wx-missing',html:'<span class="wx-symbol">❔</span><span class="wx-icao">'+safe(icao)+'</span>',iconSize:[65,58],iconAnchor:[32,29]})}).bindPopup('<strong>'+safe(icao)+'</strong>'+popupAirportActions(icao)+'<p>Aucun METAR récent disponible dans la dernière collecte.</p>');
   missingMarkers.push({marker:missingMarker,icao:String(icao).toUpperCase()});missingMarker.on('add',updateAirportLabelColors);
  }
  applyFilters();
  updateFlightRange();
  if(bounds.length&&!rangeCircle&&!routeLine)map.fitBounds(bounds,{padding:[28,28],maxZoom:4});

 }catch(e){el.innerHTML='<p class="error">'+safe(e.message)+'</p>'}finally{loading=false}
}
document.addEventListener('msfs:show-simbrief-on-weather-map',e=>{
 const orig=String(e.detail?.origin||'').trim().toUpperCase(),dest=String(e.detail?.destination||'').trim().toUpperCase();
 if(!/^[A-Z]{4}$/.test(orig)||!/^[A-Z]{4}$/.test(dest))return;
 for(const [id,code] of [['simbrief-departure',orig],['simbrief-arrival',dest]]){
  const input=$(id);if(input){input.value=code;input.dispatchEvent(new Event('input',{bubbles:true}))}
 }
 load().then(()=>{map?.invalidateSize();updateFlightRange();$('weather-map-shell')?.scrollIntoView({block:'center',behavior:'smooth'})});
});
document.addEventListener('click',e=>{if(e.target.closest('[data-view="meteo"],[data-goto="meteo"]'))setTimeout(()=>{load();map?.invalidateSize()},120)});
window.addEventListener('hashchange',()=>{if(location.hash==='#meteo')setTimeout(()=>{load();map?.invalidateSize()},120)});
document.addEventListener('DOMContentLoaded',()=>{if(location.hash==='#meteo')setTimeout(load,250)});
})();
