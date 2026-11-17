const root=document.getElementById('gameContent');
const params=new URLSearchParams(location.search);
const name=params.get('name');
const appid=params.get('appid');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function price(x){if(x.price===null||x.price===undefined)return 'Preis nicht verfügbar';try{return new Intl.NumberFormat('de-DE',{style:'currency',currency:x.currency||'EUR'}).format(Number(x.price))}catch{return `${x.price} ${x.currency||''}`}}
function safeUrl(value){try{const u=new URL(value);return ['https:'].includes(u.protocol)?u.href:''}catch{return ''}}
async function init(){
  if(!name&&!appid){root.textContent='Kein Spiel angegeben.';return}
  try{
    const query=new URLSearchParams();if(name)query.set('name',name);if(appid)query.set('appid',appid);
    const r=await fetch(`/api/game?${query}`);const d=await r.json();if(!r.ok)throw new Error(d.message||'Spiel konnte nicht geladen werden.');
    const g=d.game, st=g.steam||{}, offers=Array.isArray(g.offers)?g.offers:[];
    document.title=`${g.name} · GameRadar`;
    const shots=st.screenshots||[], movies=st.movies||[];
    const gallery=shots.length?`<section class="game-media-section"><h2>Bilder aus dem Spiel</h2><div class="screenshot-gallery">${shots.slice(0,12).map((x,i)=>`<a href="${esc(safeUrl(x.full))}" target="_blank" rel="noopener noreferrer"><img src="${esc(safeUrl(x.thumb)||safeUrl(x.full))}" alt="${esc(g.name)} Screenshot ${i+1}" loading="lazy"></a>`).join('')}</div></section>`:'';
    const trailers=movies.length?`<section class="game-media-section"><h2>Gameplay & Trailer</h2><div class="trailer-grid">${movies.slice(0,6).map(m=>{const video=safeUrl(m.mp4)||safeUrl(m.webm),thumb=safeUrl(m.thumbnail);return `<article class="trailer-card">${video?`<video controls preload="none" poster="${esc(thumb)}"><source src="${esc(video)}" type="${video.endsWith('.webm')?'video/webm':'video/mp4'}">Dein Browser unterstützt dieses Videoformat nicht.</video>`:`<img src="${esc(thumb)}" alt="${esc(m.name)}" loading="lazy">`}<p>${esc(m.name)}</p></article>`}).join('')}</div></section>`:'';
    const description=st.description||st.short_description||'Für dieses Spiel liegt derzeit keine Beschreibung aus der Steam-Datenquelle vor.';
    root.innerHTML=`<div class="eyebrow">GAME INTELLIGENCE</div>
      <div class="detail-hero"><img class="detail-cover" src="${esc(safeUrl(st.header_image)||safeUrl(g.image))}" alt="${esc(g.name)}" onerror="this.style.display='none'"><div><h1 class="page-title">${esc(g.name)}</h1><p class="detail-description-short">${esc(st.short_description||'Spielübersicht und verfügbare Angebotsdaten.')}</p><div class="detail-meta">${(st.genres||[]).map(x=>`<span class="meta-chip">${esc(x)}</span>`).join('')} ${st.release_date?`<span class="meta-chip">Release: ${esc(st.release_date)}</span>`:''}${st.developers?.length?`<span class="meta-chip">Studio: ${esc(st.developers.join(', '))}</span>`:''}</div><h2>${price(st.price!==null&&st.price!==undefined?st:g)}</h2><div class="detail-actions"><button class="primary-action" id="favButton">☆ Zu Favoriten hinzufügen</button>${safeUrl(st.steam_url||g.url)?`<a class="small-action" href="${esc(safeUrl(st.steam_url||g.url))}" target="_blank" rel="noopener noreferrer">Steam Store öffnen ↗</a>`:''}</div><p id="favMessage" role="status"></p></div></div>
      ${gallery}${trailers}<section class="game-media-section"><h2>Über dieses Spiel</h2><p class="game-description">${esc(description)}</p></section>
      <section class="owner-section"><h2>Preis- und Angebotsübersicht</h2><div class="detail-offers">${offers.length?offers.map(o=>`<div class="offer-row"><div><b>${esc(o.store_name||o.store||o.provider_name||'Store')}</b><div class="section-note">${esc(o.drm||o.region||'Details nicht verfügbar')}</div></div><strong>${price(o)}</strong>${safeUrl(o.url||o.link)?`<a href="${esc(safeUrl(o.url||o.link))}" target="_blank" rel="noopener noreferrer">Angebot ↗</a>`:'<span class="section-note">Kein Link</span>'}</div>`).join(''):'Für dieses Spiel liefert die Preisquelle aktuell keine einzelnen Angebotsdetails.'}</div></section>
      <p class="plans-note">Spieldaten, Bilder und Videos: Steam Store. Angebotsdaten: <a href="${esc(safeUrl(d.attribution?.url)||'https://superduperbundle.com/') }" target="_blank" rel="noopener noreferrer">${esc(d.attribution?.text||'SuperDuperBundle')}</a>. Angaben werden nur angezeigt, wenn die Datenquelle sie liefert.</p>`;
    document.getElementById('favButton').onclick=async()=>{try{const r=await fetch('/api/favorites',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:g.name})});const x=await r.json();if(!r.ok)throw new Error(x.message||'Bitte einloggen.');document.getElementById('favMessage').textContent='Spiel wurde zu deinen Favoriten hinzugefügt.'}catch(e){document.getElementById('favMessage').textContent=e.message}};
  }catch(e){root.innerHTML=`<h2>Keine Spieldetails verfügbar.</h2><p>${esc(e.message)}</p>`}
}
init();
