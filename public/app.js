'use strict';
const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const isSafeUrl=u=>{try{const x=new URL(u);return ['https:','http:'].includes(x.protocol)?x.href:'#'}catch{return '#'}};
const localDate=s=>{if(!s)return '—';const d=new Date(s.length===10?s+'T12:00:00Z':s);return isNaN(d)?s:new Intl.DateTimeFormat('fr-FR',{day:'2-digit',month:'short',year:'numeric',timeZone:'Europe/Paris'}).format(d)};
const localDateTime=s=>{if(!s)return 'Non exécutée';const d=new Date(s);return isNaN(d)?s:new Intl.DateTimeFormat('fr-FR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',timeZone:'Europe/Paris'}).format(d)};
let airports=[], status={}, editorial={};
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
  if(!a||!b)return 'different';
  const n=Math.max(a.length,b.length);
  for(let i=0;i<n;i++){const x=Number(a[i]||0),y=Number(b[i]||0);if(y>x)return 'update';if(y<x)return 'ahead'}
  return 'current';
}
function renderAirports(){
  const q=$('#airport-search').value.trim().toLowerCase(),region=$('#region-filter').value,st=$('#status-filter').value;
  const checkedDate=String(status.versions_checked_at||'').slice(0,10);
  const isVerified=a=>!!a.server_version&&a.version_check_state==='verified'&&a.version_checked_at===checkedDate;
  const verified=airports.filter(isVerified);
  const updates=verified.filter(a=>compareVersions(a.installed,a.server_version)==='update');
  $('#verified-count').textContent=verified.length;
  $('#updates-count').textContent=updates.length;
  const matches=airports.filter(a=>(!q||[a.icao,a.original,a.name,a.publisher,a.folder,a.country,a.region,a.installed,a.server_version].join(' ').toLowerCase().includes(q))&&(!region||(a.region||a.country)===region)&&(!st||(st==='verified'?isVerified(a):st==='update'?isVerified(a)&&compareVersions(a.installed,a.server_version)==='update':a.status===st)));
  $('#airport-count').textContent=`${matches.length} scène${matches.length>1?'s':''} affichée${matches.length>1?'s':''} sur ${airports.length}`;
  const cls={'UNK-P':'p','UNK-V':'v','UNK-C':'c','UNK-S':'s','verified':'ok'};
  $('#airport-body').innerHTML=matches.map(a=>{
    const st=a.status||'UNK-V';
    const source=a.source_url?`<a href="${esc(isSafeUrl(a.source_url))}" target="_blank" rel="noopener noreferrer">Fiche éditeur ↗</a>`:'';
    const comp=a.server_version?compareVersions(a.installed,a.server_version):'unknown';
    const compLabel=comp==='update'?'MISE À JOUR':comp==='current'?'À JOUR':comp==='ahead'?'INSTALLÉE + RÉCENTE':'À COMPARER';
    const compClass=comp==='update'?'flag-s':comp==='current'?'flag-ok':'flag-v';
    const online=isVerified(a)?`<b>${esc(a.server_version)}</b><small><span class="flag ${compClass}">${compLabel}</span></small><small>${source}</small><small>Vérifiée le ${esc(localDate(a.version_checked_at))}</small>`:a.server_version?`<b>${esc(a.server_version)}</b><small>Dernière version connue, non revalidée aujourd’hui</small><small><span class="flag flag-${cls[st]||'v'}">${esc(st==='verified'?'UNK-V':st)}</span></small><small>${source}</small><small>Dernière confirmation : ${esc(localDate(a.version_checked_at))}</small>`:`<span class="flag flag-${cls[st]||'v'}">${esc(st)}</span>${source?`<small>${source}</small>`:''}`;
    return `<tr><td><span class="code">${esc(a.icao)}</span>${a.original!==a.icao?`<small>Source : ${esc(a.original)}</small>`:''}</td><td><b>${esc(a.name)}</b><small>${esc(a.note||a.folder||'')}</small></td><td>${esc(a.publisher)}</td><td><b>${esc(a.installed||'Non renseignée')}</b></td><td>${online}</td></tr>`;
  }).join('')||'<tr><td colspan="5">Aucune scène correspondant à ces filtres.</td></tr>';
}
function renderMap(){
  const slot=$('#google-map');
  if(!slot)return;
  const url=(window.MSFS_MAP_URL||'').trim();
  const m=url.match(/[?&]mid=([a-zA-Z0-9_-]+)/);
  if(m&&/^https:\/\/(?:www\.)?google\.com\/maps\/d\//.test(url)){
    slot.innerHTML=`<p class="map-caption map-open"><a target="_blank" rel="noopener noreferrer" href="https://www.google.com/maps/d/viewer?mid=${encodeURIComponent(m[1])}">↗ Ouvrir ma carte complète dans Google Maps</a></p><iframe title="Carte personnelle Google My Maps des aéroports" loading="eager" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen src="https://www.google.com/maps/d/embed?mid=${encodeURIComponent(m[1])}&ehbc=2E312F"></iframe><p class="map-caption">Si la carte ne se charge pas dans Safari, utilise le lien ci-dessus pour la consulter directement.</p>`;
  }else{
    slot.innerHTML='<div class="map-placeholder"><strong>Ta carte Google My Maps</strong><p>Emplacement prêt. Il manque uniquement le lien de partage de ta carte pour afficher tes aéroports ici.</p><a href="https://www.google.com/maps/d/" target="_blank" rel="noopener noreferrer">Accéder à Google My Maps ↗</a></div>';
  }
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
function newsMarkup(a){
  return '<article class="news-card"><div class="news-meta">'+esc(a.category||'ACTUALITÉS')+' · '+esc(localDate(a.date))+(a.new?'<span class="new-tag">NEWS</span>':'')+'</div><div class="news-heading">'+topicBadge(a)+'<h3>'+esc(a.title)+'</h3></div>'+(a.summary?'<p>'+esc(a.summary)+'</p>':'')+(a.impact?'<div class="news-impact"><b>Impact / action :</b> '+esc(a.impact)+'</div>':'')+'<div class="news-source"><a href="'+esc(isSafeUrl(a.url))+'" target="_blank" rel="noopener noreferrer">'+esc(a.source||'Source officielle')+' ↗</a></div></article>';
}
function renderNews(){
  const editorialNews=editorial.news||[];
  const superseded=new Set(editorialNews.flatMap(a=>a.supersedes||[]));
  const a=[...editorialNews,...(status.news||[]).filter(x=>!superseded.has(x.url))]
    .filter((x,i,all)=>all.findIndex(y=>y.url===x.url)===i)
    .sort((x,y)=>String(y.date||'').localeCompare(String(x.date||'')));
  $('#news-container').innerHTML=a.length?a.map(newsMarkup).join(''):'<div class="empty"><strong>Aucune nouveauté vérifiée</strong>Le site ne publie pas d’annonce sans date ni source vérifiable.</div>';
  $('#home-news').innerHTML=a.slice(0,3).map(x=>'<article><div class="home-news-row">'+topicBadge(x)+'<div class="home-news-content"><small>'+esc(x.category||'Actualités')+' · '+esc(localDate(x.date))+'</small><strong>'+esc(x.title)+'</strong><a href="'+esc(isSafeUrl(x.url))+'" target="_blank" rel="noopener noreferrer">Source officielle ↗</a></div></div></article>').join('')||'<p class="muted">Aucune actualité sourcée pour le moment.</p>';
}
function renderHardwareNews(){const a=editorial.hardware||[];$('#hardware-news').innerHTML=a.length?'<div class="sectionbar"><h2>Actualités du matériel</h2></div><div class="news-grid">'+a.map(newsMarkup).join('')+'</div>':''}
function renderStatus(){if(status.edition)$('#edition-date').textContent=new Date(status.edition+'T12:00:00Z').toLocaleDateString('fr-FR',{day:'numeric',month:'long',year:'numeric',timeZone:'Europe/Paris'}).toUpperCase();const done=!!status.last_run;const dateTime=new Intl.DateTimeFormat('fr-FR',{day:'2-digit',month:'long',year:'numeric',hour:'2-digit',minute:'2-digit',timeZone:'Europe/Paris'});$('#home-updated').textContent=done?'Le '+dateTime.format(new Date(status.last_run)):'En attente de la première collecte';$('#home-editorial-updated').textContent=editorial.last_updated?localDate(editorial.last_updated):'Non actualisées';$('#last-check').textContent=done?'Collecte : '+localDateTime(status.last_run):'Données de lancement · non actualisées';$('#sync-label').textContent=done?'DERNIÈRE COLLECTE : '+localDateTime(status.last_run):'COLLECTE AUTOMATIQUE NON ENCORE EXÉCUTÉE';$('#dashboard-timestamp').textContent=done?'Dernier passage : '+localDateTime(status.last_run):'Édition de lancement';$('#run-state').textContent=done?'Collecte exécutée':'Automatisation non encore exécutée';$('#run-detail').textContent=done?'Voir le détail des sources ci-dessous.':'La collecte doit être activée après publication sur GitHub.';$('#status-dot').classList.toggle('good',done&&status.source_status?.metar==='ok');$('#footer-updated').textContent=done?'Dernière collecte : '+localDateTime(status.last_run):'Publication et automatisation non encore activées';const src=status.source_status||{};const parts=[['Météo METAR',src.metar],['Prévisions TAF',src.taf],['Actualités officielles',src.official_news],['Versions des scènes',airports.some(a=>a.server_version)?'partial':src.airport_versions],['Éditorial ChatGPT',editorial.last_updated?'ok':'non_executed']];$('#source-health').innerHTML=parts.map(([name,s])=>`<div class="health ${s==='ok'?'ok':''}"><strong>${esc(name)}</strong><span>${s==='ok'?'Collecte réussie':s==='non_verified'?'Non vérifiées':s==='error'?'Échec de collecte':s==='partial'?'Partiellement vérifiées':'En attente'}</span></div>`).join('')}
async function init(){try{const [ar,sr,er]=await Promise.all([fetch('airports.json',{cache:'no-store'}),fetch('status.json',{cache:'no-store'}),fetch('editorial.json',{cache:'no-store'})]);if(!ar.ok||!sr.ok||!er.ok)throw new Error('Fichiers de données indisponibles');[airports,status,editorial]=await Promise.all([ar.json(),sr.json(),er.json()]);$('#count-scenes').textContent=airports.length;$('#count-codes').textContent=new Set(airports.map(x=>x.icao)).size;$('#airport-total').textContent=airports.length+' SCÈNES';const regions=[...new Set(airports.map(a=>a.region||a.country).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'fr'));$('#region-filter').innerHTML='<option value="">Toutes les régions</option>'+regions.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');renderAirports();renderStatus();renderWeather();renderNews();renderHardwareNews();}catch(e){$('#run-state').textContent='Données indisponibles';$('#run-detail').textContent='Impossible de charger les fichiers JSON.';$('#weather-container').innerHTML='<div class="error">Chargement des données impossible. Ouvre le site via un serveur web.</div>';$('#airport-count').textContent='Erreur de chargement';console.error(e)}if(location.hash)switchView(location.hash.slice(1))}
['airport-search','region-filter','status-filter'].forEach(id=>$('#'+id).addEventListener(id==='airport-search'?'input':'change',renderAirports));init();
