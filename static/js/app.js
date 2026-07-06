const API = '';
let courses = [];
let favs = [];
let cat = '';

const $ = id => document.getElementById(id);
const searchInput = $('search-input');
const clearBtn = $('clear-search');
const diffFilter = $('difficulty-filter');
const freeChk = $('free-only');
const grid = $('grid');
const tabsEl = $('tabs');
const loading = $('loading');
const themeBtn = $('theme-toggle');
const favBtn = $('fav-toggle');
const favCount = $('fav-count');
const favModal = $('fav-modal');
const closeFav = $('close-modal');
const favList = $('fav-list');
const btt = $('btt');

const ICONS = {
    'web-development': '💻', 'data-science': '📊', 'artificial-intelligence': '🤖',
    'data-analytics': '📈', 'app-development': '📱', 'cyber-security': '🔒',
    'blockchain': '⛓️', 'cloud-computing': '☁️', 'vr-ar': '🥽',
    'devops': '⚙️', 'machine-learning': '🧠', 'deep-learning': '🔬',
    'robotics': '🦾'
};

const CAT_COLORS = {
    'web-development': '#6366f1', 'data-science': '#ec4899', 'artificial-intelligence': '#8b5cf6',
    'data-analytics': '#f59e0b', 'app-development': '#10b981', 'cyber-security': '#ef4444',
    'blockchain': '#06b6d4', 'cloud-computing': '#3b82f6', 'vr-ar': '#f97316',
    'devops': '#64748b', 'machine-learning': '#a855f7', 'deep-learning': '#14b8a6',
    'robotics': '#e11d48'
};

async function init() {
    loadTheme();
    await loadStats();
    await loadCourses();
    await loadFavs();
    bind();
}

function loadTheme() {
    const t = localStorage.getItem('theme');
    if (t === 'dark') {
        document.body.classList.add('dark');
        themeBtn.innerHTML = '<i class="fas fa-sun"></i>';
    }
}

themeBtn.onclick = () => {
    document.body.classList.toggle('dark');
    const d = document.body.classList.contains('dark');
    localStorage.setItem('theme', d ? 'dark' : 'light');
    themeBtn.innerHTML = d ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
};

async function loadStats() {
    try {
        const r = await fetch(`${API}/api/stats`);
        const s = await r.json();
        $('stat-categories').textContent = s.total_categories;
        $('stat-courses').textContent = s.total_courses;
        $('stat-free').textContent = s.free_courses;
        $('stat-favorites').textContent = s.user_favorites;
    } catch(e) {}
}

async function loadCourses() {
    loading.style.display = 'block';
    grid.innerHTML = '<div class="loading" id="loading"><div class="spinner"></div><p>Loading courses...</p></div>';

    const p = new URLSearchParams();
    if (cat) p.set('category', cat);
    const q = searchInput.value.trim();
    if (q) p.set('search', q);
    if (diffFilter.value) p.set('difficulty', diffFilter.value);
    if (freeChk.checked) p.set('free', 'true');

    try {
        const r = await fetch(`${API}/api/courses?${p}`);
        courses = await r.json();
        render();
    } catch(e) {
        grid.innerHTML = '<div class="empty"><div class="icon">⚠️</div><h3>Something broke</h3><p>Check your connection and refresh.</p></div>';
    } finally {
        loading.style.display = 'none';
    }
}

function render() {
    grid.innerHTML = '';
    renderTabs();

    if (courses.length === 0) {
        grid.innerHTML = '<div class="empty"><div class="icon">🔍</div><h3>No courses found</h3><p>Try a different search or filter.</p></div>';
        return;
    }

    courses.forEach((c, i) => {
        const icon = ICONS[c.id] || '📚';
        const color = CAT_COLORS[c.id] || '#6366f1';
        const card = document.createElement('div');
        card.className = 'card';
        card.style.animationDelay = `${i * 0.04}s`;

        card.innerHTML = `
            <div class="card-head" onclick="this.parentElement.classList.toggle('collapsed')">
                <div class="emoji" style="background:${color}15;color:${color}">${icon}</div>
                <div class="info">
                    <div class="title">${c.category}</div>
                    <div class="subtitle">${c.courses.length} courses</div>
                </div>
                <i class="fas fa-chevron-down chevron"></i>
            </div>
            <div class="card-body">
                ${c.courses.map(cr => renderRow(cr, c.category)).join('')}
            </div>
        `;
        grid.appendChild(card);
    });
}

