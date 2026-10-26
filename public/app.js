'use strict';
const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const isSafeUrl=u=>{try{const x=new URL(u);return ['https:','http:'].includes(x.protocol)?x.href:'#'}catch{return '#'}};
const localDate=s=>{if(!s)return '—';const d=new Date(s.length===10?s+'T12:00:00Z':s);return isNaN(d)?s:new Intl.DateTimeFormat('fr-FR',{day:'2-digit',month:'short',year:'numeric',timeZone:'Europe/Paris'}).format(d)};
const localDateTime=s=>{if(!s)return 'Non exécutée';const d=new Date(s);return isNaN(d)?s:new Intl.DateTimeFormat('fr-FR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',timeZone:'Europe/Paris'}).format(d)};
let airports=[], status={}, editorial={}, software={items:[]}, hardware=[], hardwareImages={};
const brandLogos=(()=>{try{return JSON.parse(document.getElementById('brand-manifest')?.textContent||'{}')}catch{return {}}})();
function brandIcon(kind,label){
  const source=brandLogos[kind]?.path||'icons/'+kind+'.svg';
  const fallback='icons/'+kind+'.svg';
  const cls=brandLogos[kind]?' brand-original':'';
  return '<span class="topic-icon topic-'+kind+cls+'" title="'+esc(label)+'" aria-label="'+esc(label)+'"><img src="'+esc(source)+'" width="42" height="42" alt="" decoding="async" onerror="this.onerror=null;this.src=&#39;'+esc(fallback)+'&#39;"></span>';
}
window.MSFS_MAP_URL='https://www.google.com/maps/d/u/0/edit?mid=1smgM-lIXr_QPyWKxPrS68bmU0FsMjYM&usp=sharing';
function switchView(view){if(!document.getElementById(view))view='accueil';$$('.view').forEach(e=>e.classList.toggle('active',e.id===view));$$('.navbtn').forEach(e=>{const sel=e.dataset.view===view;e.classList.toggle('selected',sel);if(sel)e.setAttribute('aria-current','page');else e.removeAttribute('aria-current')});history.replaceState(null,'','#'+view);if(view==='aeroports')renderMap();window.scrollTo({top:0,behavior:'smooth'})}
$$('.navbtn').forEach(e=>e.addEventListener('click',()=>switchView(e.dataset.view)));
$$('[data-goto]').forEach(e=>e.addEventListener('click',()=>switchView(e.dataset.goto)));
$$('[data-top]').forEach(e=>e.addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'})));

function compareVersions(installed,online){
  const a=String(installed||'').match(/\d+/g),b=String(online||'').match(/\d+/g);
  if(!a||!b||a.length!==b.length)return 'different';
  if(Number(a[0])!==Number(b[0]))return Number(b[0])>Number(a[0])?'major':'ahead';
  const n=Math.max(a.length,b.length);
  for(let i=0;i<n;i++){const x=Number(a[i]||0),y=Number(b[i]||0);if(y>x)return 'update';if(y<x)return 'ahead'}
  return 'current';
}
function renderAirports(){
  const q=$('#airport-search').value.trim().toLowerCase(),region=$('#region-filter').value,st=$('#status-filter').value;
  const checkedDate=String(status.versions_checked_at||'').slice(0,10);
  const isVerified=a=>!!a.server_version&&a.version_check_state==='verified'&&a.version_checked_at===checkedDate;
  const verified=airports.filter(isVerified);
  const updates=verified.filter(a=>a.version_comparison==='update');
  $('#verified-count').textContent=verified.length;
  $('#updates-count').textContent=updates.length;
  const issues={
    "Version non publiée":airports.filter(a=>a.version_check_state==='no_version').length,
    "Boutique en retard":airports.filter(a=>a.version_check_state==='source_older').length,
    "Édition / format ambigu":airports.filter(a=>a.version_check_state==='inconsistent').length,
    "Source inaccessible":airports.filter(a=>a.version_check_state==='unavailable').length,
    "Fiche produit manquante":airports.filter(a=>a.version_check_state==='no_source').length,
    "Sous-scène / privé":airports.filter(a=>a.version_check_state==='not_automatable').length
  };
  const unresolved=airports.length-verified.length;
  const diag=$('#airport-diagnostics');
  if(diag)diag.textContent=`À approfondir : ${unresolved} scènes · `+Object.entries(issues).filter(([,n])=>n).map(([label,n])=>`${n} ${label.toLowerCase()}`).join(' · ')+'. Chaque cas est réévalué quotidiennement.';
  const duplicateCounts=new Map();
  airports.forEach(a=>{const code=String(a.icao||'').trim().toUpperCase();if(code)duplicateCounts.set(code,(duplicateCounts.get(code)||0)+1)});
  const matches=airports.filter(a=>(!q||[a.icao,a.original,a.name,a.publisher,a.folder,a.country,a.region,a.installed,a.server_version].join(' ').toLowerCase().includes(q))&&(!region||(a.region||a.country)===region)&&(!st||(st==='verified'?isVerified(a):st==='current'?isVerified(a)&&a.version_comparison==='equal':st==='update'?isVerified(a)&&a.version_comparison==='update':st==='duplicates'?(duplicateCounts.get(String(a.icao||'').trim().toUpperCase())||0)>1:a.status===st)));
  if(airportMap)updateAirportMap(matches);
  $('#airport-count').textContent=`${matches.length} scène${matches.length>1?'s':''} affichée${matches.length>1?'s':''} sur ${airports.length}`;
  const cls={'UNK-P':'p','UNK-V':'v','UNK-C':'c','UNK-S':'s','verified':'ok'};
  $('#airport-body').innerHTML=matches.map(a=>{
    const st=a.status||'UNK-V';
    const source=a.source_url?`<a href="${esc(isSafeUrl(a.source_url))}" target="_blank" rel="noopener noreferrer">${esc((a.source_store||'Éditeur')+(a.source_edition?' · '+a.source_edition:''))} ↗</a>`:a.source_catalog_url?`<a href="${esc(isSafeUrl(a.source_catalog_url))}" target="_blank" rel="noopener noreferrer">Catalogue éditeur (version non confirmée) ↗</a>`:'';
    const comp=a.server_version?(a.version_comparison==='update'?'update':a.version_comparison==='equal'?'current':a.version_comparison==='source_older'?'ahead':'unknown'):'unknown';
    const compLabel=comp==='update'?'MISE À JOUR':comp==='current'?'À JOUR':comp==='ahead'?'INSTALLÉE + RÉCENTE':comp==='major'?'NOUVELLE ÉDITION':'À COMPARER';
    const compClass=comp==='update'?'flag-s':comp==='current'?'flag-ok':'flag-v';
    const online=isVerified(a)?`<b>${esc(a.server_version)}</b><small><span class="flag ${compClass}">${compLabel}</span></small><small>${source}</small><small>Vérifiée le ${esc(localDate(a.version_checked_at))}</small>`:a.server_version?`<b>${esc(a.server_version)}</b><small>${a.version_checked_at===checkedDate?'Version boutique contrôlée aujourd’hui, comparaison non validée':'Dernière version connue, non revalidée aujourd’hui'}</small><small><span class="flag flag-${cls[st]||'v'}">${esc(st==='verified'?'UNK-V':st)}</span></small><small>${source}</small><small>Dernière confirmation : ${esc(localDate(a.version_checked_at))}</small>`:`<span class="flag flag-${cls[st]||'v'}">${esc(st)}</span>${source?`<small>${source}</small>`:''}`;
    return `<tr><td><span class="code">${esc(a.icao)}</span>${a.original!==a.icao?`<small>Source : ${esc(a.original)}</small>`:''}</td><td><b>${esc(a.name)}</b><small>${esc(a.note||a.folder||'')}</small></td><td>${esc(a.publisher)}</td><td><b>${esc(a.installed||'Non renseignée')}</b></td><td>${online}${(a.version_check_state!=='verified'&&a.version_check_reason)?`<small class="source-note">${esc(a.version_check_reason)}</small>`:''}${a.source_note?`<small class="source-note">${esc(a.source_note)}</small>`:''}${a.reference_version&&a.reference_source_url?`<small class="source-note">${a.reference_confidence==='publisher_page_human_checked'||a.reference_confidence==='official_support_human_checked'?'Référence éditeur, non revalidée automatiquement':'Indication tierce non officielle'} : <a href="${esc(isSafeUrl(a.reference_source_url))}" target="_blank" rel="noopener noreferrer">${esc(a.reference_version)} ↗</a> (non utilisée pour les alertes)</small>`:''}</td></tr>`;
  }).join('')||'<tr><td colspan="5">Aucune scène correspondant à ces filtres.</td></tr>';
}
let airportMap=null;
let airportMapMarkers=[];
let airportMapCaption=null;
function updateAirportMap(matches){
 if(!airportMap)return;
 const visibleCodes=new Set(matches.map(a=>String(a.icao||'').trim().toUpperCase()));
 let shown=0;
 for(const item of airportMapMarkers){
  if(visibleCodes.has(item.code)){if(!airportMap.hasLayer(item.marker))item.marker.addTo(airportMap);shown++}
  else if(airportMap.hasLayer(item.marker))airportMap.removeLayer(item.marker);
 }
 if(airportMapCaption)airportMapCaption.textContent=shown+' aéroports affichés sur '+airportMapMarkers.length+' géolocalisés · '+matches.length+' scènes filtrées · Vert : à jour · Orange : MAJ disponible · Gris : non vérifié';
}
async function renderMap(){
 const slot=$('#google-map');if(!slot||airportMap)return;
 try{
  const data=await fetch('airport_coordinates.json').then(r=>r.json());
  if(!window.L){await new Promise((ok,no)=>{const s=document.createElement('script');s.src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';s.onload=ok;s.onerror=no;document.head.appendChild(s)})}
  slot.innerHTML='<div id="airport-leaflet-map"></div><p class="map-caption">Vert : à jour · Orange : mise à jour disponible · Gris : non vérifié</p>';
  airportMap=L.map('airport-leaflet-map').setView([43.7,7.2],5);
  const baseMaps={
    'Plan':L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}),
    'Satellite':L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Tiles &copy; Esri and contributors'}),
    'Relief':L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',{maxZoom:17,attribution:'&copy; OpenTopoMap contributors &copy; OpenStreetMap'}),
    'Sombre':L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',{maxZoom:19,attribution:'&copy; CARTO &copy; OpenStreetMap'})
  };
  const selectedStyle=(()=>{try{return localStorage.getItem('msfs-airport-map-style')||'Plan'}catch{return 'Plan'}})();
  (baseMaps[selectedStyle]||baseMaps.Plan).addTo(airportMap);
  const mapStyles=L.control.layers(baseMaps,null,{position:'topright',collapsed:true}).addTo(airportMap);
  airportMap.on('baselayerchange',e=>{try{localStorage.setItem('msfs-airport-map-style',e.name)}catch{}});

  const groups={};for(const a of airports){const k=a.icao;if(data[k])(groups[k]??=[]).push(a)}
  const bounds=[];
  const mappedSceneCount=Object.values(groups).reduce((sum,items)=>sum+items.length,0);
  const info=slot.querySelector('.map-caption');
  airportMapCaption=info;
  if(info)info.textContent=Object.keys(groups).length+' aéroports localisés · '+mappedSceneCount+' scènes · '+(airports.length-mappedSceneCount)+' scènes sans repère autonome (sous-scènes, code non confirmé ou fictif) · Vert : à jour · Orange : MAJ disponible · Gris : non vérifié';
  for(const [code,items] of Object.entries(groups)){
   const valid=a=>a.version_check_state==='verified'&&a.server_version&&a.version_checked_at===String(status.versions_checked_at||'').slice(0,10);
   const outdated=items.some(a=>valid(a)&&a.version_comparison==='update');
   const current=items.every(a=>valid(a)&&a.version_comparison==='equal');
   const color=outdated?'#f29a25':current?'#249c63':'#9299a3';
   const svg='<svg xmlns="http://www.w3.org/2000/svg" width="36" height="46" viewBox="0 0 36 46"><path d="M18 44C13 35 2 26 2 18a16 16 0 1 1 32 0c0 8-11 18-16 26" fill="'+color+'" stroke="white" stroke-width="2"/><path d="M18 7l3 9 9 4v3l-9-2-1 8 3 3v2l-5-2-5 2v-2l3-3-1-8-9 2v-3l9-4z" fill="white"/></svg>';
   const icon=L.divIcon({className:'airport-pin',html:svg,iconSize:[36,46],iconAnchor:[18,44]});
   const details=items.map(a=>'<p><b>'+esc(a.name||a.folder)+'</b><br>'+esc(a.publisher)+' · '+esc(a.installed||'—')+' / '+esc(a.server_version||'inconnue')+'</p>').join('');
   const m=L.marker([data[code].lat,data[code].lon],{icon}).bindPopup('<strong>'+esc(code)+' — '+esc(data[code].name||'')+'</strong>'+details).addTo(airportMap);
   airportMapMarkers.push({code:String(code).trim().toUpperCase(),marker:m});
   bounds.push(m.getLatLng());
  }
  updateAirportMap(airports.filter(a=>{const q=$('#airport-search').value.trim().toLowerCase(),region=$('#region-filter').value,st=$('#status-filter').value;const code=String(a.icao||'').trim().toUpperCase();const counts=airports.filter(x=>String(x.icao||'').trim().toUpperCase()===code).length;const verified=!!a.server_version&&a.version_check_state==='verified'&&a.version_checked_at===String(status.versions_checked_at||'').slice(0,10);return (!q||[a.icao,a.original,a.name,a.publisher,a.folder,a.country,a.region,a.installed,a.server_version].join(' ').toLowerCase().includes(q))&&(!region||(a.region||a.country)===region)&&(!st||(st==='duplicates'?counts>1:st==='verified'?verified:st==='current'?verified&&a.version_comparison==='equal':st==='update'?verified&&a.version_comparison==='update':a.status===st))}));
  if(bounds.length)airportMap.fitBounds(bounds,{padding:[20,20],maxZoom:7});
  setTimeout(()=>airportMap.invalidateSize(),100);
 }catch(e){slot.textContent='Carte momentanément indisponible : '+e.message}
}
function renderWeather(){const cov=status.weather_coverage||{};$('#metar-eligible').textContent=cov.eligible??'—';$('#metar-fresh').textContent=cov.fresh??'—';$('#metar-updated').textContent=status.weather_checked_at?localDateTime(status.weather_checked_at):'Non collectée';const arr=(status.weather||[]).slice(0,10);const w=$('#weather-container');if(!arr.length){w.innerHTML='<div class="empty"><strong>☁ Aucune observation vérifiée disponible</strong>Le TOP 10 apparaîtra après une collecte METAR réussie. Aucun classement fictif n’est présenté.</div>';return}const stale=status.source_status?.metar!=='ok';w.innerHTML=(stale?'<div class="error">La dernière collecte METAR a échoué : les observations ci-dessous peuvent être périmées. Vérifie les heures UTC.</div>':'')+arr.map((a,i)=>`<article class="weather-item"><div class="weather-rank">${String(i+1).padStart(2,'0')}</div><div class="weather-symbol" aria-label="${esc(a.phenomenon||'Conditions météo')}">${esc(a.icon||'☁️')}</div><div><div class="weather-code">${esc(a.icao)} <span style="font-weight:400;color:#6c8291;font-size:12px;letter-spacing:0">${esc(a.name||'')}</span></div><div class="weather-detail">${esc(a.summary||'Observation disponible')} · ${esc(localDateTime(a.observed_at))} (heure Paris) · <a href="${esc(isSafeUrl(a.source_url||'https://aviationweather.gov/'))}" target="_blank" rel="noopener noreferrer">NOAA AWC ↗</a></div><div class="weather-raw">METAR : ${esc(a.raw||'Non disponible')}</div>${a.taf_raw?`<div class="weather-raw">TAF (prévision) : ${esc(a.taf_raw)}</div>`:''}</div><div class="weather-score">${esc(a.level||'À surveiller')}<small>${esc(a.score??'')} points</small></div></article>`).join('');$('#tile-weather').textContent=`${arr.length} stations classées parmi ${cov.fresh??'?'} METAR récents.`}
function topicInfo(a){
  const s=String([a.topic,a.category,a.title].join(' ')).toLowerCase();
  if(/\bsayintentions\b|\bsayintention\b/.test(s))return ['SI','si','SayIntentions'];
  if(/\bmobiflight\b|\bmf\b/.test(s))return ['MF','mf','MobiFlight'];
  if(/\bfenix\b|\ba32x\b|\bcids\b/.test(s))return ['FX','fenix','Fenix'];
  if(/\bwinctrl\b|\bwinwing\b|\bsimapppro\b/.test(s))return ['WC','winctrl','WINCTRL'];
  if(/\bgsx\b/.test(s))return ['GSX','gsx','GSX'];
  if(/\bnavigraph\b/.test(s))return ['NAV','navigraph','Navigraph'];
  if(/\bfshud\b/.test(s))return ['ATC','fshud','FSHud'];
  if(/\bfsl tl\b|\bfsltl\b|\baig\b/.test(s))return ['AI','traffic','Trafic IA'];
  if(/\bsantiluib3\b|\bs3\b/.test(s))return ['S3','s3','Modules S3'];
  if(/\batc\b/.test(s))return ['ATC','atc','ATC'];
  if(/\bm[eé]t[eé]o\b|\bmetar\b|\bstratawx\b/.test(s))return ['WX','weather','Météo'];
  if(/\bmsfs\b|\bflight simulator\b|\bsim update\b/.test(s))return ['FS','msfs','MSFS 2024'];
  return ['✈','generic','Actualités aviation'];
}
function topicBadge(a){
  const [code,kind,label]=topicInfo(a);
  return brandIcon(kind,label);
}
function newsAgeGroup(a){
  const raw=String(a.published_at||a.date||'');
  const d=new Date(raw.length===10?raw+'T00:00:00Z':raw);
  if(!Number.isFinite(d.getTime()))return 3;
  const hours=(Date.now()-d.getTime())/3600000;
  return hours<=24?0:hours<=72?1:hours<=168?2:3;
}
function newsMarkup(a){
  const change=a.changelog_url?'<div class="news-impact"><b>Version : '+esc(a.version_before||'—')+' → '+esc(a.version_after||'—')+'</b>'+
    (a.details?'<details class="changelog-details"><summary>Afficher les modifications détaillées</summary><p>'+esc(a.details)+'</p></details>':'')+
    '<a href="'+esc(isSafeUrl(a.changelog_url))+'" target="_blank" rel="noopener noreferrer">Consulter le changelog officiel complet ↗</a></div>':'';
  return '<article class="news-card'+(newsAgeGroup(a)===2?' news-old':'')+'"><div class="news-meta">'+esc(a.category||'ACTUALITÉS')+' · '+esc(localDate(a.date))+
    (newsAgeGroup(a)===0?'<span class="new-tag">NEWS</span>':newsAgeGroup(a)===2?'<span class="old-tag">OLD</span>':'')+'</div><div class="news-heading">'+topicBadge(a)+
    '<h3>'+esc(a.title)+'</h3></div>'+(a.summary?'<p>'+esc(a.summary)+'</p>':'')+
    (a.impact?'<div class="news-impact"><b>Impact / action :</b> '+esc(a.impact)+'</div>':'')+change+
    '<div class="news-source"><a href="'+esc(isSafeUrl(a.url))+'" target="_blank" rel="noopener noreferrer">'+esc(a.source||'Source officielle')+' ↗</a></div></article>';
}
function renderNews(){
  const editorialNews=editorial.news||[];
  const superseded=new Set(editorialNews.flatMap(a=>a.supersedes||[]));
  const a=[...editorialNews,...(status.news||[]).filter(x=>!superseded.has(x.url))]
    .filter((x,i,all)=>all.findIndex(y=>(y.id||y.url+' '+y.title)===(x.id||x.url+' '+x.title))===i)
    .filter(x=>newsAgeGroup(x)<3)
    .sort((x,y)=>newsAgeGroup(x)-newsAgeGroup(y) || (new Date(y.published_at||y.date)-new Date(x.published_at||x.date)));
  $('#news-container').innerHTML=a.length?a.map(newsMarkup).join(''):'<div class="empty"><strong>Aucune nouveauté vérifiée</strong>Le site ne publie pas d’annonce sans date ni source vérifiable.</div>';
  $('#home-news').innerHTML=a.filter(x=>newsAgeGroup(x)===0).slice(0,3).map(x=>'<article><div class="home-news-row">'+topicBadge(x)+'<div class="home-news-content"><small>'+esc(x.category||'Actualités')+' · '+esc(localDate(x.date))+'</small><strong>'+esc(x.title)+'</strong><a href="'+esc(isSafeUrl(x.url))+'" target="_blank" rel="noopener noreferrer">Source officielle ↗</a></div></div></article>').join('')||'<p class="muted">Aucune actualité sourcée pour le moment.</p>';
}

function renderSoftware(){
  const items=Array.isArray(software.items)?software.items:[],q=($('#software-search')?.value||'').trim().toLowerCase(),filter=$('#software-filter')?.value||'';
  const changed=items.filter(x=>x.state==='changed').length,verified=items.filter(x=>x.state==='verified'||x.state==='changed').length;
  const overview=$('#software-overview');
  if(overview)overview.innerHTML='<strong>'+items.length+' logiciels suivis</strong><span>'+verified+' versions confirmées · '+changed+' changements · '+(items.length-verified)+' non confirmées</span><small>Contrôle : '+esc(localDateTime(software.checked_at))+'</small>';
  const nav=$('#software-nav-news');if(nav){nav.hidden=!changed;nav.textContent=changed?'NEWS '+changed:'NEWS'}
  const selected=items.filter(x=>(!q||[x.name,x.group,x.version,x.reason].join(' ').toLowerCase().includes(q))&&(!filter||(filter==='changed'?x.state==='changed':filter==='verified'?['verified','changed'].includes(x.state):!['verified','changed'].includes(x.state))));
  const body=$('#software-body');if(!body)return;
  body.innerHTML=selected.map(x=>{
    const ok=['verified','changed'].includes(x.state),fresh=x.state==='changed';
    const tag=fresh?'<span class="new-tag">NEWS</span>':ok?'<span class="flag flag-ok">VÉRIFIÉ</span>':x.reference_version?'<span class="flag flag-c">RÉFÉRENCE DATÉE</span>':'<span class="flag flag-v">UNKNOWN</span>';
    const preview=x.preview_version?'<small>Préversion : '+esc(x.preview_version)+'</small>':'';
    const last=x.previous_version?'<small>Précédente : '+esc(x.previous_version)+'</small>':'';
    return '<tr><td><strong>'+esc(x.name)+'</strong><small>'+esc(x.group)+'</small></td>'+
      '<td><strong>'+esc(x.version||x.reference_version||'Non publiée')+'</strong>'+(x.state==='unavailable'&&x.version?'<small>Dernière version connue · non revérifiée depuis '+esc(localDateTime(x.last_confirmed_at))+'</small>':'')+(x.reference_version&&!x.version?'<small>Relevée le '+esc(localDate(x.reference_checked_at))+' · non revalidée automatiquement</small>':'')+preview+'</td>'+
      '<td>'+tag+last+'<small>'+esc(x.reason||'')+'</small></td>'+
      '<td><a href="'+esc(isSafeUrl(x.version_url||(x.reference_version?x.reference_source_url:null)||x.source_url))+'" target="_blank" rel="noopener noreferrer">Source officielle ↗</a>'+
      (fresh?'<small>Changelog complet dans <a href="#nouveautes" data-software-news="1">Nouveautés</a></small>':'')+
      '<small>Contrôle : '+esc(localDateTime(x.checked_at))+'</small></td></tr>';
  }).join('')||'<tr><td colspan="4">Aucun logiciel correspondant.</td></tr>';
  $$('[data-software-news]').forEach(el=>el.addEventListener('click',e=>{e.preventDefault();switchView('nouveautes')}));
}
function renderHardwareGallery(){
  const el=$('#hardware-gallery');if(!el)return;
  el.innerHTML=(Array.isArray(hardware)?hardware:[]).map(x=>{
    const photo=hardwareImages[x.id]||{};
    const picture=['photo','photo_remote'].includes(photo.state)&&photo.path?
      '<img class="hardware-photo" loading="lazy" decoding="async" src="'+esc(photo.path)+'" alt="Photographie du matériel '+esc(x.name)+'" onerror="this.style.display=&#39;none&#39;;this.nextElementSibling.hidden=false">'+
      '<span class="hardware-no-photo" hidden>Photographie momentanément indisponible</span>':
      '<span class="hardware-no-photo">Photo produit non disponible</span>';
    return '<article class="hardware-card hardware-device">'+
      '<div class="hardware-image">'+picture+'</div>'+
      '<div class="overline">'+esc(x.ownership==='Possédé'?'DANS TON COCKPIT':'MATÉRIEL ATTENDU')+'</div>'+
      '<h3>'+esc(x.name)+'</h3>'+
      '<p>'+esc(x.ownership==='Possédé'?'Matériel possédé · suivi SimAppPro et Fenix.':'Sortie, disponibilité et révision à surveiller.')+'</p>'+
      (x.preview_url?'<p><a href="'+esc(isSafeUrl(x.preview_url))+'" target="_blank" rel="noopener noreferrer">Voir les visuels du prototype ↗</a><small>'+esc(x.preview_note||'')+'</small></p>':'')+'<div class="hardware-card-bottom"><span class="flag '+(x.ownership==='Possédé'?'flag-ok':'flag-v')+'">'+esc(x.ownership)+'</span>'+
      '<a href="'+esc(isSafeUrl(x.official_url))+'" target="_blank" rel="noopener noreferrer">WINCTRL ↗</a></div>'+
      (['photo','photo_remote'].includes(photo.state)?'<small class="photo-credit">'+esc(photo.source||'Photo de produit')+'</small>':'')+
      '</article>';
  }).join('')||'<p>Inventaire matériel indisponible.</p>';
}
function renderHardwareNews(){const a=editorial.hardware||[];$('#hardware-news').innerHTML=a.length?'<div class="sectionbar"><h2>Actualités du matériel</h2></div><div class="news-grid">'+a.map(newsMarkup).join('')+'</div>':''}
function renderStatus(){if(status.edition)$('#edition-date').textContent=new Date(status.edition+'T12:00:00Z').toLocaleDateString('fr-FR',{day:'numeric',month:'long',year:'numeric',timeZone:'Europe/Paris'}).toUpperCase();const done=!!status.last_run;const dateTime=new Intl.DateTimeFormat('fr-FR',{day:'2-digit',month:'long',year:'numeric',hour:'2-digit',minute:'2-digit',timeZone:'Europe/Paris'});$('#home-updated').textContent=done?'Le '+dateTime.format(new Date(status.last_run)):'En attente de la première collecte';$('#home-editorial-updated').textContent=editorial.last_updated?localDate(editorial.last_updated):'Non actualisées';$('#last-check').textContent=done?'Collecte : '+localDateTime(status.last_run):'Données de lancement · non actualisées';$('#sync-label').textContent=done?'DERNIÈRE COLLECTE : '+localDateTime(status.last_run):'COLLECTE AUTOMATIQUE NON ENCORE EXÉCUTÉE';$('#dashboard-timestamp').textContent=done?'Dernier passage : '+localDateTime(status.last_run):'Édition de lancement';$('#run-state').textContent=done?'Collecte exécutée':'Automatisation non encore exécutée';$('#run-detail').textContent=done?'Voir le détail des sources ci-dessous.':'La collecte doit être activée après publication sur GitHub.';$('#status-dot').classList.toggle('good',done&&status.source_status?.metar==='ok');$('#footer-updated').textContent=done?'Dernière collecte : '+localDateTime(status.last_run):'Publication et automatisation non encore activées';const src=status.source_status||{};const parts=[['Météo METAR',src.metar],['Prévisions TAF',src.taf],['Actualités officielles',src.official_news],['Versions des scènes',airports.some(a=>a.server_version)?'partial':src.airport_versions],['Éditorial ChatGPT',editorial.last_updated?'ok':'non_executed']];$('#source-health').innerHTML=parts.map(([name,s])=>`<div class="health ${s==='ok'?'ok':''}"><strong>${esc(name)}</strong><span>${s==='ok'?'Collecte réussie':s==='non_verified'?'Non vérifiées':s==='error'?'Échec de collecte':s==='partial'?'Partiellement vérifiées':'En attente'}</span></div>`).join('')}
function renderQualityAudit(){
 const el=$('#quality-audit-body');if(!el)return;
 const labels={no_version:'Version publique absente',source_older:'Source plus ancienne',inconsistent:'Éditions incompatibles',no_source:'Fiche exacte manquante',not_automatable:'Sous-scène / vérification manuelle',unavailable:'Source inaccessible'};
 const missing=airports.filter(a=>a.version_check_state!=='verified');
 const counts={};missing.forEach(a=>{const k=a.version_check_state||'unavailable';counts[k]=(counts[k]||0)+1});
 const unknownHardware=(Array.isArray(hardware)?hardware:[]).filter(h=>!hardwareImages[h.id]||hardwareImages[h.id].state!=='photo'||hardwareImages[h.id].verification!=='verified_exact_product');
 const sections=[['Scènes non vérifiées',missing.length+' / '+airports.length],['Matériels sans identité photo vérifiée',unknownHardware.length+' / '+(Array.isArray(hardware)?hardware.length:0)],...Object.entries(labels).filter(([k])=>counts[k]).map(([k,label])=>[label,String(counts[k])])];
 el.innerHTML=sections.map(([label,n])=>'<div class="health"><strong>'+esc(label)+'</strong><span>'+esc(n)+'</span></div>').join('');
 const details=$('#quality-airport-details');if(details){details.innerHTML='<table><thead><tr><th>Code</th><th>Scène</th><th>Installée</th><th>Version source</th><th>Diagnostic</th></tr></thead><tbody>'+missing.map(a=>'<tr><td><strong>'+esc(a.icao)+'</strong></td><td>'+esc(a.folder)+'</td><td>'+esc(a.installed||'—')+'</td><td>'+esc(a.server_version||'—')+'</td><td>'+esc(labels[a.version_check_state]||a.version_check_state)+'<small>'+esc(a.version_check_reason||'')+'</small>'+(a.source_url?'<p><a target="_blank" rel="noopener noreferrer" href="'+esc(isSafeUrl(a.source_url))+'">Source éditeur ↗</a></p>':'')+'</td></tr>').join('')+'</tbody></table>';}
 const hardwareDetails=$('#quality-hardware-details');if(hardwareDetails)hardwareDetails.innerHTML=unknownHardware.map(h=>'<p><strong>'+esc(h.name)+'</strong> — '+esc(hardwareImages[h.id]?.reason||'Photo présente mais modèle exact non vérifié visuellement')+'</p>').join('')||'<p>Toutes les photographies ont un fichier référencé. Leur exactitude doit encore être vérifiée individuellement.</p>';

}
async function init(){try{const [ar,sr,er,sv,hc,hi]=await Promise.all(['airports.json','status.json','editorial.json','software_versions.json','hardware_catalog.json','hardware-images.json'].map(p=>fetch(p,{cache:'no-store'}).catch(()=>null)));if(!ar?.ok||!sr?.ok||!er?.ok)throw new Error('Fichiers de données indisponibles');[airports,status,editorial]=await Promise.all([ar.json(),sr.json(),er.json()]);software=sv?.ok?await sv.json():{items:[]};hardware=hc?.ok?await hc.json():[];hardwareImages=hi?.ok?await hi.json():{};$('#count-scenes').textContent=airports.length;$('#count-codes').textContent=new Set(airports.map(x=>x.icao)).size;$('#airport-total').textContent=airports.length+' SCÈNES';const regions=[...new Set(airports.map(a=>a.region||a.country).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'fr'));$('#region-filter').innerHTML='<option value="">Toutes les régions</option>'+regions.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');renderAirports();renderStatus();renderWeather();renderNews();renderHardwareNews();renderSoftware();renderHardwareGallery();renderQualityAudit();}catch(e){$('#run-state').textContent='Données indisponibles';$('#run-detail').textContent='Impossible de charger les fichiers JSON.';$('#weather-container').innerHTML='<div class="error">Chargement des données impossible. Ouvre le site via un serveur web.</div>';$('#airport-count').textContent='Erreur de chargement';console.error(e)}if(location.hash)switchView(location.hash.slice(1))}
async function loadSimbriefFlight(){
  const el=$('#simbrief-flight-data'),button=$('#simbrief-refresh');
  if(!el||!button)return;
  button.disabled=true;el.textContent='Consultation du dernier OFP SimBrief…';
  const url='https://www.simbrief.com/api/xml.fetcher.php?username=Matthis&client=journal-msfs&json=v2';
  try{
    const response=await fetch(url,{cache:'no-store'});
    if(!response.ok)throw new Error('HTTP '+response.status);
    const data=await response.json();
    if(!data||!data.origin||!data.destination)throw new Error('Aucun OFP disponible');
    const val=x=>esc(x||'—');
    const origin=data.origin,dest=data.destination,g=data.general||{},aircraft=data.aircraft||{},times=data.times||{};
    const generated=data.params?.time_generated||data.params?.time_generated_utc||'';
    el.innerHTML='<div class="tile-grid"><div><small>DÉPART</small><h3>'+val(origin.icao_code)+'</h3><p>'+val(origin.name)+'</p></div><div><small>ARRIVÉE</small><h3>'+val(dest.icao_code)+'</h3><p>'+val(dest.name)+'</p></div><div><small>APPAREIL</small><h3>'+val(aircraft.icaocode||aircraft.name)+'</h3><p>'+val(g.flight_number||g.callsign)+'</p></div></div>'+
      '<p><b>Route :</b> '+val(g.route)+' · <b>Altitude :</b> '+val(g.initial_altitude)+' · <b>Durée prévue :</b> '+val(times.est_time_enroute)+'</p>'+
      '<p class="fineprint">Dernier OFP généré '+val(generated)+'. Ce document est un plan de vol, pas la preuve d’un vol effectué.</p>';
  }catch(e){el.innerHTML='<p>Lecture automatique impossible depuis ce navigateur (compte introuvable, réseau ou restrictions SimBrief). <a href="https://dispatch.simbrief.com/" target="_blank" rel="noopener noreferrer">Ouvrir SimBrief ↗</a></p><small>'+esc(e.message)+'</small>';}
  finally{button.disabled=false;}
}
$('#simbrief-refresh')?.addEventListener('click',loadSimbriefFlight);
async function showPublishedSimbrief(){
 const el=$('#simbrief-flight-data');if(!el)return;
 try{
  const response=await fetch('simbrief_last.json',{cache:'no-store'});if(!response.ok)throw Error('Not published');
  const d=await response.json();if(d.state!=='ok'||!d.origin?.icao||!d.destination?.icao)throw Error('No OFP');
  const v=x=>esc(x||'—');
  el.innerHTML='<div class="tile-grid"><div><small>🛫 DÉPART</small><h3>'+v(d.origin.icao)+'</h3><p>'+v(d.origin.name)+'</p></div><div><small>🛬 ARRIVÉE</small><h3>'+v(d.destination.icao)+'</h3><p>'+v(d.destination.name)+'</p></div><div><small>✈ APPAREIL</small><h3>'+v(d.aircraft)+'</h3><p>'+v(d.flight_number)+'</p></div></div>'+
  '<p><b>PLAN DE VOL :</b> '+v(d.route)+'</p><p><b>Altitude :</b> '+v(d.altitude)+' · <b>Temps prévu :</b> '+v(d.enroute_time)+'</p>'+
  '<p class="fineprint">Dernier OFP généré sur SimBrief · collecte '+v(d.retrieved_at)+'. Planification, pas confirmation de vol effectué.</p>';
 }catch(e){el.innerHTML='<p class="fineprint">Dernier OFP non encore disponible. Utilise « Consulter SimBrief » pour essayer une lecture directe.</p>';}
}
async function showSayIntentionsCareer(){
 const el=$('#sayintentions-career-data');if(!el)return;
 try{
  const r=await fetch('sayintentions_career.json',{cache:'no-store'});if(!r.ok)throw Error('Unavailable');
  const d=await r.json();const value=x=>esc(x??'—');
  if(d.rank==null&&d.flight_hours==null){el.innerHTML='<p class="fineprint">Le profil public est connu, mais les statistiques ne sont pas encore lisibles automatiquement. <a href="https://pilots.sayintentions.ai/u/Mathis" target="_blank" rel="noopener noreferrer">Voir le profil officiel ↗</a></p>';return;}
  el.innerHTML='<div class="tile-grid"><div><small>GRADE</small><div class="si-rank-line">'+(d.rank_badge==='sayintentions-rank.svg'?'<img class="si-rank-badge" src="https://pilots.sayintentions.ai/p2d/assets/images/rankings/senior_first_officer.svg" alt="Insigne de grade SayIntentions" loading="lazy">':'')+'<h3>'+value(d.rank)+'</h3></div></div><div><small>HEURES IFR</small><h3>'+value(d.ifr_hours)+'</h3></div><div><small>HEURES VFR</small><h3>'+value(d.vfr_hours)+'</h3></div><div><small>VOLS EFFECTUÉS</small><h3>'+value(d.total_flights)+'</h3></div><div><small>AÉROPORTS VISITÉS</small><h3>'+value(d.airports_visited)+'</h3></div></div><p class="fineprint">'+(d.state==='ok'?'Données publiques récupérées automatiquement.':'Données issues de la capture du 25 octobre 2026 ; actualisation automatique non encore opérationnelle.')+' Dernière vérification : '+value(d.verified_at)+'. <a href="https://pilots.sayintentions.ai/u/Mathis" target="_blank" rel="noopener noreferrer">Profil officiel ↗</a></p>';
  const flights=Array.isArray(d.recent_flights)?d.recent_flights:[];
  const rows=flights.map(f=>'<tr><td><strong>'+value(f.id)+'</strong></td><td>'+value(f.aircraft)+'</td><td>'+value(f.when)+'</td><td><b>'+value(f.origin)+'</b></td><td><b>'+value(f.destination)+'</b></td><td><span class="si-flight-rules">'+value(f.rules)+'</span></td><td>'+value(f.duration)+'</td></tr>').join('');
  el.innerHTML+='<div class="si-flights"><div class="si-flights-heading"><h3>✈ Mes derniers vols</h3><a href="https://pilots.sayintentions.ai/u/Mathis" target="_blank" rel="noopener noreferrer">Tous les détails sur Gate 404 ↗</a></div>'+(rows?'<div class="si-flights-scroll"><table><thead><tr><th>Vol</th><th>Avion</th><th>Quand</th><th>Départ</th><th>Arrivée</th><th>Règles</th><th>Durée</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="fineprint">Dernière lecture des vols : '+value(d.flights_checked_at)+'.</p>':'<p class="fineprint">Historique des vols en attente de récupération automatique.</p>')+'</div>';
 }catch(e){el.innerHTML='<p class="fineprint">Statistiques SayIntentions en attente de première collecte. <a href="https://pilots.sayintentions.ai/u/Mathis" target="_blank" rel="noopener noreferrer">Consulter le profil ↗</a></p>';}
}
showSayIntentionsCareer();
showPublishedSimbrief();

['airport-search','region-filter','status-filter'].forEach(id=>$('#'+id).addEventListener(id==='airport-search'?'input':'change',renderAirports));['software-search','software-filter'].forEach(id=>{const el=$('#'+id);if(el)el.addEventListener(id==='software-search'?'input':'change',renderSoftware)});init();

/* État de la publication : interroge les dernières exécutions publiques du workflow. */
async function refreshBuildStatus(){
  const badge=document.getElementById('build-status'), label=document.getElementById('build-status-text');
  if(!badge||!label)return;
  try{
    const response=await fetch('https://api.github.com/repos/Matthisfr/journal-msfs/actions/workflows/journal.yml/runs?per_page=5',{cache:'no-store',headers:{Accept:'application/vnd.github+json'}});
    if(!response.ok)throw new Error('GitHub API '+response.status);
    const data=await response.json();
    const run=(data.workflow_runs||[])[0];
    if(!run)throw new Error('Aucune exécution disponible');
    const running=run.status!=='completed';
    const ok=!running&&run.conclusion==='success';
    const kind=running?'running':ok?'ok':'error';
    const wording=running?'Mise à jour…':ok?'Journal à jour':'Échec mise à jour';
    badge.className='build-status build-status-'+kind;
    label.textContent=wording;
    badge.title=wording+' — '+new Date(run.created_at).toLocaleString('fr-FR')+' — ouvrir GitHub Actions';
    badge.setAttribute('aria-label',wording);
    badge.href=run.html_url||'https://github.com/Matthisfr/journal-msfs/actions/workflows/journal.yml';
  }catch(err){
    badge.className='build-status build-status-unknown';
    label.textContent='État indisponible';
    badge.title='Impossible de consulter GitHub Actions pour le moment';
    badge.setAttribute('aria-label','État de publication indisponible');
  }
}
if(typeof window!=='undefined'&&typeof window.fetch==='function')refreshBuildStatus();
if(typeof window!=='undefined'&&typeof window.setInterval==='function')window.setInterval(refreshBuildStatus,90000);
