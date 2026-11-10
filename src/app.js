/* Research content is local; the published homepage uses a visitor-map service. */
(() => {
  'use strict';

  const data = window.HOMEPAGE_DATA || {};
  const site = data.site || {};
  const profile = site.profile || {};
  const home = site.home || {};
  const content = (data.content || {}).items || {};
  const visible = rows => (rows || []).filter(row => !row.source_missing && !content[row.id]?.hidden);
  const publications = visible(data.publications);
  const presentations = visible(data.presentations);
  // Numbers belong to the full chronological catalog, not a filtered result or an ID suffix.
  const recordNumbers = new Map([publications, presentations].flatMap(rows => rows.map((row, index) => [row.id, rows.length - index])));
  const records = new Map([...publications, ...presentations].map(row => [row.id, row]));
  const app = document.getElementById('app');
  const dialog = document.getElementById('detail-dialog');
  const dialogContent = document.getElementById('detail-content');
  const toast = document.getElementById('toast');
  const visitorPanel = document.getElementById('visitor-panel');
  const mapModes = { Collaborations: 'collaborations', Visits: 'visits', Visitors: 'visitors' };
  const pageNames = { research: 'Research', people: 'People', publications: 'Publications', presentations: 'Presentations', news: 'News & Events', about: 'About BR', maps: 'Maps', links: 'Link · Data / SW' };
  const types = { journalArticle: 'Journal article', conferencePaper: 'Conference paper', thesis: 'Thesis', dataset: 'Dataset', book: 'Book', bookSection: 'Book chapter', report: 'Report', preprint: 'Preprint', magazineArticle: 'Magazine article', newspaperArticle: 'Newspaper article' };
  const roles = { first_author: 'First author', co_first_author: 'Co-first author', corresponding_author: 'Corresponding author', co_corresponding_author: 'Co-corresponding author' };
  const state = {
    page: 'research',
    publications: { query: '', year: '', type: '', role: '', limit: 20 },
    presentations: { query: '', year: '', type: '', eventId: '', limit: 20 },
    researchView: 'overview',
    news: { type: 'all', query: '', year: '' },
    people: { category: 'Members' },
    links: { query: '', category: '' },
    maps: { mode: 'collaborations', query: '', selected: null },
  };
  let toastTimer;
  let dialogReturnFocus = null;

  const esc = value => String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const normalize = value => String(value ?? '').normalize('NFKC').toLocaleLowerCase().replace(/\s+/g, ' ').trim();
  const arr = value => Array.isArray(value) ? value : [];
  const publicRows = value => arr(value).filter(row => row.public !== false);
  const list = value => Array.isArray(value) ? value : String(value || '').split(';').map(item => item.trim()).filter(Boolean);
  const unique = values => [...new Set(values.filter(Boolean))];
  function safeUrl(value, allowLocal = false) {
    if (!value) return '';
    const raw = String(value).trim();
    if (allowLocal && /^(?:assets|images)\//.test(raw) && !/[\\\x00-\x1f?#]/.test(raw)) {
      try {
        const decoded = decodeURIComponent(raw);
        if (!/[\\\x00-\x1f?#]/.test(decoded) && !decoded.split('/').some(part => ['..', '.'].includes(part))) return raw;
      } catch { return ''; }
    }
    try {
      const parsed = new URL(raw);
      return ['https:', 'http:'].includes(parsed.protocol) && !parsed.username && !parsed.password ? parsed.href : '';
    } catch { return ''; }
  }
  function external(label, url, className = 'text-link') {
    const safe = safeUrl(url, true);
    return safe ? `<a class="${className}" href="${esc(safe)}" target="_blank" rel="noopener noreferrer">${esc(label)}<span class="arrow-up-right" aria-hidden="true"></span></a>` : '';
  }
  function imageUrl(value) {
    const raw = String(value || '').trim();
    if (/^data:image\/(?:png|jpeg|gif|webp|avif|svg\+xml);base64,[a-z0-9+/=\s]+$/i.test(raw)) return raw;
    const url = safeUrl(raw, true);
    return /^http:/.test(url) ? '' : url;
  }
  function contentImage(value, alt = '', className = 'content-image') {
    const url = imageUrl(value);
    return url ? `<figure class="${className}"><img src="${esc(url)}" alt="${esc(alt)}" loading="lazy"></figure>` : '';
  }
  function avatar(person, large = false) {
    const url = imageUrl(person.image);
    return url ? `<div class="avatar${large ? ' avatar-large' : ''} avatar-photo"><img src="${esc(url)}" alt="${esc(person.image_alt || person.name || '')}" loading="lazy"></div>` : `<div class="avatar${large ? ' avatar-large' : ''}" aria-hidden="true">${esc(initials(person.name))}</div>`;
  }
  function lineText(value) { return esc(value).replace(/\n/g, '<br>'); }
  function actionLink(label, url, className) {
    const hash = /^#(?:research|people|publications|presentations|news|about|maps|links)$/.test(url || '') ? url : '';
    const target = hash || safeUrl(url, true);
    return target && label ? `<a class="${className}" href="${esc(target)}"${hash ? '' : ' target="_blank" rel="noopener noreferrer"'}>${esc(label)}<span class="arrow-up-right" aria-hidden="true"></span></a>` : '';
  }
  function applySiteIdentity() {
    const brandTitle = document.querySelector('.brand-copy strong');
    const brandSubtitle = document.querySelector('.brand-copy>span');
    if (brandTitle && home.site_title) brandTitle.textContent = home.site_title;
    if (brandSubtitle && home.site_subtitle) brandSubtitle.textContent = home.site_subtitle;
    if (home.site_description) document.querySelector('meta[name="description"]')?.setAttribute('content', home.site_description);
    const footerText = document.querySelector('.footer-brand p');
    const footerLocation = document.querySelector('.footer-location');
    if (footerText && home.footer_text) footerText.textContent = home.footer_text;
    if (footerLocation && home.footer_location) footerLocation.textContent = home.footer_location;
    document.querySelectorAll('.footer-brand strong').forEach(node => { node.textContent = profile.name || 'Byungki Ryu'; });
    document.querySelector('.brand')?.setAttribute('aria-label', `${home.site_title || profile.name || 'Byungki Ryu'} home`);
    const email = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(profile.email || '') ? profile.email : '';
    document.querySelectorAll('a[href^="mailto:"]').forEach(node => {
      node.hidden = !email;
      if (!email) return;
      node.href = `mailto:${email}`;
      if (node.closest('.footer-links')) node.innerHTML = `${esc(email)} <span class="arrow-up-right" aria-hidden="true"></span>`;
    });
  }
  function showToast(message) {
    clearTimeout(toastTimer);
    if (!toast) return;
    toast.textContent = message;
    toast.hidden = false;
    toast.classList.add('is-visible');
    toastTimer = setTimeout(() => { toast.classList.remove('is-visible'); toast.hidden = true; }, 2600);
  }
  function displayDate(value) {
    if (!value) return '';
    const parts = String(value).split('-');
    if (parts.length === 1) return parts[0];
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const month = months[Number(parts[1]) - 1];
    if (!month) return value;
    return parts.length === 3 ? `${month} ${Number(parts[2])}, ${parts[0]}` : `${month} ${parts[0]}`;
  }
  function todaySeoul() {
    const parts = new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
    const get = type => parts.find(part => part.type === type)?.value;
    return `${get('year')}-${get('month')}-${get('day')}`;
  }
  function upcoming(record) { return record.kind === 'presentation' && /^\d{4}-\d{2}-\d{2}$/.test(record.date || '') && record.date > todaySeoul(); }
  function authorName(name) {
    const pieces = String(name || '').split(',');
    if (pieces.length === 2 && pieces.every(piece => /^[가-힣\s]+$/u.test(piece.trim()))) {
      return pieces.map(piece => piece.replace(/\s+/g, '')).join('');
    }
    return pieces.length === 2 ? `${pieces[1].trim()} ${pieces[0].trim()}` : name;
  }
  function authorsHtml(authors) {
    return arr(authors).map(name => {
      const display = authorName(name);
      const isBK = /^ryu\s*,\s*(?:byungki|b\.?)$/i.test(name.trim()) || /^byungki\s+ryu$/i.test(name.trim()) || display === '류병기';
      return isBK ? `<strong class="author-highlight">${esc(display)}</strong>` : esc(display);
    }).join(', ');
  }
  function initials(name) {
    return String(name || '').split(/[\s,-]+/).filter(Boolean).slice(0, 2).map(word => word[0]).join('').toUpperCase();
  }
  function typeLabel(record) { return record.kind === 'presentation' ? record.presentation_type || 'Type not specified' : types[record.item_type] || record.item_type; }
  function sourceUrl(record) { return record.doi ? `https://doi.org/${record.doi}` : safeUrl(record.url); }
  function citation(record) {
    const authors = arr(record.authors).map(authorName).join(', ');
    if (record.kind === 'presentation') return [authors, `“${record.title}”`, record.venue, record.place, displayDate(record.date), record.presentation_type, safeUrl(record.url)].filter(Boolean).join('. ');
    const volume = [record.volume, record.issue ? `(${record.issue})` : ''].filter(Boolean).join('');
    return [authors, `“${record.title}”`, record.venue, [volume, record.pages].filter(Boolean).join(', '), `(${record.year})`, sourceUrl(record)].filter(Boolean).join('. ');
  }
  async function copyText(text) {
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text);
      else throw new Error('Clipboard unavailable');
      showToast('Citation copied');
    } catch {
      const field = document.createElement('textarea');
      field.value = text;
      field.style.cssText = 'position:fixed;left:-9999px;top:0';
      document.body.append(field);
      field.select();
      const copied = document.execCommand('copy');
      field.remove();
      showToast(copied ? 'Citation copied' : 'Select and copy the citation in the details panel.');
    }
  }
  function heading(kicker, title, description = '') {
    return `<header class="page-heading"><p class="eyebrow">${esc(kicker)}</p><h1 class="page-title">${esc(title)}</h1>${description ? `<p class="page-description">${esc(description)}</p>` : ''}</header>`;
  }
  function chips(values, selected, attribute) {
    return `<div class="chip-group">${values.map(value => `<button type="button" class="chip${selected === value ? ' is-active' : ''}" ${attribute}="${esc(value)}" aria-pressed="${selected === value}">${esc(value)}</button>`).join('')}</div>`;
  }
  function empty(title, description = 'Try another search or clear the filters.') {
    return `<div class="empty-state"><h3>${esc(title)}</h3><p>${esc(description)}</p></div>`;
  }
  function roleBadges(record) {
    return arr(record.roles).map(role => `<span class="badge badge-role">${esc(roles[role] || role)}</span>`).join('');
  }
  function recordCard(record, compact = false) {
    const detail = content[record.id] || {};
    const meta = record.kind === 'presentation'
      ? [displayDate(record.date), record.place].filter(Boolean).join(' · ')
      : [record.volume ? `${record.volume}${record.issue ? `(${record.issue})` : ''}` : '', record.pages].filter(Boolean).join(', ');
    const link = sourceUrl(record);
    return `<article class="record-card${compact ? ' record-card-compact' : ''}" data-record-id="${esc(record.id)}">
      <div class="record-year record-number" aria-label="Record number ${recordNumbers.get(record.id)}">${recordNumbers.get(record.id)}</div>
      <div class="record-main">
        <div class="record-kicker">${compact ? `<span>${esc(record.year)}</span>` : ''}<span>${esc(typeLabel(record))}</span>${upcoming(record) ? '<span class="badge badge-upcoming">Upcoming</span>' : ''}${detail.featured ? '<span class="badge">Selected</span>' : ''}</div>
        <h3 class="record-title"><button type="button" data-open-record="${esc(record.id)}">${esc(record.title)}</button></h3>
        <p class="record-authors">${authorsHtml(record.authors)}</p>
        <p class="record-venue">${esc(record.venue || '')}${meta ? `<span>${record.venue ? ' · ' : ''}${esc(meta)}</span>` : ''}</p>
        <div class="record-meta">${roleBadges(record)}</div>
        ${compact ? '' : `<div class="record-actions"><button class="text-link" type="button" data-open-record="${esc(record.id)}">Details <span class="arrow-right" aria-hidden="true"></span></button>${external(record.doi ? 'DOI' : 'Website', link)}<button type="button" class="text-link quiet" data-copy-record="${esc(record.id)}">Copy citation</button></div>`}
      </div>
    </article>`;
  }

  function researchViews() {
    return `<nav class="section-tabs" aria-label="Research sections">${[['overview', 'Overview'], ['projects', 'Projects'], ['facilities', 'Facilities']].map(([view, label]) => `<a href="#research?view=${view}"${state.researchView === view ? ' aria-current="page"' : ''}>${label}</a>`).join('')}</nav>`;
  }
  function renderResearch() {
    if (state.researchView === 'projects') { renderProjects(); return; }
    if (state.researchView === 'facilities') { renderFacilities(); return; }
    renderResearchOverview();
  }
  function renderProjects() {
    const projects = publicRows(site.research?.projects);
    const period = project => [project.start_date, project.end_date].filter(Boolean).map(date => date.replaceAll('-', '.')).join(' – ');
    app.innerHTML = researchViews() + heading('RESEARCH PROGRAMS', 'Projects', 'Research projects in materials, interfaces, thermoelectric energy conversion, and cooling.') +
      `<div class="project-list">${projects.length ? projects.map(project => `<article class="project-row"><p class="project-period">${esc(period(project))}</p><div><h2>${esc(project.title || project.title_ko)}</h2>${project.title && project.title_ko ? `<p class="project-title-ko" lang="ko">${esc(project.title_ko)}</p>` : ''}${project.description ? `<p class="quiet long-text">${esc(project.description)}</p>` : ''}</div></article>`).join('') : empty('No projects listed', '')}</div>`;
  }
  function renderFacilities() {
    const facilities = publicRows(site.research?.facilities);
    app.innerHTML = researchViews() + heading('RESEARCH INFRASTRUCTURE', 'Facilities') + `<div class="facility-grid">${facilities.length ? facilities.map(facility => `<article class="facility-card"><h2>${esc(facility.title || facility.title_ko)}</h2>${facility.title && facility.title_ko ? `<p lang="ko">${esc(facility.title_ko)}</p>` : ''}${facility.description ? `<p class="long-text">${esc(facility.description)}</p>` : ''}${contentImage(facility.image, facility.image_alt || facility.title)}${external('Learn more', facility.url)}</article>`).join('') : empty('Facilities information is coming soon', 'Details of our research facilities will be added here.')}</div>`;
  }
  function renderResearchOverview() {
    const research = site.research || {};
    const topics = publicRows(research.topics);
    const lattice = document.getElementById('lattice-visual');
    const latestNews = newsItems().slice(0, 3);
    const selectedIds = list(home.featured_publication_ids);
    const selectedPublications = selectedIds.map(id => publications.find(record => record.id === id)).filter(Boolean);
    const featured = publications.filter(record => content[record.id]?.featured);
    const homePublications = selectedIds.length ? selectedPublications : featured.length ? featured.slice(0, 3) : publications.slice(0, 3);
    const heroImage = contentImage(home.hero_image, home.hero_image_alt || '', 'hero-image');
    app.innerHTML = researchViews() + `<section class="hero-grid">
      <div class="hero-copy"><p class="eyebrow">${esc(home.hero_kicker || 'THERMO-ELECTRIC SCIENCE · KERI')}</p>
        <h1 class="hero-title">${lineText(home.hero_title || 'Thermoelectric science,')}<br><em>${lineText(home.hero_emphasis || 'from atoms to applications.')}</em></h1>
        <p class="hero-summary">${lineText(home.hero_summary || research.intro || 'Understanding thermoelectric phenomena through materials physics, computation, data, and experiment.')}</p>
        <div class="hero-actions">${actionLink(home.primary_label || 'Explore publications', home.primary_url || '#publications', 'button')}${actionLink(home.secondary_label || 'About Byungki Ryu', home.secondary_url || '#about', 'button button-secondary')}</div>
      </div><div class="hero-art"${heroImage ? '' : ' aria-label="Conceptual illustration connecting atomic structure and thermoelectric transport"'}>${heroImage || lattice?.innerHTML || '<div class="science-symbol">σ · S · κ</div>'}</div>
    </section>
    <section class="stats-strip" aria-label="Research archive"><div class="stat"><strong>${publications.length}</strong><span>Publications &amp; datasets</span></div><div class="stat"><strong>${presentations.length}</strong><span>Presentations</span></div><div class="stat"><strong>σ · S · κ</strong><span>Transport across scales</span></div></section>
    <section class="research-topics"><div class="section-heading"><div><p class="eyebrow">RESEARCH DIRECTIONS</p><h2>${lineText(home.research_heading || 'Connecting structure,\ntransport, and performance.')}</h2></div><p>${lineText(home.research_description || 'Materials physics and computational tools\nfor thermoelectric energy conversion.')}</p></div>
      ${topics.map((topic, index) => `<article class="topic-row"><span class="topic-index">${String(index + 1).padStart(2, '0')}</span><div class="topic-body"><p class="eyebrow">${esc(topic.kicker || '')}</p><h3>${esc(topic.title)}</h3><p class="long-text">${esc(topic.description || '')}</p>${contentImage(topic.image, topic.image_alt || '')}<div class="topic-links">${arr(topic.links).map(link => external(link.label, link.url)).join('')}</div></div><div class="topic-detail"><ul>${list(topic.details).map(item => `<li>${esc(item)}</li>`).join('')}</ul><div class="topic-tags">${list(topic.keywords).map(keyword => `<button type="button" class="topic-tag" data-topic-search="${esc(keyword)}">${esc(keyword)}</button>`).join('')}</div></div></article>`).join('')}
    </section>
    <section><div class="section-heading"><div><p class="eyebrow">FROM THE ARCHIVE</p><h2>${selectedIds.length || featured.length ? 'Selected publications' : 'Recent publications'}</h2></div><a class="text-link section-link" href="#publications">All ${publications.length} records <span class="arrow-up-right" aria-hidden="true"></span></a></div><div class="record-list">${homePublications.length ? homePublications.map(record => recordCard(record, true)).join('') : empty('No selected publications', 'Check the publication IDs in the home settings.')}</div></section>
    ${latestNews.length ? `<section class="mini-news"><div class="section-heading"><div><p class="eyebrow">GROUP UPDATES</p><h2>News &amp; Events</h2></div><a class="text-link" href="#news">View all news &amp; events <span class="arrow-up-right" aria-hidden="true"></span></a></div>${latestNews.map(item => `<article class="timeline-item"><time class="news-date">${esc(displayDate(item.sortDate))}</time><div><p class="eyebrow">${item.type === 'events' ? 'EVENT' : 'NEWS'}</p><h3>${esc(item.title)}</h3><p class="long-text">${esc(item.body || item.description || '')}</p>${contentImage(item.image, item.image_alt || '')}${external('Read more', item.url)}</div></article>`).join('')}</section>` : ''}`;
  }

  function filterSelect(label, key, values, selected, catalog) {
    return `<label class="filter-select"><span>${esc(label)}</span><select data-catalog="${catalog}" data-filter="${key}" aria-label="${esc(label)}"><option value="">All ${esc(label.toLowerCase())}</option>${values.map(item => `<option value="${esc(item.value)}"${String(selected) === String(item.value) ? ' selected' : ''}>${esc(item.label)}</option>`).join('')}</select></label>`;
  }
  function eventDate(event) {
    return [displayDate(event.start_date), event.end_date && event.end_date !== event.start_date ? displayDate(event.end_date) : ''].filter(Boolean).join(' – ');
  }
  function eventStatus(event) {
    return event.status || (event.start_date && event.start_date > todaySeoul() ? 'Upcoming' : '');
  }
  function renderPresentations() { renderCatalogue('presentations'); }
  function renderCatalogue(catalog) {
    const isTalk = catalog === 'presentations';
    const rows = isTalk ? presentations : publications;
    const filters = state[catalog];
    const years = unique(rows.map(record => record.year)).sort((a, b) => b - a).map(year => ({ value: year, label: year }));
    const kinds = unique(rows.map(record => isTalk ? record.presentation_type || '__unspecified__' : record.item_type)).sort().map(value => ({ value, label: isTalk ? (value === '__unspecified__' ? 'Type not specified' : value) : types[value] || value }));
    const options = unique(rows.flatMap(record => arr(record.roles))).map(value => ({ value, label: roles[value] || value }));
    const eventOptions = publicRows(site.events).map(event => ({ value: event.id, label: event.title }));
    app.innerHTML = heading(isTalk ? 'TALKS · CONFERENCES · SEMINARS' : 'PAPERS · PROCEEDINGS · DATA', isTalk ? 'Presentations' : 'Publications', isTalk ? 'Explore conference contributions, invited talks, posters, and seminars.' : 'Explore research articles, conference papers, datasets, and the doctoral thesis.') +
      `<section class="filter-bar" aria-label="${isTalk ? 'Presentation' : 'Publication'} filters"><label class="search-field"><span class="visually-hidden">Search ${catalog}</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" stroke="currentColor" stroke-width="1.7"/><path d="m16 16 4.5 4.5" stroke="currentColor" stroke-width="1.7"/></svg><input type="search" data-catalog="${catalog}" data-filter="query" placeholder="Search title, author, ${isTalk ? 'event' : 'journal, DOI'}, or keyword…" value="${esc(filters.query)}" autocomplete="off"></label>${filterSelect('Years', 'year', years, filters.year, catalog)}${filterSelect('Types', 'type', kinds, filters.type, catalog)}${!isTalk ? filterSelect('Roles', 'role', options, filters.role, catalog) : eventOptions.length ? filterSelect('Events', 'eventId', eventOptions, filters.eventId, catalog) : ''}<button type="button" class="text-link clear-filters" data-clear-catalog="${catalog}">Reset</button></section>
      <div class="results-header"><p id="result-count" role="status" aria-live="polite"></p><span class="quiet small">Newest first</span></div><div id="catalog-results" class="record-list"></div><div id="catalog-more" class="load-more"></div>`;
    updateCatalogue(catalog);
  }
  function matchingRecords(catalog) {
    const filters = state[catalog];
    const isTalk = catalog === 'presentations';
    return (isTalk ? presentations : publications).filter(record => {
      const detail = content[record.id] || {};
      const linkedEvent = publicRows(site.events).find(event => event.id === detail.event_id);
      const corpus = normalize([record.title, ...arr(record.authors), ...arr(record.authors).map(authorName), record.venue, record.place, record.doi, ...arr(record.manual_tags), ...arr(record.automatic_tags), ...list(detail.tags), record.presentation_type, linkedEvent?.title].filter(Boolean).join(' '));
      const terms = normalize(filters.query).split(' ').filter(Boolean);
      return terms.every(term => corpus.includes(term)) && (!filters.year || String(record.year) === filters.year) && (!filters.type || (isTalk ? record.presentation_type || '__unspecified__' : record.item_type) === filters.type) && (!filters.role || arr(record.roles).includes(filters.role)) && (!filters.eventId || detail.event_id === filters.eventId);
    });
  }
  function catalogueGroups(rows) {
    const groups = [];
    for (const record of rows) {
      const year = String(record.year || 'Year not specified');
      if (!groups.length || groups[groups.length - 1].year !== year) groups.push({ year, rows: [] });
      groups[groups.length - 1].rows.push(record);
    }
    return groups.map(group => `<section class="catalog-year-group" aria-label="${esc(group.year)}"><h2 class="catalog-year-heading">${esc(group.year)}</h2>${group.rows.map(record => recordCard(record)).join('')}</section>`).join('');
  }
  function updateCatalogue(catalog) {
    const matches = matchingRecords(catalog);
    const total = catalog === 'presentations' ? presentations.length : publications.length;
    const limit = state[catalog].limit;
    document.getElementById('result-count').innerHTML = `<strong>${matches.length}</strong> of ${total} ${catalog === 'presentations' ? 'presentations' : 'records'}`;
    document.getElementById('catalog-results').innerHTML = matches.length ? catalogueGroups(matches.slice(0, limit)) : empty('No matching records');
    document.getElementById('catalog-more').innerHTML = matches.length > limit ? `<button type="button" class="button button-secondary" data-load-more="${catalog}">Show more <span class="quiet">(${Math.min(20, matches.length - limit)})</span></button><p class="quiet small">Showing ${Math.min(limit, matches.length)} of ${matches.length}</p>` : '';
  }

  function renderPeople() {
    const people = publicRows(site.people);
    const categories = ['Members', 'Alumni', 'Visitors'].filter(category => people.some(person => person.category === category));
    const selectedId = new URLSearchParams(location.hash.split('?')[1] || '').get('person');
    const selected = people.find(person => person.id === selectedId);
    if (selected) state.people.category = selected.category;
    if (!categories.includes(state.people.category)) state.people.category = categories[0] || '';
    app.innerHTML = heading('THE PEOPLE BEHIND THE RESEARCH', 'People', 'Researchers, collaborators, and visitors in thermoelectric science.') + chips(categories, state.people.category, 'data-people-category') + '<div id="people-results" class="people-grid"></div>';
    updatePeople();
    if (selected) document.getElementById(`person-${selected.id}`)?.focus({ preventScroll: true });
  }
  function updatePeople() {
    const rows = publicRows(site.people).filter(person => person.category === state.people.category);
    document.getElementById('people-results').innerHTML = rows.length ? rows.map(person => `<article class="person-card" id="person-${esc(person.id)}" tabindex="-1">${avatar(person)}<div><p class="eyebrow">${esc(person.title || person.category)}</p><h2>${esc(person.name)}</h2>${person.affiliation ? `<p class="person-meta">${esc(person.affiliation)}</p>` : ''}${person.period ? `<p class="person-meta quiet">${esc(person.period)}</p>` : ''}${person.description ? `<p class="long-text">${esc(person.description)}</p>` : ''}${external('Profile', person.url)}</div></article>`).join('') : empty('No people in this category', '');
    app.querySelectorAll('[data-people-category]').forEach(button => {
      const active = button.dataset.peopleCategory === state.people.category;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
  }
  function newsItems() {
    return [...publicRows(site.news).map(item => ({ ...item, type: 'news', sortDate: item.date || '' })),
      ...publicRows(site.events).map(item => ({ ...item, type: 'events', sortDate: item.start_date || '' }))]
      .sort((a, b) => b.sortDate.localeCompare(a.sortDate) || String(a.id).localeCompare(String(b.id)));
  }
  function renderNews() {
    const years = unique(newsItems().map(item => item.sortDate.slice(0, 4))).sort().reverse();
    app.innerHTML = heading('RESEARCH · COMMUNITY · GATHERINGS', 'News & Events', 'News from the group, workshops, conferences, and upcoming events.') +
      `<nav class="section-tabs" aria-label="News and event views">${[['all', 'All'], ['news', 'News'], ['events', 'Events']].map(([view, label]) => `<button type="button" data-news-view="${view}" aria-pressed="${state.news.type === view}">${label}</button>`).join('')}</nav>
      <section class="filter-bar" aria-label="News and event filters"><label class="search-field"><span class="visually-hidden">Search news and events</span><input type="search" data-news-search placeholder="Search news, events, or places…" value="${esc(state.news.query)}" autocomplete="off"></label><label class="filter-select"><span>Years</span><select data-news-year aria-label="News and event year"><option value="">All years</option>${years.map(year => `<option value="${esc(year)}"${state.news.year === year ? ' selected' : ''}>${esc(year)}</option>`).join('')}</select></label><button type="button" class="text-link clear-filters" data-clear-news>Reset</button></section><div class="results-header"><p id="news-count" role="status" aria-live="polite"></p><span class="quiet small">Newest first</span></div><div id="news-results" class="timeline"></div>`;
    updateNews();
  }
  function updateNews() {
    const items = newsItems();
    const terms = normalize(state.news.query).split(' ').filter(Boolean);
    const matches = items.filter(item => (state.news.type === 'all' || item.type === state.news.type) &&
      (!state.news.year || item.sortDate.startsWith(state.news.year)) &&
      terms.every(term => normalize([item.title, item.body, item.description, item.place, item.category, item.status].join(' ')).includes(term)));
    document.getElementById('news-count').textContent = `${matches.length} ${state.news.type === 'all' ? 'news & events' : state.news.type === 'news' ? 'news items' : 'events'}`;
    document.getElementById('news-results').innerHTML = matches.length ? matches.map(item => {
      const isEvent = item.type === 'events';
      const linked = isEvent ? presentations.filter(record => content[record.id]?.event_id === item.id) : [];
      const status = isEvent ? eventStatus(item) : '';
      return `<article class="timeline-item${isEvent ? ' event-card' : ''}" data-update-type="${item.type}"><div class="news-date">${esc(isEvent ? eventDate(item) || 'Date to be announced' : displayDate(item.date))}</div><div><p class="eyebrow">${isEvent ? 'EVENT' : 'NEWS'}${isEvent && item.category ? ` · ${esc(item.category)}` : ''}</p><h2>${esc(item.title)}</h2>${status ? `<span class="badge">${esc(status)}</span>` : ''}${item.featured ? '<span class="badge">Highlighted update</span>' : ''}${isEvent && item.place ? `<p class="event-place">${esc(item.place)}</p>` : ''}${item.body || item.description ? `<p class="long-text">${esc(item.body || item.description)}</p>` : ''}${contentImage(item.image, item.image_alt || '')}<div class="event-actions">${external(isEvent ? 'Event website' : 'Related link', item.url)}${linked.length ? `<button type="button" class="text-link" data-event-records="${esc(item.id)}">View ${linked.length} presentation${linked.length === 1 ? '' : 's'} <span class="arrow-right" aria-hidden="true"></span></button>` : ''}</div></div></article>`;
    }).join('') : empty('No matching news or events');
  }
  function timelineSection(title, rows) {
    return rows.length ? `<section class="detail-section"><h2>${esc(title)}</h2><div class="career-list">${rows.map(row => `<article><span class="quiet small">${esc(row.period || '')}</span><div><h3>${esc(row.title || '')}</h3>${row.organization ? `<p>${esc(row.organization)}</p>` : ''}</div></article>`).join('')}</div></section>` : '';
  }
  function renderAbout() {
    const email = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(profile.email || '') ? profile.email : '';
    app.innerHTML = heading('PHYSICS · MATERIALS · THERMOELECTRICS', `About ${profile.name || 'Byungki Ryu'}`, profile.description || '') + `<div class="about-grid"><aside class="profile-summary">${avatar({ ...profile, name: profile.name || 'Byungki Ryu' }, true)}<h2>${esc(profile.name || 'Byungki Ryu')}</h2><p>${esc(profile.role || '')}</p><p>${esc(profile.institution || '')}</p>${profile.location ? `<p class="quiet">${esc(profile.location)}</p>` : ''}<div class="profile-contact">${email ? `<a class="text-link" href="mailto:${esc(email)}">${esc(email)}</a>` : ''}${publicRows(profile.links).map(link => external(link.label, link.url)).join('')}</div></aside><div>${timelineSection('Experience', publicRows(profile.career))}${timelineSection('Education', publicRows(profile.education))}${timelineSection('Awards & recognition', publicRows(profile.awards))}${publicRows(profile.about_sections).map(section => `<section class="detail-section"><h2>${esc(section.title)}</h2><ul>${list(section.entries).map(entry => `<li>${esc(entry)}</li>`).join('')}</ul></section>`).join('')}</div></div>`;
  }
  function renderLinks() {
    const categories = unique(publicRows(site.links).map(link => link.category));
    app.innerHTML = heading('OPEN TOOLS · DATA · SOFTWARE', 'Resources for research', 'Explore databases, models, and tools connected to our research.') + `<section class="filter-bar"><label class="search-field"><span class="visually-hidden">Search resources</span><input type="search" data-link-search placeholder="Search tools and datasets…" value="${esc(state.links.query)}"></label><label class="filter-select"><span>Category</span><select data-link-category aria-label="Resource category"><option value="">All categories</option>${categories.map(category => `<option value="${esc(category)}"${state.links.category === category ? ' selected' : ''}>${esc(category)}</option>`).join('')}</select></label></section><p class="quiet small" id="link-count" role="status"></p><div class="link-grid" id="link-results"></div>`;
    updateLinks();
  }
  function updateLinks() {
    const matches = publicRows(site.links).filter(link => (!state.links.category || link.category === state.links.category) && normalize([link.title, link.description, link.category].join(' ')).includes(normalize(state.links.query)));
    document.getElementById('link-count').textContent = `${matches.length} resources`;
    document.getElementById('link-results').innerHTML = matches.length ? matches.map(link => `<article class="link-card"><p class="eyebrow">${esc(link.category || 'Resource')}</p><h2>${esc(link.title)}</h2><p class="long-text">${esc(link.description || '')}</p>${contentImage(link.image, link.image_alt || '')}${external('Explore resource', link.url)}</article>`).join('') : empty('No matching resources');
  }

  const projectPoint = (longitude, latitude) => [(Number(longitude) + 180) / 360 * 960, (90 - Number(latitude)) / 180 * 480];
  function landPaths() {
    const world = data.world;
    const features = world?.type === 'FeatureCollection' ? world.features : world?.type === 'Feature' ? [world] : world ? [{ geometry: world }] : [];
    const polygons = features.flatMap(feature => {
      const geometry = feature.geometry;
      return geometry?.type === 'Polygon' ? [geometry.coordinates] : geometry?.type === 'MultiPolygon' ? geometry.coordinates : [];
    });
    return polygons.map(polygon => `<path d="${polygon.map(ring => ring.map((coordinate, index) => `${index ? 'L' : 'M'}${projectPoint(...coordinate).map(value => value.toFixed(1)).join(',')}`).join('') + 'Z').join('')}"/>`).join('');
  }
  function hasMapCoordinates(point) {
    return [point.lat, point.lon].every(value => value !== null && value !== undefined && String(value).trim() !== '' && Number.isFinite(Number(value))) && Math.abs(Number(point.lat)) <= 90 && Math.abs(Number(point.lon)) <= 180;
  }
  function mapRows() {
    return publicRows((site.maps || {})[state.maps.mode]).filter(point => normalize([point.name, point.place, point.description].join(' ')).includes(normalize(state.maps.query)));
  }
  function renderMaps() {
    const visitors = state.maps.mode === 'visitors';
    const selectedLabel = Object.keys(mapModes).find(label => mapModes[label] === state.maps.mode);
    app.innerHTML = heading('SCIENTIFIC EXCHANGE', 'Research around the world', 'Explore collaborations, places visited, and our website visitors.') + `<div class="map-controls">${chips(Object.keys(mapModes), selectedLabel, 'data-map-mode')}${visitors ? '' : `<label class="search-field map-search"><span class="visually-hidden">Search locations</span><input type="search" data-map-search placeholder="Search an institution or place…" value="${esc(state.maps.query)}"></label>`}</div>${visitors ? '' : '<div class="map-panel"><div id="map-canvas" class="world-map"></div><div class="map-count" id="map-count" role="status"></div></div><div class="map-layout"><div id="map-detail" class="map-detail"></div><div id="map-list" class="map-list"></div></div>'}`;
    syncVisitorPanel();
    if (!visitors) updateMaps();
  }
  function syncVisitorPanel() {
    const active = state.page === 'maps' && state.maps.mode === 'visitors';
    app.classList.toggle('is-visitor-view', active);
    if (!visitorPanel) return;
    visitorPanel.classList.toggle('is-parked', !active);
    visitorPanel.inert = !active;
    visitorPanel.setAttribute('aria-hidden', String(!active));
  }
  function initVisitorWidget() {
    const widget = document.getElementById('visitor-widget');
    const status = document.getElementById('visitor-status');
    if (!widget || !status || document.getElementById('mapmyvisitors')) return;
    // Do not add development and downloaded-preview visits to the live counter.
    if (location.hostname !== 'byungkiryu.github.io' || !location.pathname.startsWith('/bresearch/')) {
      status.textContent = 'The visitor map is available on the published website. You can open the statistics using the link above.';
      return;
    }
    const fallback = () => {
      status.hidden = false;
      status.textContent = 'The visitor map could not be loaded. Open Visitor counts & statistics above to see the recorded visits.';
    };
    // Wait for a rendered image, canvas or frame, not just the script's load event.
    const hasMap = () => [...widget.querySelectorAll('img')].some(img => img.complete && img.naturalWidth > 10) ||
      Boolean(widget.querySelector('canvas, svg, iframe[data-visitor-loaded]'));
    const checkMap = () => {
      if (!hasMap()) return;
      status.hidden = true;
      clearTimeout(timeout);
    };
    widget.addEventListener('load', event => {
      if (event.target.tagName === 'IFRAME') event.target.dataset.visitorLoaded = 'true';
      checkMap();
    }, true);
    const observer = new MutationObserver(checkMap);
    observer.observe(widget, { childList: true, subtree: true });
    const timeout = setTimeout(fallback, 15000);
    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.id = 'mapmyvisitors';
    script.src = 'https://mapmyvisitors.com/map.js?d=-00QWIWpD4vLg07w0VXFdgovJq5gd6V1O1ndzMcoBH4&cl=ffffff&w=a';
    script.async = true;
    script.onerror = () => { clearTimeout(timeout); fallback(); };
    widget.appendChild(script);
  }
  function updateMaps() {
    if (state.maps.mode === 'visitors') return;
    const points = mapRows();
    if (!points.some(point => point.id === state.maps.selected)) state.maps.selected = points[0]?.id || null;
    const selected = points.find(point => point.id === state.maps.selected);
    const groups = new Map();
    for (const point of points.filter(hasMapCoordinates)) {
      const key = `${Number(point.lat).toFixed(2)},${Number(point.lon).toFixed(2)}`;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(point);
    }
    const markers = [...groups.values()].map(group => {
      const current = group.find(point => point.id === state.maps.selected) || group[0];
      const [x, y] = projectPoint(current.lon, current.lat);
      const isSelected = group.some(point => point.id === state.maps.selected);
      return `<g class="map-point${isSelected ? ' is-selected' : ''}" transform="translate(${x.toFixed(2)} ${y.toFixed(2)})" tabindex="0" role="button" data-select-map="${esc(current.id)}" aria-label="${esc(`${current.name}${current.place ? ', ' + current.place : ''}${group.length > 1 ? ', ' + group.length + ' records at this location' : ''}`)}"><title>${esc(current.name)}</title><circle class="map-point-halo" r="${isSelected ? '15' : '11'}"/><circle class="map-point-core" r="${group.length > 1 ? '5.8' : '4.3'}"/>${group.length > 1 ? `<text class="map-point-label" y="-11" text-anchor="middle">${group.length}</text>` : ''}</g>`;
    }).join('');
    const grid = [-120, -60, 0, 60, 120].map(lon => `<path d="M${projectPoint(lon, 90)[0]},0V480"/>`).join('') + [-60, -30, 0, 30, 60].map(lat => `<path d="M0,${projectPoint(-180, lat)[1]}H960"/>`).join('');
    document.getElementById('map-canvas').innerHTML = `<svg viewBox="0 0 960 480" role="group" aria-label="${state.maps.mode === 'collaborations' ? 'Collaboration' : 'Visit'} locations. Select a point or use the location list."><rect class="map-ocean" width="960" height="480"/><g class="map-grid">${grid}</g><g class="map-land">${landPaths()}</g><g class="map-markers">${markers}</g></svg>`;
    const unmapped = points.filter(point => !hasMapCoordinates(point)).length;
    document.getElementById('map-count').textContent = `${points.length} ${state.maps.mode === 'collaborations' ? 'collaboration records' : 'visit records'} · ${groups.size} mapped locations${unmapped ? ` · ${unmapped} coordinates unconfirmed (미확인)` : ''}`;
    const coordinates = selected && hasMapCoordinates(selected) ? `<p class="quiet small">${Math.abs(Number(selected.lat)).toFixed(2)}° ${Number(selected.lat) >= 0 ? 'N' : 'S'} · ${Math.abs(Number(selected.lon)).toFixed(2)}° ${Number(selected.lon) >= 0 ? 'E' : 'W'}</p>${external('View on OpenStreetMap', `https://www.openstreetmap.org/?mlat=${encodeURIComponent(selected.lat)}&mlon=${encodeURIComponent(selected.lon)}#map=12/${encodeURIComponent(selected.lat)}/${encodeURIComponent(selected.lon)}`)}` : '<p class="quiet small">Coordinates unconfirmed (미확인) · This visit is listed without a map marker.</p>';
    document.getElementById('map-detail').innerHTML = selected ? `<p class="eyebrow">SELECTED LOCATION</p><h2>${esc(selected.name)}</h2>${selected.place ? `<p>${esc(selected.place)}</p>` : ''}${selected.description ? `<p class="quiet long-text">${esc(selected.description)}</p>` : ''}${contentImage(selected.image, selected.image_alt || '')}${coordinates}${external('Related link', selected.url)}` : empty('No matching locations');
    document.getElementById('map-list').innerHTML = points.length ? points.map(point => `<button type="button" class="map-list-item${point.id === state.maps.selected ? ' is-selected' : ''}" data-select-map="${esc(point.id)}" aria-pressed="${point.id === state.maps.selected}"><strong>${esc(point.name)}</strong><span>${esc(point.place || '')}</span>${state.maps.mode === 'visits' && point.description ? `<span>${esc(point.description.split('\n')[0])}</span>` : ''}${!hasMapCoordinates(point) ? '<span>Coordinates unconfirmed (미확인)</span>' : ''}<span class="arrow-up-right" aria-hidden="true"></span></button>`).join('') : empty('No matching locations');
    app.querySelectorAll('[data-map-mode]').forEach(button => {
      const active = mapModes[button.dataset.mapMode] === state.maps.mode;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
  }

  function openRecord(id) {
    const record = records.get(id);
    if (!record || !dialog || !dialogContent) return;
    const detail = content[id] || {};
    const tags = unique([...arr(record.manual_tags).filter(tag => !tag.startsWith('BR:')), ...arr(record.automatic_tags), ...list(detail.tags)]);
    const image = imageUrl(detail.image);
    const linkedEvent = publicRows(site.events).find(event => event.id === detail.event_id);
    const relatedPeople = list(detail.person_ids).map(personId => publicRows(site.people).find(person => person.id === personId)).filter(Boolean);
    const eventSection = linkedEvent ? `<section class="detail-section linked-event"><h3>Linked event</h3><p class="linked-event-title">${esc(linkedEvent.title)}</p><dl class="metadata-grid">${[['Event dates', eventDate(linkedEvent) || '미확인'], ['Location', linkedEvent.place], ['Category', linkedEvent.category], ['Status', eventStatus(linkedEvent)]].filter(([, value]) => value).map(([label, value]) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl>${linkedEvent.description ? `<p class="long-text">${esc(linkedEvent.description)}</p>` : ''}${external('Event website', linkedEvent.url)}</section>` : '';
    const peopleSection = relatedPeople.length ? `<section class="detail-section"><h3>Related people</h3><div class="related-people">${relatedPeople.map(person => `<a class="text-link" href="#people?person=${esc(encodeURIComponent(person.id))}">${esc(person.name)} <span class="arrow-right" aria-hidden="true"></span></a>`).join('')}</div></section>` : '';
    const externalLinks = arr(detail.links).map(link => external(link.label || 'Related resource', link.url)).join('');
    const metaRows = [
      [linkedEvent ? 'Record date' : 'Date', displayDate(record.date)],
      [record.kind === 'presentation' ? 'Event' : 'Publication', record.venue],
      ['Location', record.place], ['Type', typeLabel(record)],
      ['Volume', record.volume], ['Issue', record.issue], ['Pages / article number', record.pages],
      ['DOI', record.doi],
    ].filter(([, value]) => value);
    dialogContent.innerHTML = `<div class="dialog-header"><p class="eyebrow">${esc(record.year)} · ${esc(typeLabel(record))}</p><h2 id="record-detail-title">${esc(record.title)}</h2><p class="record-authors">${authorsHtml(record.authors)}</p><div class="record-meta">${roleBadges(record)}${upcoming(record) ? '<span class="badge badge-upcoming">Upcoming</span>' : ''}</div></div><dl class="metadata-grid">${metaRows.map(([label, value]) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl>${detail.summary ? `<section class="detail-section"><h3>Research notes</h3><p class="long-text">${esc(detail.summary)}</p></section>` : ''}${image ? `<figure class="detail-image"><img src="${esc(image)}" alt="${esc(detail.image_alt || '')}" loading="lazy">${detail.image_alt ? `<figcaption>${esc(detail.image_alt)}</figcaption>` : ''}</figure>` : ''}${eventSection}${peopleSection}${tags.length ? `<section class="detail-section"><h3>Keywords</h3><div class="chip-group">${tags.map(tag => `<span class="tag">${esc(tag)}</span>`).join('')}</div></section>` : ''}<section class="detail-section"><h3>Citation</h3><p class="citation-text">${esc(citation(record))}</p></section><div class="dialog-actions">${external(record.doi ? 'Open DOI' : 'Open website', sourceUrl(record), 'button')}<button type="button" class="button button-secondary" data-copy-record="${esc(record.id)}">Copy citation</button>${externalLinks}</div>`;
    dialog.setAttribute('aria-labelledby', 'record-detail-title');
    dialogReturnFocus = document.activeElement;
    if (!dialog.open) dialog.showModal();
    document.getElementById('dialog-close')?.focus();
  }
  function closeDialog() { dialog?.close(); }
  function getPage() {
    const hash = location.hash.slice(1).split('?')[0];
    return Object.hasOwn(pageNames, hash) ? hash : 'research';
  }
  function renderPage(scroll = false) {
    state.page = getPage();
    const params = new URLSearchParams(location.hash.split('?')[1] || '');
    if (state.page === 'research') state.researchView = ['projects', 'facilities'].includes(params.get('view')) ? params.get('view') : 'overview';
    if (state.page === 'news') state.news.type = ['news', 'events'].includes(params.get('view')) ? params.get('view') : 'all';
    if (state.page === 'presentations' && params.has('event')) {
      state.presentations.eventId = publicRows(site.events).some(item => item.id === params.get('event')) ? params.get('event') : '';
    }
    if (state.page === 'maps') {
      const view = new URLSearchParams(location.hash.split('?')[1] || '').get('view');
      if (Object.values(mapModes).includes(view)) state.maps.mode = view;
    }
    syncVisitorPanel();
    closeDialog();
    document.title = `${pageNames[state.page]} — ${home.site_title || 'Byungki Ryu · TES'}`;
    document.querySelectorAll('a[data-page]').forEach(link => {
      const active = link.dataset.page === state.page;
      link.classList.toggle('is-active', active);
      if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
    });
    const renderers = { research: renderResearch, people: renderPeople, publications: () => renderCatalogue('publications'), presentations: renderPresentations, news: renderNews, about: renderAbout, maps: renderMaps, links: renderLinks };
    renderers[state.page]();
    if (scroll) window.scrollTo({ top: 0, behavior: 'instant' });
  }

  app.addEventListener('input', event => {
    const target = event.target;
    if (target.matches('[data-catalog][data-filter="query"]')) {
      const catalog = target.dataset.catalog;
      state[catalog].query = target.value;
      state[catalog].limit = 20;
      updateCatalogue(catalog);
    } else if (target.matches('[data-news-search]')) {
      state.news.query = target.value;
      updateNews();
    } else if (target.matches('[data-link-search]')) {
      state.links.query = target.value;
      updateLinks();
    } else if (target.matches('[data-map-search]')) {
      state.maps.query = target.value;
      updateMaps();
    }
  });
  app.addEventListener('change', event => {
    const target = event.target;
    if (target.matches('select[data-catalog]')) {
      const catalog = target.dataset.catalog;
      state[catalog][target.dataset.filter] = target.value;
      state[catalog].limit = 20;
      if (catalog === 'presentations' && target.dataset.filter === 'eventId') history.replaceState(null, '', target.value ? `#presentations?event=${encodeURIComponent(target.value)}` : '#presentations');
      updateCatalogue(catalog);
    } else if (target.matches('[data-news-year]')) {
      state.news.year = target.value;
      updateNews();
    } else if (target.matches('[data-link-category]')) {
      state.links.category = target.value;
      updateLinks();
    }
  });
  app.addEventListener('click', event => {
    const target = event.target.closest('button, [data-select-map]');
    if (!target) return;
    if (target.hasAttribute('data-open-record')) openRecord(target.dataset.openRecord);
    else if (target.hasAttribute('data-copy-record')) copyText(citation(records.get(target.dataset.copyRecord)));
    else if (target.hasAttribute('data-load-more')) {
      state[target.dataset.loadMore].limit += 20;
      updateCatalogue(target.dataset.loadMore);
    } else if (target.hasAttribute('data-news-view')) {
      state.news.type = target.dataset.newsView;
      history.replaceState(null, '', state.news.type === 'all' ? '#news' : `#news?view=${state.news.type}`);
      renderNews();
      app.querySelector(`[data-news-view="${state.news.type}"]`)?.focus({ preventScroll: true });
    } else if (target.hasAttribute('data-event-records')) {
      state.presentations = { query: '', year: '', type: '', eventId: target.dataset.eventRecords, limit: 20 };
      location.hash = `presentations?event=${encodeURIComponent(target.dataset.eventRecords)}`;
    } else if (target.hasAttribute('data-clear-news')) {
      state.news = { type: state.news.type, query: '', year: '' };
      renderNews();
      app.querySelector('[data-news-search]')?.focus();
    } else if (target.hasAttribute('data-clear-catalog')) {
      const catalog = target.dataset.clearCatalog;
      state[catalog] = { query: '', year: '', type: '', role: '', eventId: '', limit: 20 };
      if (catalog === 'presentations') history.replaceState(null, '', '#presentations');
      renderCatalogue(catalog);
      app.querySelector('input[type="search"]')?.focus();
    } else if (target.hasAttribute('data-people-category')) {
      state.people.category = target.dataset.peopleCategory;
      updatePeople();
    } else if (target.hasAttribute('data-topic-search')) {
      state.publications = { query: target.dataset.topicSearch, year: '', type: '', role: '', limit: 20 };
      location.hash = 'publications';
    } else if (target.hasAttribute('data-map-mode')) {
      state.maps.mode = mapModes[target.dataset.mapMode] || 'collaborations';
      state.maps.selected = null;
      history.replaceState(null, '', `#maps?view=${state.maps.mode}`);
      renderMaps();
      app.querySelector(`[data-map-mode="${target.dataset.mapMode}"]`)?.focus({ preventScroll: true });
    } else if (target.hasAttribute('data-select-map')) {
      state.maps.selected = target.dataset.selectMap;
      updateMaps();
      const selector = target.tagName.toLowerCase() === 'g' ? 'g' : 'button';
      app.querySelector(`${selector}[data-select-map="${CSS.escape(state.maps.selected)}"]`)?.focus({ preventScroll: true });
    }
  });
  app.addEventListener('keydown', event => {
    if (event.target.matches('g[data-select-map]') && ['Enter', ' '].includes(event.key)) {
      event.preventDefault();
      state.maps.selected = event.target.dataset.selectMap;
      updateMaps();
      app.querySelector(`g[data-select-map="${CSS.escape(state.maps.selected)}"]`)?.focus({ preventScroll: true });
    }
  });
  dialog?.addEventListener('click', event => {
    const button = event.target.closest('[data-copy-record]');
    if (button) copyText(citation(records.get(button.dataset.copyRecord)));
    if (event.target === dialog) {
      const box = dialog.getBoundingClientRect();
      if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) closeDialog();
    }
  });
  document.getElementById('dialog-close')?.addEventListener('click', closeDialog);
  dialog?.addEventListener('close', () => { if (dialogReturnFocus?.isConnected) dialogReturnFocus.focus(); });
  window.addEventListener('hashchange', () => renderPage(true));
  applySiteIdentity();
  renderPage();
  initVisitorWidget();
})();