function renderRow(cr, cat) {
    const on = favs.some(f => f.course_url === cr.url);
    const diff = cr.difficulty.toLowerCase();
    return `
        <div class="row">
            <div class="row-info">
                <div class="row-name">${cr.name}</div>
                <div class="row-meta">
                    <span class="tag ${diff}">${cr.difficulty}</span>
                    <span class="tag source">${cr.source}</span>
                    <span class="tag ${cr.free ? 'free' : 'paid'}">${cr.free ? 'Free' : 'Paid'}</span>
                </div>
            </div>
            <div class="row-actions">
                <button class="fav ${on ? 'on' : ''}" onclick="toggleFav('${cr.url}','${cr.name.replace(/'/g,"\\'")}','${cat}','${cr.difficulty}','${cr.source}',this)" title="${on ? 'Remove' : 'Save'}">
                    <i class="fas fa-heart"></i>
                </button>
                <a href="${cr.url}" target="_blank" class="row-link">Visit <i class="fas fa-arrow-right"></i></a>
            </div>
        </div>
    `;
}

function renderTabs() {
    tabsEl.innerHTML = `<button class="tab ${!cat ? 'active' : ''}" onclick="setCat('')">All</button>`;
    courses.forEach(c => {
        const b = document.createElement('button');
        b.className = `tab ${cat === c.id ? 'active' : ''}`;
        b.textContent = c.category;
        b.onclick = () => setCat(c.id);
        tabsEl.appendChild(b);
    });
}

function setCat(id) {
    cat = id;
    loadCourses();
}

async function loadFavs() {
    try {
        const r = await fetch(`${API}/api/favorites`);
        favs = await r.json();
        updateFavCount();
    } catch(e) {}
}

async function toggleFav(url, name, cat, diff, src, btn) {
    const on = favs.some(f => f.course_url === url);
    try {
        if (on) {
            await fetch(`${API}/api/favorites/${encodeURIComponent(url)}`, { method: 'DELETE' });
            favs = favs.filter(f => f.course_url !== url);
            btn.classList.remove('on');
            toast('Removed', '🗑️');
        } else {
            const r = await fetch(`${API}/api/favorites`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, name, category: cat, difficulty: diff, source: src })
            });
            if (r.status === 409) { toast('Already saved', '⚠️'); return; }
            favs.push({ course_url: url, course_name: name, category: cat, difficulty: diff, source: src });
            btn.classList.add('on');
            toast('Saved!', '❤️');
        }
        updateFavCount();
        render();
    } catch(e) { toast('Error', '❌'); }
}

function updateFavCount() {
    favCount.textContent = favs.length;
    favCount.classList.toggle('show', favs.length > 0);
    $('stat-favorites').textContent = favs.length;
}

favBtn.onclick = () => {
    favModal.classList.add('open');
    renderFavList();
};

closeFav.onclick = () => favModal.classList.remove('open');
favModal.onclick = e => { if (e.target === favModal) favModal.classList.remove('open'); };

function renderFavList() {
    if (!favs.length) {
        favList.innerHTML = '<div class="empty-fav">No favorites yet. Tap the heart on any course to save it.</div>';
        return;
    }
    favList.innerHTML = favs.map(f => `
        <div class="fav-row">
            <div class="fav-row-info">
                <div class="fav-row-name">${f.course_name}</div>
                <div class="fav-row-cat">${f.category} · ${f.difficulty} · ${f.source}</div>
            </div>
            <div class="fav-row-actions">
                <a href="${f.course_url}" target="_blank" class="go-btn">Visit <i class="fas fa-arrow-right"></i></a>
                <button class="rm-btn" onclick="rmFav('${f.course_url}')"><i class="fas fa-trash"></i></button>
            </div>
        </div>
    `).join('');
}

async function rmFav(url) {
    await fetch(`${API}/api/favorites/${encodeURIComponent(url)}`, { method: 'DELETE' });
    favs = favs.filter(f => f.course_url !== url);
    updateFavCount();
    renderFavList();
    render();
    toast('Removed', '🗑️');
}

function toast(msg, icon = '✓') {
    const t = document.createElement('div');
    t.className = 'toast';
    t.innerHTML = `<span>${icon}</span> ${msg}`;
    document.body.appendChild(t);
    requestAnimationFrame(() => t.classList.add('show'));
    setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 2000);
}

function bind() {
    let timer;
    searchInput.oninput = () => {
        clearBtn.classList.toggle('show', searchInput.value.length > 0);
        clearTimeout(timer);
        timer = setTimeout(loadCourses, 250);
    };
    clearBtn.onclick = () => { searchInput.value = ''; clearBtn.classList.remove('show'); loadCourses(); searchInput.focus(); };
    diffFilter.onchange = loadCourses;
    freeChk.onchange = loadCourses;

    window.onscroll = () => {
        btt.classList.toggle('show', window.scrollY > 300);
    };
    btt.onclick = () => window.scrollTo({ top: 0, behavior: 'smooth' });

    document.onkeydown = e => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); searchInput.focus(); }
        if (e.key === 'Escape') favModal.classList.remove('open');
    };
}

init();
