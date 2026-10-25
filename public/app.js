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
  const matches=airports.filter(a=>(!q||[a.icao,a.original,a.name,a.publisher,a.folder,a.country,a.region,a.installed,a.server_version].join(' ').toLowerCase().includes(q))&&(!region||(a.region||a.country)===region)&&(!st||(st==='verified'?isVerified(a):st==='update'?isVerified(a)&&a.version_comparison==='update':a.status===st)));
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
  const change=a.changelog_url?'<div class="news-impact"><b>Version : '+esc(a.version_before||'—')+' → '+esc(a.version_after||'—')+'</b>'+
    (a.details?'<details class="changelog-details"><summary>Afficher les modifications détaillées</summary><p>'+esc(a.details)+'</p></details>':'')+
    '<a href="'+esc(isSafeUrl(a.changelog_url))+'" target="_blank" rel="noopener noreferrer">Consulter le changelog officiel complet ↗</a></div>':'';
  return '<article class="news-card"><div class="news-meta">'+esc(a.category||'ACTUALITÉS')+' · '+esc(localDate(a.date))+
    (a.new?'<span class="new-tag">NEWS</span>':'')+'</div><div class="news-heading">'+topicBadge(a)+
    '<h3>'+esc(a.title)+'</h3></div>'+(a.summary?'<p>'+esc(a.summary)+'</p>':'')+
    (a.impact?'<div class="news-impact"><b>Impact / action :</b> '+esc(a.impact)+'</div>':'')+change+
    '<div class="news-source"><a href="'+esc(isSafeUrl(a.url))+'" target="_blank" rel="noopener noreferrer">'+esc(a.source||'Source officielle')+' ↗</a></div></article>';
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
    const tag=fresh?'<span class="new-tag">NEWS</span>':ok?'<span class="flag flag-ok">VÉRIFIÉ</span>':'<span class="flag flag-v">UNKNOWN</span>';
    const preview=x.preview_version?'<small>Préversion : '+esc(x.preview_version)+'</small>':'';
    const last=x.previous_version?'<small>Précédente : '+esc(x.previous_version)+'</small>':'';
    return '<tr><td><strong>'+esc(x.name)+'</strong><small>'+esc(x.group)+'</small></td>'+
      '<td><strong>'+esc(x.version||'Non publiée')+'</strong>'+preview+'</td>'+
      '<td>'+tag+last+'<small>'+esc(x.reason||'')+'</small></td>'+
      '<td><a href="'+esc(isSafeUrl(x.version_url||x.source_url))+'" target="_blank" rel="noopener noreferrer">Source officielle ↗</a>'+
      (fresh?'<small>Changelog complet dans <a href="#nouveautes" data-software-news="1">Nouveautés</a></small>':'')+
      '<small>Contrôle : '+esc(localDateTime(x.checked_at))+'</small></td></tr>';
  }).join('')||'<tr><td colspan="4">Aucun logiciel correspondant.</td></tr>';
  $$('[data-software-news]').forEach(el=>el.addEventListener('click',e=>{e.preventDefault();switchView('nouveautes')}));
}
function renderHardwareGallery(){
  const el=$('#hardware-gallery');if(!el)return;
  el.innerHTML=(Array.isArray(hardware)?hardware:[]).map(x=>{
    const photo=hardwareImages[x.id]||{};
    const picture=photo.state==='photo'&&photo.path?
      '<img class="hardware-photo" loading="lazy" decoding="async" src="'+esc(photo.path)+'" alt="Photographie du matériel '+esc(x.name)+'" onerror="this.style.display=&#39;none&#39;;this.nextElementSibling.hidden=false">'+
      '<span class="hardware-no-photo" hidden>Photographie momentanément indisponible</span>':
      '<span class="hardware-no-photo">Photo produit non disponible</span>';
    return '<article class="hardware-card hardware-device">'+
      '<div class="hardware-image">'+picture+'</div>'+
      '<div class="overline">'+esc(x.ownership==='Possédé'?'DANS TON COCKPIT':'MATÉRIEL ATTENDU')+'</div>'+
      '<h3>'+esc(x.name)+'</h3>'+
      '<p>'+esc(x.ownership==='Possédé'?'Matériel possédé · suivi SimAppPro et Fenix.':'Sortie, disponibilité et révision à surveiller.')+'</p>'+
      '<div class="hardware-card-bottom"><span class="flag '+(x.ownership==='Possédé'?'flag-ok':'flag-v')+'">'+esc(x.ownership)+'</span>'+
      '<a href="'+esc(isSafeUrl(x.official_url))+'" target="_blank" rel="noopener noreferrer">WINCTRL ↗</a></div>'+
      (photo.state==='photo'?'<small class="photo-credit">'+esc(photo.source||'Photo de produit')+'</small>':'')+
      '</article>';
  }).join('')||'<p>Inventaire matériel indisponible.</p>';
}
function renderHardwareNews(){const a=editorial.hardware||[];$('#hardware-news').innerHTML=a.length?'<div class="sectionbar"><h2>Actualités du matériel</h2></div><div class="news-grid">'+a.map(newsMarkup).join('')+'</div>':''}
function renderStatus(){if(status.edition)$('#edition-date').textContent=new Date(status.edition+'T12:00:00Z').toLocaleDateString('fr-FR',{day:'numeric',month:'long',year:'numeric',timeZone:'Europe/Paris'}).toUpperCase();const done=!!status.last_run;const dateTime=new Intl.DateTimeFormat('fr-FR',{day:'2-digit',month:'long',year:'numeric',hour:'2-digit',minute:'2-digit',timeZone:'Europe/Paris'});$('#home-updated').textContent=done?'Le '+dateTime.format(new Date(status.last_run)):'En attente de la première collecte';$('#home-editorial-updated').textContent=editorial.last_updated?localDate(editorial.last_updated):'Non actualisées';$('#last-check').textContent=done?'Collecte : '+localDateTime(status.last_run):'Données de lancement · non actualisées';$('#sync-label').textContent=done?'DERNIÈRE COLLECTE : '+localDateTime(status.last_run):'COLLECTE AUTOMATIQUE NON ENCORE EXÉCUTÉE';$('#dashboard-timestamp').textContent=done?'Dernier passage : '+localDateTime(status.last_run):'Édition de lancement';$('#run-state').textContent=done?'Collecte exécutée':'Automatisation non encore exécutée';$('#run-detail').textContent=done?'Voir le détail des sources ci-dessous.':'La collecte doit être activée après publication sur GitHub.';$('#status-dot').classList.toggle('good',done&&status.source_status?.metar==='ok');$('#footer-updated').textContent=done?'Dernière collecte : '+localDateTime(status.last_run):'Publication et automatisation non encore activées';const src=status.source_status||{};const parts=[['Météo METAR',src.metar],['Prévisions TAF',src.taf],['Actualités officielles',src.official_news],['Versions des scènes',airports.some(a=>a.server_version)?'partial':src.airport_versions],['Éditorial ChatGPT',editorial.last_updated?'ok':'non_executed']];$('#source-health').innerHTML=parts.map(([name,s])=>`<div class="health ${s==='ok'?'ok':''}"><strong>${esc(name)}</strong><span>${s==='ok'?'Collecte réussie':s==='non_verified'?'Non vérifiées':s==='error'?'Échec de collecte':s==='partial'?'Partiellement vérifiées':'En attente'}</span></div>`).join('')}
async function init(){try{const [ar,sr,er,sv,hc,hi]=await Promise.all(['airports.json','status.json','editorial.json','software_versions.json','hardware_catalog.json','hardware-images.json'].map(p=>fetch(p,{cache:'no-store'}).catch(()=>null)));if(!ar?.ok||!sr?.ok||!er?.ok)throw new Error('Fichiers de données indisponibles');[airports,status,editorial]=await Promise.all([ar.json(),sr.json(),er.json()]);software=sv?.ok?await sv.json():{items:[]};hardware=hc?.ok?await hc.json():[];hardwareImages=hi?.ok?await hi.json():{};$('#count-scenes').textContent=airports.length;$('#count-codes').textContent=new Set(airports.map(x=>x.icao)).size;$('#airport-total').textContent=airports.length+' SCÈNES';const regions=[...new Set(airports.map(a=>a.region||a.country).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'fr'));$('#region-filter').innerHTML='<option value="">Toutes les régions</option>'+regions.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');renderAirports();renderStatus();renderWeather();renderNews();renderHardwareNews();renderSoftware();renderHardwareGallery();}catch(e){$('#run-state').textContent='Données indisponibles';$('#run-detail').textContent='Impossible de charger les fichiers JSON.';$('#weather-container').innerHTML='<div class="error">Chargement des données impossible. Ouvre le site via un serveur web.</div>';$('#airport-count').textContent='Erreur de chargement';console.error(e)}if(location.hash)switchView(location.hash.slice(1))}
['airport-search','region-filter','status-filter'].forEach(id=>$('#'+id).addEventListener(id==='airport-search'?'input':'change',renderAirports));['software-search','software-filter'].forEach(id=>{const el=$('#'+id);if(el)el.addEventListener(id==='software-search'?'input':'change',renderSoftware)});init();
