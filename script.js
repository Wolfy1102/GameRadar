const $ = (id) => document.getElementById(id);
const searchInput = $('search'), regionSelect = $('region'), searchForm = $('searchForm');
const searchButton = $('searchButton'), gamesContainer = $('games');
let currentUser = null, csrfToken = '', authMode = 'login';
const providerNames = {steam:'Steam',epic:'Epic Games',gog:'GOG',xbox:'Xbox',psn:'PlayStation',nintendo:'Nintendo',ea:'EA app',ubisoft:'Ubisoft',bnet:'Battle.net'};

function escapeHtml(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c])); }
function showMessage(title, message, error=false) { gamesContainer.innerHTML = `<div class="empty-state ${error?'error-state':''}"><h3>${escapeHtml(title)}</h3><p>${escapeHtml(message)}</p></div>`; }
function formatPrice(item) {
  if (item.price === null || item.price === undefined) return 'Preis nicht verfügbar';
  const amount = Number(item.price); if (!Number.isFinite(amount)) return `${item.price} ${item.currency||''}`;
  try { return new Intl.NumberFormat('de-DE',{style:'currency',currency:item.currency||'EUR'}).format(amount); }
  catch { return `${amount.toFixed(2)} ${item.currency||'EUR'}`; }
}
function renderGames(items) {
  if (!items.length) return showMessage('Keine Treffer gefunden.','Versuche einen anderen Suchbegriff.');
  gamesContainer.innerHTML = items.map(item => {
    const name=escapeHtml(item.name), image=escapeHtml(item.image||'');
    const provider=providerNames[item.provider]||escapeHtml(item.provider)||'Store';
    const discount=Number(item.discount), badge=Number.isFinite(discount)&&discount>0?`<span class="deal-badge">-${discount}%</span>`:'';
    const link=/^https:\/\//i.test(item.url||'')?item.url:'#';
    return `<article class="game-card"><div class="game-art">${badge}<img class="game-image" src="${image}" alt="${name}" loading="lazy" onerror="this.style.display='none'"></div><div class="game-info"><div class="store-label">${escapeHtml(provider)}</div><h3 title="${name}">${name}</h3><div class="game-bottom"><span class="game-price">${escapeHtml(formatPrice(item))}</span><a class="game-link" href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">VIEW DEAL ↗</a></div></div></article>`;
  }).join('');
}
function setAuthMode(mode) {
  authMode=mode; $('authTitle').innerHTML=mode==='login'?'Welcome <span>back.</span>':'Join the <span>radar.</span>';
  $('nameWrap').hidden=mode==='login'; $('authName').required=mode==='register';
  $('authPassword').autocomplete=mode==='login'?'current-password':'new-password';
  $('authSubmit').textContent=mode==='login'?'ANMELDEN':'KONTO ERSTELLEN'; $('authMessage').textContent='';
  document.querySelectorAll('.auth-tab').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
}
function openAuth(mode='login') { setAuthMode(mode); $('authModal').hidden=false; $('authEmail').focus(); }
function closeAuth() { $('authModal').hidden=true; }
function updateAccount() {
  const button=$('accountButton'), status=$('accountStatus'), owner=$('ownerPanel');
  if (!currentUser) { button.textContent='LOGIN / SIGN UP'; status.hidden=true; owner.hidden=true; return; }
  button.textContent='LOGOUT'; status.hidden=false;
  status.innerHTML=`Angemeldet als <b>${escapeHtml(currentUser.name)}</b> · ${escapeHtml(currentUser.tier_name)}${currentUser.role==='owner'?' · OWNER':''}`;
  owner.hidden=currentUser.role!=='owner';
  $('searchButton').disabled=false;
}
async function api(url, options={}) {
  const headers={'Content-Type':'application/json',...(options.headers||{})};
  if (options.method==='POST' && csrfToken && !['/api/login','/api/register'].includes(url)) headers['X-CSRF-Token']=csrfToken;
  const response=await fetch(url,{...options,headers});
  const data=await response.json().catch(()=>({message:'Ungültige Serverantwort.'}));
  if(!response.ok) throw new Error(data.message||`Serverfehler (${response.status})`);
  return data;
}
async function loadSession() {
  try { const data=await api('/api/me'); currentUser=data.user; csrfToken=data.csrf||''; }
  catch { currentUser=null; csrfToken=''; }
  updateAccount();
}
async function authSubmit(event) {
  event.preventDefault(); const button=$('authSubmit'); button.disabled=true; $('authMessage').textContent='';
  try {
    const payload={email:$('authEmail').value.trim(),password:$('authPassword').value};
    if(authMode==='register') payload.name=$('authName').value.trim();
    const data=await api(authMode==='login'?'/api/login':'/api/register',{method:'POST',body:JSON.stringify(payload)});
    currentUser=data.user; csrfToken=data.csrf; updateAccount(); closeAuth(); $('authForm').reset();
    showMessage('Radar bereit.',`Du bist als ${currentUser.name} angemeldet. Suche nach deinem nächsten Deal.`);
  } catch(error) { $('authMessage').textContent=error.message; }
  finally { button.disabled=false; }
}
async function logout() {
  try { await api('/api/logout',{method:'POST',body:'{}'}); } catch(error) { console.warn(error); }
  currentUser=null; csrfToken=''; updateAccount(); showMessage('Abgemeldet.','Dein Radar wartet beim nächsten Login.');
}
async function searchGames(event) {
  if(event) event.preventDefault(); const term=searchInput.value.trim();
  if(!term) return showMessage('Ready when you are.','Gib oben einen Spieletitel ein und starte den Radar.');
  if(!currentUser) { openAuth('login'); $('authMessage').textContent='Bitte melde dich an, um die Suche zu nutzen.'; return; }
  searchButton.disabled=true; searchButton.textContent='SCANNING …'; showMessage('Scanning…','GameRadar sucht verfügbare Angebote.');
  try { const params=new URLSearchParams({term,country:regionSelect.value}); const data=await api(`/api/search?${params}`); renderGames(data.items||[]); }
  catch(error) { showMessage('Radar signal lost.',error.message,true); }
  finally { searchButton.disabled=false; searchButton.innerHTML='SEARCH <span>↗</span>'; }
}
$('accountButton').addEventListener('click',()=>currentUser?logout():openAuth('login'));
$('closeAuth').addEventListener('click',closeAuth);
$('authModal').addEventListener('click',e=>{if(e.target===$('authModal'))closeAuth();});
document.querySelectorAll('.auth-tab').forEach(b=>b.addEventListener('click',()=>setAuthMode(b.dataset.mode)));
$('authForm').addEventListener('submit',authSubmit); searchForm.addEventListener('submit',searchGames);
document.querySelectorAll('[data-plan]').forEach(button=>button.addEventListener('click',()=>{
  const plan={radar:'Radar · 5 €/Monat',pro:'Pro · 10 €/Monat',ultimate:'Ultimate · 30 €/Monat'}[button.dataset.plan];
  alert(`${plan}\n\nDas ist das geplante Abo-Modell. Checkout und Zahlungen sind in dieser Version noch nicht aktiviert. Dein Owner kann Testkonten über die Owner Console freischalten.`);
}));
$('tierForm').addEventListener('submit',async e=>{
  e.preventDefault(); $('ownerMessage').textContent='Wird gespeichert…';
  try { const result=await api('/api/admin/tier',{method:'POST',body:JSON.stringify({email:$('tierEmail').value.trim(),tier:$('tierValue').value})}); $('ownerMessage').textContent=result.message; }
  catch(error) { $('ownerMessage').textContent=error.message; }
});
if('serviceWorker' in navigator) window.addEventListener('load',()=>navigator.serviceWorker.register('/service-worker.js').catch(()=>{}));
loadSession();
