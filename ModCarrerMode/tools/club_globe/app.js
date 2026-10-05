(() => {
  const root = document.getElementById('ff-club-globe');
  const data = JSON.parse(document.getElementById('ff-globe-data').textContent);
  const $ = selector => root.querySelector(selector);
  const canvas = $('.ff-world canvas'), ctx = canvas.getContext('2d'), pin = $('.ff-pin');
  const controlHints = $('[data-control-hints]'), feedback = $('[data-feedback]');
  const projection = d3.geoOrthographic().clipAngle(90).precision(0.3);
  const graticule = d3.geoGraticule().step([15, 15])();
  const path = d3.geoPath(projection, ctx);
  const textureCanvas = document.createElement('canvas');
  textureCanvas.width = 128; textureCanvas.height = 128;
  const textureContext = textureCanvas.getContext('2d');
  const textureImage = textureContext.createImageData(128, 128);
  let textureSeed = 8128;
  for (let i = 0; i < textureImage.data.length; i += 4) {
    textureSeed = (textureSeed * 1664525 + 1013904223) >>> 0;
    const grain = 90 + ((textureSeed >>> 24) & 63);
    textureImage.data[i] = grain;
    textureImage.data[i + 1] = grain + 10;
    textureImage.data[i + 2] = grain + 19;
    textureImage.data[i + 3] = 13 + ((textureSeed >>> 16) & 19);
  }
  textureContext.putImageData(textureImage, 0, 0);
  const landTexture = ctx.createPattern(textureCanvas, 'repeat');
  let countryId = data.defaultCountryId, leagueId = data.defaultLeagueId;
  let selectedId = data.defaultTeamId ?? null, camera = { ...data.defaultView };
  let width = 0, height = 0, frame = 0, drag = null;
  const choiceOrder = ['country', 'league', 'team'];
  let activeChoice = 'team', feedbackTimer = 0;
  let activeGamepadIndex = null, previousPadButtons = [], padDirection = '', padRepeatAt = 0;
  let lastPadFrame = 0;
  let paused=false;const query=new URLSearchParams(location.search);
  let detailsOpen = false, activeInfoIndex = 0;const clubDetails=new Map(),clubLoads=new Set();if(data.sampleClubDetail)clubDetails.set(data.sampleClubDetail.clubId,data.sampleClubDetail);
  const country = () => data.countries.find(item => item.id === countryId) || data.countries[0];
  const countryLeagues = () => country().leagueIds
    .map(id => data.leagues.find(item => item.id === id)).filter(Boolean);
  const league = () => countryLeagues().find(item => item.id === leagueId) || countryLeagues()[0];
  const team = () => league()?.clubs.find(item => item.id === selectedId) || league()?.clubs[0];
  const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
  const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const countryAt = () => data.countries.findIndex(item => item.id === countryId);
  const leagueAt = () => countryLeagues().findIndex(item => item.id === leagueId);
  const teamAt = () => league().clubs.findIndex(item => item.id === selectedId);

  function setActiveChoice(name, moveDomFocus = false) {
    if (!choiceOrder.includes(name)) return;
    activeChoice = name;
    for (const card of root.querySelectorAll('[data-choice]')) {
      const active = card.dataset.choice === name;
      card.dataset.active = String(active);
      card.tabIndex = active ? 0 : -1;
      if (active && moveDomFocus) card.focus({ preventScroll: true });
    }
  }

  function changeActiveChoice(delta) {
    const next = (choiceOrder.indexOf(activeChoice) + delta + choiceOrder.length) % choiceOrder.length;
    setActiveChoice(choiceOrder[next], true);
  }

  function stepActiveChoice(delta) {
    if (activeChoice === 'country') cycleCountry(delta);
    else if (activeChoice === 'league') cycleLeague(delta);
    else cycleTeam(delta);
  }

  function showFeedback(message) {
    feedback.textContent = message;
    feedback.hidden = false;
    clearTimeout(feedbackTimer);
    feedbackTimer = setTimeout(() => { feedback.hidden = true; }, 1800);
  }

  function colorHex(rgb, fallback = '#1b3764') {
    if (!Array.isArray(rgb) || rgb.length < 3) return fallback;
    return `#${rgb.slice(0, 3).map(value => clamp(Number(value) || 0, 0, 255)
      .toString(16).padStart(2, '0')).join('')}`;
  }

  function teamInk(rgb) {
    if (!Array.isArray(rgb) || rgb.length < 3) return '#fff';
    const [r, g, b] = rgb.slice(0, 3).map(value => {
      const c = clamp(Number(value) || 0, 0, 255) / 255;
      return c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4;
    });
    return .2126 * r + .7152 * g + .0722 * b > .48 ? '#101820' : '#fff';
  }

  function setText(selector, value, fallback = '—') {
    const target = $(selector);
    target.textContent = value === null || value === undefined || value === '' ? fallback : value;
  }

  function renderKits(kits) {
    const list = $('[data-kit-list]');
    list.replaceChildren();
    for (const kit of kits || []) {
      const [primary, secondary, tertiary] = [kit.primary, kit.secondary, kit.tertiary]
        .map(color => colorHex(color));
      const item = document.createElement('div');
      item.className = 'ff-kit';
      const shirt = document.createElement('svg');
      shirt.setAttribute('viewBox', '0 0 120 135');
      shirt.setAttribute('role', 'img');
      shirt.setAttribute('aria-label', `${kit.name} do clube`);
      shirt.innerHTML = `<path d="M36 12 49 6h22l13 6 27 15-13 24-14-8v81H36V43l-14 8L11 27z" fill="${primary}" stroke="#ffffff40" stroke-width="2"/><path d="M49 6q11 12 22 0v14q-11 9-22 0z" fill="${secondary}"/><path d="M48 24h24v94H48z" fill="${secondary}" opacity=".88"/><path d="M16 29 35 18l10 13-17 13zM104 29 85 18 75 31l17 13z" fill="${tertiary}"/><path d="M42 118h36" stroke="${tertiary}" stroke-width="3" opacity=".8"/>`;
      const label = document.createElement('span');
      label.textContent = kit.name;
      if (kit.image) { const picture=document.createElement('img'); picture.src=kit.image; picture.alt=kit.name+' do clube'; picture.onerror=()=>picture.replaceWith(shirt); item.append(picture,label); } else item.append(shirt, label);
      list.append(item);
    }
    if (!list.children.length) list.innerHTML = '<div class="ff-stadium-placeholder">Uniformes indisponíveis</div>';
  }

  function renderHighlights(players) {
    const list = $('[data-highlight-list]');
    list.replaceChildren();
    for (const player of players || []) {
      const card = document.createElement('article');
      card.className = 'ff-highlight';card.tabIndex=0;card.setAttribute('role','button');card.dataset.navCard='';card.dataset.playerProfile=player.id;card.addEventListener('click',()=>{if(parent!==window)parent.postMessage({type:'ff-player',id:player.id,clubId:team()?.id},'*');else location.href='player.html?id='+encodeURIComponent(player.id)+'&club='+team()?.id;});
      if (player.portrait) {
        const portrait = document.createElement('img');
        portrait.src = player.portrait;
        portrait.alt = '';
        portrait.onerror = () => portrait.remove();
        card.append(portrait);
      }
      const rating = document.createElement('strong');
      rating.className = 'ff-highlight-rating';
      rating.textContent = player.overall || '—';
      const position = document.createElement('span');
      position.className = 'ff-highlight-pos';
      position.textContent = player.position || 'JOG';
      const name = document.createElement('span');
      name.className = 'ff-highlight-name';
      name.textContent = player.name;
      card.append(rating, position, name);
      list.append(card);
    }
    if (!list.children.length) list.innerHTML = '<div class="ff-stadium-placeholder">Destaques indisponíveis</div>';
  }

  function renderPitch(players, formation) {
    const list = $('[data-pitch-list]'), empty = $('[data-pitch-empty]');
    list.replaceChildren();
    setText('[data-pitch-formation]', formation ? `${formation} · SAVE` : 'FORMAÇÃO NÃO DISPONÍVEL');
    for (const player of players || []) {
      const marker = document.createElement('div');
      marker.className = 'ff-pitch-player';
      marker.style.left = `${Number(player.x) * 100}%`;
      marker.style.top = `${Number(player.y) * 100}%`;
      const portrait = document.createElement('img');
      portrait.alt = '';
      if (player.portrait) {
        portrait.src = player.portrait;
        portrait.onerror = () => portrait.remove();
      } else {
        portrait.hidden = true;
      }
      const position = document.createElement('small');
      position.textContent = player.position || 'JOG';
      const name = document.createElement('b');
      name.textContent = player.name || 'Jogador';
      marker.append(portrait, position, name);
      list.append(marker);
    }
    empty.hidden = !!players?.length;
    empty.textContent = players?.length === 11
      ? '' : 'O save não fornece onze posições táticas válidas para este clube.';
  }

  function flagFromCountryCode(code) {
    if (!/^[a-z]{2}$/i.test(code || '')) return '';
    return String.fromCodePoint(...[...code.toUpperCase()].map(letter => 127397 + letter.charCodeAt(0)));
  }

  function renderCoach(coach) {
    const card=$('[data-coach-name]').closest('[data-nav-card]');if(card){card.dataset.coachProfile='true';card.setAttribute('role','button');}
    setText('[data-coach-name]', coach?.name, 'Técnico não identificado no save');
    setText('[data-coach-country]', coach?.country, 'País não informado');
    setText('[data-coach-photo-note]', coach?.photoKind === 'official'
      ? 'Foto cadastrada para o técnico.'
      : coach?.photo ? 'Retrato estático gerado a partir do modelo do jogo.' : 'Retrato não disponível.');
    $('[data-coach-flag]').textContent = flagFromCountryCode(coach?.countryCode);
    const photo = $('[data-coach-photo]');
    const model = $('[data-coach-model]');
    setImage(photo, coach?.photo, coach?.name ? `Retrato de ${coach.name}` : 'Retrato do técnico');
    setImage(model, coach?.model, coach?.name ? `Modelo 3D nativo de ${coach.name}` : 'Modelo 3D do técnico');
    $('[data-coach-empty]').hidden = !!coach?.model;
    $('[data-coach-body]').hidden = !coach?.name && !coach?.photo && !coach?.model;
  }

  function renderHistory(rows) {
    const list = $('[data-history-list]');
    list.replaceChildren();
    for (const row of rows || []) {
      const entry = document.createElement('button');
      entry.type = 'button';
      entry.className = 'ff-history-entry';
      entry.dataset.historyEntry = '';
      entry.dataset.navCard = '';
      entry.setAttribute('aria-expanded', 'false');
      const season = document.createElement('strong');
      season.textContent = `Temporada ${row.season}`;
      const record = document.createElement('span');
      record.textContent = `${row.games} jogos · ${row.wins}V ${row.draws}E ${row.losses}D`;
      const points = document.createElement('span');
      points.className = 'ff-history-result';
      points.textContent = `${row.points} pts`;
      const details = document.createElement('span');
      details.className = 'ff-history-detail';
      details.hidden = true;
      const values = [
        ['Gols pró', row.goalsFor], ['Gols contra', row.goalsAgainst],
        ['Posição', row.tablePosition || '—'],
        ['Títulos', Number(row.leagueTrophies || 0) + Number(row.domesticTrophies || 0) + Number(row.continentalTrophies || 0)],
      ];
      for (const [label, value] of values) {
        const item = document.createElement('span');
        const number = document.createElement('b'); number.textContent = value;
        const caption = document.createElement('small'); caption.textContent = label;
        item.append(number, caption); details.append(item);
      }
      entry.append(season, record, points, details);
      list.append(entry);
    }
    if (!list.children.length) list.innerHTML = '<div class="ff-history-empty">O save não contém temporadas registradas para este clube.</div>';
  }

  function infoTargets() {
    return [...root.querySelectorAll('[data-nav-card]')].filter(target => !target.hidden);
  }

  function updateInfoHints(target){controlHints.configure({canActivate:!!target?.matches('[data-player-profile],[data-coach-profile],[data-history-entry]'),activateLabel:target?.matches('[data-history-entry]')?'Expandir / recolher':target?.matches('[data-coach-profile]')?'Perfil do treinador':'Perfil do jogador'});}
  function focusInfoTarget(delta = 0) {
    const targets = infoTargets();
    if (!targets.length) return;
    const active = targets.indexOf(document.activeElement);
    activeInfoIndex = active >= 0 ? active : clamp(activeInfoIndex, 0, targets.length - 1);
    if(typeof delta==='string'){const next=FFSpatialNavigation.next(targets,targets[activeInfoIndex],delta);if(next)activeInfoIndex=targets.indexOf(next);}else if(delta)activeInfoIndex=(activeInfoIndex+delta+targets.length)%targets.length;
    targets.forEach((target, index) => { target.dataset.focused = String(index === activeInfoIndex); });
    const target = targets[activeInfoIndex];
    target.focus({ preventScroll: true });
    target.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });updateInfoHints(target);
  }

  function toggleHistoryEntry(entry) {
    if (!entry?.matches('[data-history-entry]')) return;
    const details = entry.querySelector('.ff-history-detail');
    const expanded = entry.getAttribute('aria-expanded') !== 'true';
    entry.setAttribute('aria-expanded', String(expanded));
    if (details) details.hidden = !expanded;
  }

  function closeClubDetails() {
    if(query.get('overlay')==='1'&&parent!==window){parent.postMessage({type:'ff-close-club'},'*');return;}
    if (!detailsOpen) return;
    detailsOpen = false;
    $('[data-info-top]').hidden = true;
    $('[data-info-view]').hidden = true;
    $('.ff-header').hidden = false;
    $('.ff-main').hidden = false;
    root.dataset.view = 'globe';
    setActiveChoice('team', true);
    setGamepadMode(connectedGamepad());
  }

  function openClubDetails(refresh=false) {
    const active = team();
    if(!active)return;if(!refresh&&parent!==window&&query.get('view')!=='club'){sessionStorage.setItem('ff-globe-state',JSON.stringify({countryId,leagueId,selectedId:active.id}));parent.postMessage({type:'ff-open-club',clubId:active.id},'*');return;}
    const savedScroll=$('[data-info-view]').scrollTop;const saveDetails=clubDetails.get(active.id)||(data.sampleClubDetail?.clubId===active.id?data.sampleClubDetail:null);
    if(!refresh&&window.FFClubData&&!clubLoads.has(active.id)){const id=active.id;clubLoads.add(id);window.FFClubData.load(id,(detail,pending)=>{clubDetails.set(id,detail);if(detailsOpen&&team()?.id===id)openClubDetails(true);}).catch(error=>{clubLoads.delete(id);showFeedback(error.message);});}
    detailsOpen = true;
    root.dataset.view = 'club-info';
    $('.ff-header').hidden = true;
    $('.ff-main').hidden = true;
    $('[data-info-top]').hidden = false;
    $('[data-info-view]').hidden = false;
    const primary = saveDetails?.primary || active.primary;
    const hero = $('[data-club-hero]');
    hero.style.setProperty('--club-primary', colorHex(primary));
    hero.style.setProperty('--club-ink', teamInk(primary));
    setText('[data-info-name]', active.name);
    setText('[data-info-league-name]', league()?.label || 'Liga');
    setText('[data-info-country]', country()?.name || 'País');
    const cityWrap = $('[data-info-city-wrap]');
    const city = active.city && !/^regi[aã]o\b/i.test(active.city) ? active.city : '';
    $('[data-info-city]').textContent = city;
    cityWrap.hidden = !city;
    setImage($('[data-info-crest]'), active.crest, `Escudo do ${active.name}`);
    setImage($('[data-info-league]'), league()?.icon, `Escudo de ${league()?.label || 'liga'}`);
    const overall = saveDetails?.overall || active.overall || Math.round(((active.attack || 0) + (active.midfield || 0) + (active.defense || 0)) / 3);
    setText('[data-info-overall]', overall);
    for (const [selector, value] of [['[data-info-attack]', active.attack], ['[data-info-midfield]', active.midfield], ['[data-info-defense]', active.defense]]) setText(selector, value);
    const reputation = Math.max(0, Math.min(5, Number(saveDetails?.reputation ?? active.reputation ?? 0) / 4));
    $('[data-info-stars]').textContent = '★'.repeat(Math.floor(reputation)) + (reputation % 1 >= .5 ? '½' : '') + '☆'.repeat(5 - Math.ceil(reputation));
    $('[data-info-stars]').setAttribute('aria-label', `Reputação ${reputation.toFixed(1)} de 5 estrelas`);
    const starts = saveDetails?.starters || [];
    $('[data-xi-scene]').setAttribute('aria-label', starts.length
      ? `Cena 3D do onze titular de ${active.name}: ${starts.map(player => `${player.name}, ${player.position}`).join('; ')}`
      : `Cena 3D do onze titular de ${active.name}`);
    const caption = saveDetails?.lineupScene ? `Cena 3D nativa · ${active.name}` : `Cena 3D indisponível para ${active.name}`;
    setText('[data-xi-caption]', caption);
    setText('[data-xi-count]', `${starts.length} JOGADORES`);
    setText('[data-info-formation]', starts.length === 11 && saveDetails?.formation
      ? `${saveDetails.formation} · FORMAÇÃO SALVA` : 'FORMAÇÃO DO SAVE');
    const emptyScene = $('[data-xi-empty]');
    const lineupImage = $('[data-xi-image]');
    setImage(lineupImage, saveDetails?.lineupScene, `Cena 3D nativa com os onze titulares de ${active.name}`);
    emptyScene.textContent = saveDetails?.lineupScene ? '' : saveDetails
      ? 'O renderizador nativo não conseguiu montar a cena completa deste save.'
      : 'Carregando os dados e a cena 3D deste clube…';
    emptyScene.hidden = !!saveDetails?.lineupScene;
    renderPitch(starts, saveDetails?.formation || '');
    renderHighlights(saveDetails?.highlights || []);
    renderCoach(saveDetails?.coach);
    const stadium = saveDetails?.stadium;
    setText('[data-stadium-name]', stadium?.name || 'Estádio não encontrado');
    setText('[data-stadium-capacity]', stadium?.capacity ? `Capacidade ${Number(stadium.capacity).toLocaleString('pt-BR')}` : 'Capacidade —');
    const stadiumImage = $('[data-stadium-image]'), stadiumPlaceholder = $('[data-stadium-placeholder]');
    setImage(stadiumImage, stadium?.image, `Estádio ${stadium?.name || ''}`);
    stadiumPlaceholder.hidden = !!stadium?.image;
    if (!stadium?.image) {
      stadiumImage.hidden = true;
      stadiumPlaceholder.textContent = 'Imagem não configurada na fonte nativa do jogo';
    }
    renderKits(saveDetails?.kits || []);
    for (const [selector, field] of [['[data-stat-games]', 'games'], ['[data-stat-wins]', 'wins'],
      ['[data-stat-draws]', 'draws'], ['[data-stat-losses]', 'losses']]) setText(selector, saveDetails?.season?.[field]);
    $('[data-season-label]').textContent = saveDetails?.season ? 'SAVE ATIVO' : 'SEM REGISTRO NO SAVE';
    $('[data-club-competitions]').innerHTML=FFSeasonCharts.table(saveDetails?.competitions||[{name:league()?.label,recorded:false}]);
    $('[data-season-charts]').innerHTML=FFSeasonCharts.render(saveDetails);
    renderHistory(saveDetails?.history || []);
    $('[data-announcement]').textContent = `Informações do clube ${active.name}`;
    if(!refresh){$('[data-info-view]').scrollTop=0;activeInfoIndex=0;focusInfoTarget();}else $('[data-info-view]').scrollTop=savedScroll;
    setGamepadMode(connectedGamepad());
  }

  function confirmClub() {
    const active = team();
    if (!active) return;
    openClubDetails();
  }

  function restoreSaveClub() {
    if (detailsOpen) { closeClubDetails(); return; }
    countryId = data.defaultCountryId;
    leagueId = data.defaultLeagueId;
    selectedId = data.defaultTeamId ?? null;
    setActiveChoice('team', true);
    update(true, 'save');
    showFeedback('Clube ativo do save restaurado');
  }

  function recenterGlobe() {
    const active = team() || league();
    if (active) fly({ ...active, zoom: camera.zoom });
  }

  function zoomBy(factor) {
    cancelAnimationFrame(frame);
    frame = 0;
    camera.zoom = clamp(camera.zoom * factor, .75, 10);
    paint();
  }

  function preferredLeagueId(targetCountryId) {
    const leagues = data.countries.find(item => item.id === targetCountryId)?.leagueIds
      .map(id => data.leagues.find(entry => entry.id === id)).filter(Boolean) || [];
    if (targetCountryId === data.defaultCountryId && leagues.some(item => item.id === data.defaultLeagueId)) {
      return data.defaultLeagueId;
    }
    return [...leagues].sort((a, b) => a.level - b.level || a.id - b.id)[0]?.id;
  }

  function setImage(image, src, alt, fallback) {
    image.hidden = !src;
    if (src) {
      image.src = src;
      image.alt = alt || '';
      image.onerror = () => { image.hidden = true; fallback?.(); };
    } else {
      image.removeAttribute('src');
      image.alt = '';
    }
  }

  function paint() {
    if (!width || !height) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    const radius = Math.min(width * .43, height * .45) * camera.zoom;
    const center = [width * .5, height * .52];
    projection.scale(radius).translate(center).rotate([-camera.lon, -camera.lat, 0]);

    ctx.fillStyle = '#bdd9ee';
    for (let i = 0; i < 56; i++) {
      ctx.globalAlpha = .12 + (i % 5) * .055;
      ctx.beginPath();
      ctx.arc(((i * 193 + 41) % 997) / 997 * width,
        ((i * 139 + 37) % 991) / 991 * height, i % 7 === 0 ? 1.15 : .58, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    const halo = ctx.createRadialGradient(center[0], center[1], radius * .95,
      center[0], center[1], radius * 1.1);
    halo.addColorStop(0, '#65b7f500'); halo.addColorStop(.45, '#65b7f52b');
    halo.addColorStop(1, '#65b7f500');
    ctx.fillStyle = halo; ctx.beginPath(); ctx.arc(...center, radius * 1.1, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = '#88b5d32b'; ctx.lineWidth = 1; ctx.beginPath();
    ctx.ellipse(...center, radius * 1.12, radius * .3, -.27, 0, Math.PI * 2); ctx.stroke();

    ctx.beginPath(); path({ type: 'Sphere' });
    const ocean = ctx.createRadialGradient(center[0] - radius * .27, center[1] - radius * .31,
      radius * .06, ...center, radius * 1.12);
    ocean.addColorStop(0, '#1c3b53'); ocean.addColorStop(.48, '#11283b');
    ocean.addColorStop(.82, '#0a1725'); ocean.addColorStop(1, '#03080f');
    ctx.fillStyle = ocean; ctx.fill();

    const mapCountry = country().iso3;
    for (const feature of data.world.features) {
      const selected = feature.properties.id === mapCountry;
      ctx.beginPath(); path(feature);
      ctx.fillStyle = selected ? '#547d98' : '#2b465a'; ctx.fill();
      ctx.globalAlpha = selected ? .25 : .20; ctx.fillStyle = landTexture; ctx.fill(); ctx.globalAlpha = 1;
      ctx.strokeStyle = selected ? '#a5cee9' : '#688397';
      ctx.lineWidth = selected ? 1.3 : .55; ctx.stroke();
    }
    ctx.beginPath(); path(graticule); ctx.strokeStyle = '#a1c3d718'; ctx.lineWidth = .65; ctx.stroke();
    const sheen = ctx.createRadialGradient(center[0] - radius * .3, center[1] - radius * .3,
      0, ...center, radius);
    sheen.addColorStop(0, '#b0dcff10'); sheen.addColorStop(.65, '#00000000');
    sheen.addColorStop(1, '#0000007d');
    ctx.beginPath(); path({ type: 'Sphere' }); ctx.fillStyle = sheen; ctx.fill();
    ctx.beginPath(); path({ type: 'Sphere' }); ctx.strokeStyle = '#81bbdc75'; ctx.lineWidth = 1.2; ctx.stroke();

    const seen = new Set();
    for (const club of league().clubs) {
      const key = `${club.lat},${club.lon}`;
      if (seen.has(key)) continue;
      seen.add(key);
      if (!club.located || d3.geoDistance([camera.lon, camera.lat], [club.lon, club.lat]) > Math.PI / 2 - .025) continue;
      const xy = projection([club.lon, club.lat]);
      ctx.fillStyle = '#d4ebfb'; ctx.globalAlpha = .66;
      ctx.beginPath(); ctx.arc(...xy, 2.7, 0, Math.PI * 2); ctx.fill();
    }
    ctx.globalAlpha = 1;
    const active = team();
    const visible = active?.located
      && d3.geoDistance([camera.lon, camera.lat], [active.lon, active.lat]) < Math.PI / 2 - .025;
    if (visible) {
      const xy = projection([active.lon, active.lat]);
      ctx.save(); ctx.shadowColor = '#80d7ff'; ctx.shadowBlur = 10;
      ctx.strokeStyle = '#9ad8ff'; ctx.lineWidth = 1.6;
      ctx.beginPath(); ctx.moveTo(xy[0], xy[1] - 4); ctx.lineTo(xy[0], xy[1] - 26); ctx.stroke();
      const marker = ctx.createRadialGradient(xy[0] - 1, xy[1] - 1, 0, xy[0], xy[1], 5);
      marker.addColorStop(0, '#fff'); marker.addColorStop(.45, '#bce8ff'); marker.addColorStop(1, '#76bde8');
      ctx.fillStyle = marker; ctx.beginPath(); ctx.arc(...xy, 4.5, 0, Math.PI * 2); ctx.fill(); ctx.restore();
      pin.style.left = `${xy[0]}px`; pin.style.top = `${xy[1] - 26}px`;
      pin.hidden = !active.crest || xy[0] < 36 || xy[0] > width - 36 || xy[1] < 112 || xy[1] > height - 24;
    } else pin.hidden = true;
    canvas.dataset.centerLatitude = camera.lat.toFixed(5);
    canvas.dataset.centerLongitude = camera.lon.toFixed(5);
    canvas.dataset.zoom = camera.zoom.toFixed(2);
  }

  function fly(destination, animate = true) {
    cancelAnimationFrame(frame);
    const from = { ...camera };
    const interpolate = d3.geoInterpolate([from.lon, from.lat], [destination.lon, destination.lat]);
    if (!animate || reduced()) {
      camera = { lon: destination.lon, lat: destination.lat, zoom: destination.zoom };
      paint();
      return;
    }
    const started = performance.now();
    const step = now => {
      const t = clamp((now - started) / 1050, 0, 1), k = d3.easeCubicInOut(t);
      const point = interpolate(k);
      camera = { lon: point[0], lat: point[1], zoom: from.zoom + (destination.zoom - from.zoom) * k };
      paint();
      if (t < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
  }

  function syncSelection() {
    if (!countryLeagues().some(item => item.id === leagueId)) leagueId = preferredLeagueId(countryId);
    if (!league()?.clubs.some(item => item.id === selectedId)) selectedId = league()?.clubs[0]?.id ?? null;
  }

  function clubStrength(club) {
    const overall = Number(club?.overall);
    if (Number.isFinite(overall) && overall > 0) return clamp(overall, 0, 100);
    const ratings = [club?.attack, club?.midfield, club?.defense]
      .map(Number).filter(value => Number.isFinite(value) && value > 0);
    return ratings.length ? ratings.reduce((sum, value) => sum + value, 0) / ratings.length : null;
  }

  function averageClubStrength(clubs) {
    const unique = new Map((clubs || []).map(club => [club.id, club]));
    const values = [...unique.values()].map(clubStrength).filter(Number.isFinite);
    return values.length ? Math.round(values.reduce((sum, value) => sum + value, 0) / values.length) : null;
  }

  function paintStrength(selector, clubs, label) {
    const badge = $(selector), score = averageClubStrength(clubs);
    badge.textContent = score === null ? '—' : String(score);
    badge.dataset.score = score === null ? '' : String(score);
    if (score === null) {
      badge.style.backgroundColor = '#253443';
      badge.setAttribute('aria-label', `${label}: sem avaliações de clube disponíveis`);
      return;
    }
    const hue = Math.round(score * 1.2);
    badge.style.backgroundColor = `hsl(${hue} 66% 34%)`;
    badge.style.borderColor = `hsl(${hue} 78% 56% / .72)`;
    badge.setAttribute('aria-label', `${label}: ${score} de 100`);
  }

  function update(animate = true, focus = 'team') {
    syncSelection();
    const c = country(), l = league(), active = team();
    const countryIcon = $('[data-choice="country"] img');
    setImage(countryIcon, c.icon, c.name + ' flag');
    $('[data-country-name]').textContent = c.name;
    $('[data-country-meta]').textContent = `${c.leagueIds.length} ${c.leagueIds.length === 1 ? 'liga' : 'ligas'}`;
    const countryClubs = countryLeagues().flatMap(item => item.clubs);
    paintStrength('[data-country-strength]', countryClubs, `Força média de ${c.name}`);
    const leagueIcon = $('[data-choice="league"] img');
    setImage(leagueIcon, l.icon, l.label);
    $('[data-league-name]').textContent = l.label;
    $('[data-league-meta]').textContent = l.division;
    paintStrength('[data-league-strength]', l.clubs, `Força média de ${l.label}`);
    setImage($('[data-world-league-icon]'), l.icon, `Escudo de ${l.label}`);
    $('[data-team-name]').textContent = active?.name || 'Clube indisponível';
    const cityLabel = active?.city && !/^regi[aã]o\b/i.test(active.city) ? active.city : '';
    const locationLabel = $('[data-team-location]');
    locationLabel.textContent = cityLabel;
    locationLabel.hidden = !cityLabel;
    const stars = Math.max(0, Math.min(5, Number(active?.reputation || 0) / 4));
    const starRow = $('[data-team-stars]');
    starRow.replaceChildren(...Array.from({ length: 5 }, (_, index) => {
      const star = document.createElement('span');
      const fill = Math.max(0, Math.min(1, stars - index));
      star.className = 'ff-star';
      star.textContent = '★';
      star.style.setProperty('--ff-star-fill', `${fill * 100}%`);
      star.setAttribute('aria-hidden', 'true');
      return star;
    }));
    const reputationText = Number.isInteger(stars) ? String(stars) : stars.toFixed(1).replace('.', ',');
    starRow.setAttribute('aria-label', `Reputação ${reputationText} de 5 estrelas`);
    $('[data-team-attack]').textContent = active?.attack ?? '—';
    $('[data-team-midfield]').textContent = active?.midfield ?? '—';
    $('[data-team-defense]').textContent = active?.defense ?? '—';
    $('[data-team-count]').textContent = `${l.clubs.length} clubes`;
    const monogram = $('.ff-monogram'), teamIcon = $('.ff-team-emblem');
    monogram.textContent = (active?.name || 'FF').split(/\s+/).slice(0, 2).map(word => word[0]).join('').toUpperCase();
    monogram.hidden = !!active?.crest;
    setImage(teamIcon, active?.crest, `Escudo do ${active?.name || 'clube'}`);
    if (active?.crest) {
      const pinIcon = $('.ff-pin img');
      pinIcon.src = active.crest;
      pinIcon.alt = '';
    }
    $('[data-world-title]').textContent = `${c.name} · ${l.label}`;
    $('[data-announcement]').textContent = active
      ? `${c.name}${cityLabel ? `, ${cityLabel}` : ''}, ${active.name}` : c.name;
    canvas.setAttribute('aria-label', active
      ? `Globo com marcador do ${active.name}, ${c.name}${cityLabel ? ` — ${cityLabel}` : ''}`
      : `Globo de ${c.name}`);
    const destination = focus === 'league' ? l
      : focus === 'team' && active ? { ...active, zoom: camera.zoom }
        : active || l;
    fly(destination, animate);
  }

  function cycleCountry(delta) {
    const next = (countryAt() + delta + data.countries.length) % data.countries.length;
    countryId = data.countries[next].id;
    leagueId = preferredLeagueId(countryId);
    selectedId = null;
    update(true, 'league');
  }

  function cycleLeague(delta) {
    const leagues = countryLeagues();
    const next = (leagueAt() + delta + leagues.length) % leagues.length;
    leagueId = leagues[next].id;
    selectedId = null;
    update(true, 'league');
  }

  function cycleTeam(delta) {
    const clubs = league().clubs;
    if (!clubs.length) return;
    const next = (teamAt() + delta + clubs.length) % clubs.length;
    selectedId = clubs[next].id;
    update(true, 'team');
  }

  root.querySelectorAll('[data-step-country]').forEach(button => button.addEventListener('click', () => {
    setActiveChoice('country');
    cycleCountry(Number(button.dataset.stepCountry));
  }));
  root.querySelectorAll('[data-step-league]').forEach(button => button.addEventListener('click', () => {
    setActiveChoice('league');
    cycleLeague(Number(button.dataset.stepLeague));
  }));
  root.querySelectorAll('[data-step-team]').forEach(button => button.addEventListener('click', () => {
    setActiveChoice('team');
    cycleTeam(Number(button.dataset.stepTeam));
  }));

  root.querySelectorAll('[data-choice]').forEach(card => {
    card.addEventListener('focusin', () => setActiveChoice(card.dataset.choice));
    card.addEventListener('pointerenter', () => setActiveChoice(card.dataset.choice));
    card.addEventListener('click', event => {
      if (event.target.closest('button')) return;
      setActiveChoice(card.dataset.choice, true);
      if (card.dataset.choice === 'team') openClubDetails();
    });
  });
  window.FFControlHints.mount(controlHints, { mode: 'keyboard', view: 'globe' });
  const infoView = $('[data-info-view]');
  infoView.addEventListener('pointerover', event => {
    const target=event.target.closest('[data-nav-card]');if(!target)return;
    const targets=infoTargets();activeInfoIndex=targets.indexOf(target);targets.forEach(item=>item.dataset.focused=String(item===target));updateInfoHints(target);
  });
  infoView.addEventListener('focusin', event => {
    const target = event.target.closest('[data-nav-card]');
    if (!target) return;
    const targets = infoTargets();
    activeInfoIndex = targets.indexOf(target);
    targets.forEach(item => { item.dataset.focused = String(item === target); });updateInfoHints(target);
  });
  infoView.addEventListener('click', event => {
    const coach=event.target.closest('[data-coach-profile]');if(coach){if(parent!==window)parent.postMessage({type:'ff-coach',clubId:team()?.id},'*');else if(window.chrome?.webview)window.chrome.webview.postMessage('coach:'+team()?.id+':leagues');else {sessionStorage.setItem('ff-return-tab','leagues');sessionStorage.setItem('ff-return-club',String(team()?.id));location.href='coach.html?club='+team()?.id;}return;}
    const historyEntry = event.target.closest('[data-history-entry]');
    if (historyEntry) toggleHistoryEntry(historyEntry);
  });

  document.addEventListener('keydown', event => {
    if(paused)return;
    if (event.altKey || event.ctrlKey || event.metaKey || event.defaultPrevented) return;
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName)) return;
    if(parent!==window && ['q','e','PageUp','PageDown'].includes(event.key)){event.preventDefault();parent.postMessage({type:'ff-tab',direction:['q','PageUp'].includes(event.key)?-1:1},'*');return;}
    if (detailsOpen) {
      if((event.key==='Enter'||event.key===' ')&&event.target.closest('[data-player-profile],[data-coach-profile]')){event.preventDefault();event.target.closest('[data-player-profile],[data-coach-profile]').click();return;}
      if (event.key === 'Escape' || event.key === 'Backspace') {
        event.preventDefault();
        closeClubDetails();
      } else if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
        event.preventDefault();
        focusInfoTarget(event.key.slice(5).toLowerCase());
      }
      return;
    }
    const card = event.target.closest('[data-choice]');
    if (card) setActiveChoice(card.dataset.choice);
    const keys = {
      ArrowUp: () => changeActiveChoice(-1),
      ArrowDown: () => changeActiveChoice(1),
      ArrowLeft: () => stepActiveChoice(-1),
      ArrowRight: () => stepActiveChoice(1),
    };
    if (keys[event.key]) {
      event.preventDefault();
      keys[event.key]();
    } else if (event.key === 'Enter' || event.key === ' ') {
      if (event.target.matches('[data-choice]')) {
        event.preventDefault();
        confirmClub();
      }
    } else if (event.key === 'Escape' || event.key === 'Backspace') {
      event.preventDefault();
      if (parent !== window) parent.postMessage({type:'ff-back'}, '*');
      else if (window.chrome?.webview) window.chrome.webview.postMessage('back');
      else restoreSaveClub();
    } else if (event.key.toLowerCase() === 'r') {
      event.preventDefault();
      recenterGlobe();
    } else if (event.key === '+' || event.key === '=') {
      event.preventDefault();
      zoomBy(1.18);
    } else if (event.key === '-' || event.key === '_') {
      event.preventDefault();
      zoomBy(1 / 1.18);
    }
  });

  function connectedGamepad() {
    if (!navigator.getGamepads) return null;
    let pads;
    try { pads = Array.from(navigator.getGamepads()); } catch (_) { return null; }
    return (activeGamepadIndex !== null && pads[activeGamepadIndex]?.connected
      ? pads[activeGamepadIndex] : pads.find(pad => pad?.connected)) || null;
  }

  function setGamepadMode(pad) {
    const nextIndex = pad?.index ?? null;
    if (nextIndex === activeGamepadIndex && controlHints.dataset.mode === (pad ? 'gamepad' : 'keyboard')
      && controlHints.dataset.view === (detailsOpen ? 'details' : 'globe')) return;
    activeGamepadIndex = nextIndex;
    previousPadButtons = [];
    padDirection = '';
    padRepeatAt = 0;
    lastPadFrame = 0;
    window.FFControlHints.mount(controlHints, {
      mode: pad ? 'gamepad' : 'keyboard',
      controllerId: pad?.id || '',
      view: detailsOpen ? 'details' : 'globe',
    });
  }

  function gamepadFrame(now) {
    if(paused){previousPadButtons=connectedGamepad()?.buttons.map(b=>!!b.pressed)||[];requestAnimationFrame(gamepadFrame);return;}
    const pad = connectedGamepad();
    if (!pad) {
      if (activeGamepadIndex !== null || controlHints.dataset.mode !== 'keyboard') setGamepadMode(null);
      requestAnimationFrame(gamepadFrame);
      return;
    }
    if (pad.index !== activeGamepadIndex || controlHints.dataset.mode !== 'gamepad') setGamepadMode(pad);

    const elapsed = lastPadFrame ? Math.min(.05, Math.max(0, (now - lastPadFrame) / 1000)) : 0;
    lastPadFrame = now;
    const pressed = index => !!pad.buttons[index]?.pressed;
    const stickX = Number(pad.axes?.[2] || 0), stickY = Number(pad.axes?.[3] || 0);
    if (detailsOpen && Math.abs(stickY) > .14 && elapsed) {
      infoView.scrollTop += stickY * elapsed * 850;
    } else if (!detailsOpen && (Math.abs(stickX) > .14 || Math.abs(stickY) > .14)) {
      cancelAnimationFrame(frame);
      frame = 0;
      const rotateX = Math.abs(stickX) > .14 ? stickX : 0;
      const rotateY = Math.abs(stickY) > .14 ? stickY : 0;
      camera.lon = ((camera.lon + rotateX * 84 * elapsed / camera.zoom + 540) % 360) - 180;
      camera.lat = clamp(camera.lat - rotateY * 56 * elapsed / camera.zoom, -80, 80);
      paint();
    }
    const leftX = Number(pad.axes?.[0] || 0), leftY = Number(pad.axes?.[1] || 0);
    const stickDirection = Math.max(Math.abs(leftX), Math.abs(leftY)) > .38
      ? (Math.abs(leftX) > Math.abs(leftY)
        ? `h${leftX < 0 ? -1 : 1}`
        : `v${leftY < 0 ? -1 : 1}`)
      : '';
    const vertical = pressed(12) ? -1 : pressed(13) ? 1 : 0;
    const horizontal = pressed(14) ? -1 : pressed(15) ? 1 : 0;
    const direction = vertical ? `v${vertical}` : horizontal ? `h${horizontal}` : stickDirection;
    const directionChanged = !!direction && direction !== padDirection;
    if (direction && (directionChanged || now >= padRepeatAt)) {
      const directionValue = Number(direction.slice(1));
      if(detailsOpen)focusInfoTarget(direction[0]==='h'?(directionValue<0?'left':'right'):(directionValue<0?'up':'down'));
      else if (direction[0] === 'v') changeActiveChoice(directionValue);
      else stepActiveChoice(directionValue);
      padDirection = direction;
      padRepeatAt = now + (directionChanged ? 340 : 185);
    } else if (!direction) {
      padDirection = '';
      padRepeatAt = 0;
    }

    const currentButtons = pad.buttons.map(button => !!button?.pressed);
    if (currentButtons[0] && !previousPadButtons[0]) {
      if (detailsOpen) {
        const historyEntry = document.activeElement.closest?.('[data-history-entry]');
        if (historyEntry) toggleHistoryEntry(historyEntry);
        else document.activeElement.closest?.('[data-player-profile],[data-coach-profile]')?.click();
      } else confirmClub();
    }
    if (currentButtons[1] && !previousPadButtons[1]) {
      if (detailsOpen) closeClubDetails();
      else if (parent !== window) parent.postMessage({type:'ff-back'}, '*');
      else if (window.chrome?.webview) window.chrome.webview.postMessage('back');
      else restoreSaveClub();
    }
    if (!detailsOpen && currentButtons[3] && !previousPadButtons[3]) recenterGlobe();
    if (parent === window && !detailsOpen && currentButtons[5] && !previousPadButtons[5]) zoomBy(1.2);
    const l2 = Math.max(Number(pad.buttons[6]?.value || 0), currentButtons[6] ? 1 : 0);
    const r2 = Math.max(Number(pad.buttons[7]?.value || 0), currentButtons[7] ? 1 : 0);
    if (!detailsOpen && elapsed && (l2 > .1 || r2 > .1)) zoomBy(Math.exp((r2 - l2) * elapsed * 1.05));
    previousPadButtons = currentButtons;
    requestAnimationFrame(gamepadFrame);
  }

  window.addEventListener('gamepadconnected', event => setGamepadMode(event.gamepad));
  window.addEventListener('gamepaddisconnected', () => {
    activeGamepadIndex = null;
    const pad = connectedGamepad();
    setGamepadMode(pad);
  });
  canvas.addEventListener('pointerdown', event => {
    cancelAnimationFrame(frame);
    drag = { x: event.clientX, y: event.clientY, ...camera };
    canvas.setPointerCapture(event.pointerId);
  });
  canvas.addEventListener('pointermove', event => {
    if (!drag) return;
    camera.lon = drag.lon - (event.clientX - drag.x) * .22 / camera.zoom;
    camera.lat = clamp(drag.lat + (event.clientY - drag.y) * .22 / camera.zoom, -80, 80);
    paint();
  });
  canvas.addEventListener('pointerup', () => { drag = null; });
  canvas.addEventListener('pointercancel', () => { drag = null; });
  canvas.addEventListener('lostpointercapture', () => { drag = null; });
  canvas.addEventListener('wheel', event => {
    event.preventDefault();
    zoomBy(Math.exp(-event.deltaY * .0015));
  }, { passive: false });
  const observer = new ResizeObserver(() => {
    const rect = canvas.getBoundingClientRect(), dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = rect.width; height = rect.height;
    canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr);
    paint();
  });
  observer.observe(canvas);
  window.addEventListener('message',event=>{
    if(parent===window||event.source!==parent||event.data?.type!=='ff-career')return;
    const career=event.data.context;if(!career?.clubId)return;
    const entry=data.leagues.find(l=>l.clubs.some(c=>c.id===career.clubId));if(!entry)return;
    const changed=data.defaultTeamId!==career.clubId;
    data.defaultTeamId=career.clubId;data.defaultLeagueId=entry.id;data.defaultCountryId=entry.countryId;
    data.sampleClubDetail={...(data.sampleClubDetail?.clubId===career.clubId?data.sampleClubDetail:{}),...career.detail,clubId:career.clubId,name:career.clubName};
    clubDetails.set(career.clubId,data.sampleClubDetail);
    if(changed&&!query.get('club')&&query.get('restore')!=='1'){countryId=entry.countryId;leagueId=entry.id;selectedId=career.clubId;update(false);if(detailsOpen)openClubDetails();}
  });
  const requestedClub=Number(query.get('club'));if(requestedClub){const selectedLeague=data.leagues.find(l=>String(l.id)===query.get('league')&&l.clubs.some(c=>c.id===requestedClub))||data.leagues.find(l=>l.clubs.some(c=>c.id===requestedClub));if(selectedLeague){countryId=selectedLeague.countryId;leagueId=selectedLeague.id;selectedId=requestedClub;}}
  if(query.get('restore')==='1'){try{const saved=JSON.parse(sessionStorage.getItem('ff-globe-state'));if(saved&&data.leagues.some(l=>l.id===saved.leagueId&&l.clubs.some(c=>c.id===saved.selectedId))){countryId=saved.countryId;leagueId=saved.leagueId;selectedId=saved.selectedId;}}catch{}}
  window.addEventListener('message',event=>{if(event.source===parent&&event.data?.type==='ff-activate'){if(detailsOpen)focusInfoTarget();else setActiveChoice(activeChoice,true);}if(event.source===parent&&event.data?.type==='ff-suspend'){paused=!!event.data.paused;if(!paused)setActiveChoice(activeChoice,true);previousPadButtons=connectedGamepad()?.buttons.map(b=>!!b.pressed)||[];}});
  update(false);
  if(new URLSearchParams(location.search).get('view')==='club')confirmClub();
  if(!detailsOpen)setActiveChoice('team',true);
  requestAnimationFrame(gamepadFrame);
})();
