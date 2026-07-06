const API = '';
let courses = [];
let favs = [];
let cat = '';
let user = null;
let isLoggedIn = false;

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
const goalBtn = $('goal-btn');
const authBtn = $('auth-btn');
const userBtn = $('user-btn');

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
    await checkAuth();
    await loadStats();
    await loadCourses();
    if (isLoggedIn) {
        await Promise.all([loadFavs(), loadProgress()]);
    }
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

async function checkAuth() {
    try {
        const r = await fetch(`${API}/api/auth/me`);
        const data = await r.json();
        if (!data.logged_in) return;
        user = data;
        isLoggedIn = true;
        updateAuthUI();
    } catch(e) {}
}

function updateAuthUI() {
    authBtn.style.display = 'none';
    userBtn.style.display = 'flex';
    if (user.avatar) {
        userBtn.innerHTML = `<img src="${user.avatar}" alt="">${user.streak ? `<span class="streak-badge">🔥</span>` : ''}`;
    } else {
        userBtn.textContent = user.name.charAt(0).toUpperCase();
    }
    userBtn.onclick = () => window.location.href = '/dashboard';
}

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
    const progress = user ? getProgress(cr.url) : null;
    const review = user ? getReview(cr.url) : null;

    return `
        <div class="row">
            <div class="row-info">
                <div class="row-name">${cr.name}</div>
                <div class="row-meta">
                    <span class="tag ${diff}">${cr.difficulty}</span>
                    <span class="tag source">${cr.source}</span>
                    <span class="tag ${cr.free ? 'free' : 'paid'}">${cr.free ? 'Free' : 'Paid'}</span>
                    ${review ? `<span class="tag" style="background:#fef3c7;color:#f59e0b;">★ ${review.rating}</span>` : ''}
                </div>
            </div>
            <div class="row-actions">
                <button class="fav ${on ? 'on' : ''}" onclick="toggleFav('${cr.url}','${cr.name.replace(/'/g,"\\'")}','${cat}','${cr.difficulty}','${cr.source}',this)" title="${on ? 'Remove' : 'Save'}">
                    <i class="fas fa-heart"></i>
                </button>
                ${isLoggedIn ? `
                    <button class="fav" onclick="openProgress('${cr.url}','${cr.name.replace(/'/g,"\\'")}','${cat}')" title="Track progress">
                        <i class="fas fa-chart-line"></i>
                    </button>
                    <button class="fav" onclick="openReview('${cr.url}','${cr.name.replace(/'/g,"\\'")}')" title="Rate course">
                        <i class="fas fa-star"></i>
                    </button>
                ` : ''}
                <a href="${cr.url}" target="_blank" class="row-link">Visit <i class="fas fa-arrow-right"></i></a>
            </div>
        </div>
    `;
}

function getProgress(url) {
    return progressData?.find(p => p.course_url === url) || null;
}
function getReview(url) {
    return reviewData?.find(r => r.course_url === url) || null;
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

// ===== Favorites =====
async function loadFavs() {
    try {
        const r = await fetch(`${API}/api/favorites`);
        favs = await r.json();
        updateFavCount();
    } catch(e) {}
}

async function toggleFav(url, name, cat, diff, src, btn) {
    if (!isLoggedIn) {
        toast('Sign in to save favorites', '🔐');
        window.location.href = '/login';
        return;
    }
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
                headers: {'Content-Type': 'application/json'},
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
    if (!isLoggedIn) {
        toast('Sign in to view favorites', '🔐');
        window.location.href = '/login';
        return;
    }
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

// ===== Progress =====
let progressData = [];
let selectedProgressUrl = '';
let selectedProgressName = '';
let selectedProgressCat = '';
let selectedStatus = 'not_started';

async function loadProgress() {
    try {
        const r = await fetch(`${API}/api/progress`);
        progressData = await r.json();
    } catch(e) {}
}

function openProgress(url, name, cat) {
    if (!isLoggedIn) { toast('Sign in to track progress', '🔐'); return; }
    selectedProgressUrl = url;
    selectedProgressName = name;
    selectedProgressCat = cat;
    selectedStatus = 'not_started';

    const existing = progressData.find(p => p.course_url === url);
    if (existing) {
        selectedStatus = existing.status;
        $('progress-range').value = existing.progress_pct;
    } else {
        $('progress-range').value = 0;
    }

    updateProgressUI();
    $('progress-modal').classList.add('open');
}

function updateProgressUI() {
    document.querySelectorAll('.status-opt').forEach(b => {
        b.classList.toggle('active', b.dataset.status === selectedStatus);
    });
    $('pct-display').textContent = $('progress-range').value;
}

$('progress-range').oninput = () => {
    $('pct-display').textContent = $('progress-range').value;
    if ($('progress-range').value == 100) selectedStatus = 'completed';
};

document.querySelectorAll('.status-opt').forEach(b => {
    b.onclick = () => {
        selectedStatus = b.dataset.status;
        updateProgressUI();
    };
});

$('submit-progress').onclick = async () => {
    const pct = parseInt($('progress-range').value);
    await fetch(`${API}/api/progress`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            url: selectedProgressUrl,
            name: selectedProgressName,
            category: selectedProgressCat,
            status: selectedStatus,
            progress_pct: pct
        })
    });
    await loadProgress();
    $('progress-modal').classList.remove('open');
    toast('Progress updated!', '📊');
    render();
};

$('close-progress').onclick = () => $('progress-modal').classList.remove('open');
$('progress-modal').onclick = e => { if (e.target.id === 'progress-modal') e.target.classList.remove('open'); };

// ===== Reviews =====
let reviewData = [];
let selectedRating = 0;
let selectedReviewUrl = '';
let selectedReviewName = '';

async function loadReviews() {
    try {
        const r = await fetch(`${API}/api/reviews`);
        reviewData = await r.json();
    } catch(e) {}
}

function openReview(url, name) {
    if (!isLoggedIn) { toast('Sign in to rate courses', '🔐'); return; }
    selectedReviewUrl = url;
    selectedReviewName = name;
    selectedRating = 0;
    $('review-text').value = '';

    const existing = reviewData.find(r => r.course_url === url);
    if (existing) {
        selectedRating = existing.rating;
        $('review-text').value = existing.review || '';
    }

    updateStars();
    $('review-modal').classList.add('open');
}

document.querySelectorAll('.star-rating .star').forEach(s => {
    s.onclick = () => {
        selectedRating = parseInt(s.dataset.rating);
        updateStars();
    };
    s.onmouseenter = () => {
        const r = parseInt(s.dataset.rating);
        document.querySelectorAll('.star-rating .star').forEach((star, i) => {
            star.style.color = i < r ? '#f59e0b' : '';
        });
    };
    s.onmouseleave = () => updateStars();
});

function updateStars() {
    document.querySelectorAll('.star-rating .star').forEach((s, i) => {
        s.classList.toggle('active', i < selectedRating);
        s.style.color = i < selectedRating ? '#f59e0b' : '';
    });
    $('submit-review').disabled = selectedRating === 0;
}

$('submit-review').onclick = async () => {
    await fetch(`${API}/api/reviews`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            url: selectedReviewUrl,
            name: selectedReviewName,
            rating: selectedRating,
            review: $('review-text').value.trim()
        })
    });
    await loadReviews();
    $('review-modal').classList.remove('open');
    toast('Review submitted!', '⭐');
    render();
};

$('close-review').onclick = () => $('review-modal').classList.remove('open');
$('review-modal').onclick = e => { if (e.target.id === 'review-modal') e.target.classList.remove('open'); };

// ===== Goals =====
goalBtn.onclick = () => {
    if (!isLoggedIn) { toast('Sign in to set goals', '🔐'); return; }
    const sel = $('goal-category');
    sel.innerHTML = courses.map(c => `<option value="${c.id}">${c.category}</option>`).join('');
    $('goal-range').value = 5;
    $('goal-display').textContent = '5';
    $('goal-modal').classList.add('open');
};

$('goal-range').oninput = () => { $('goal-display').textContent = $('goal-range').value; };

$('submit-goal').onclick = async () => {
    await fetch(`${API}/api/goals`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            category: $('goal-category').value,
            target: parseInt($('goal-range').value)
        })
    });
    $('goal-modal').classList.remove('open');
    toast('Goal set!', '🎯');
};

$('close-goal').onclick = () => $('goal-modal').classList.remove('open');
$('goal-modal').onclick = e => { if (e.target.id === 'goal-modal') e.target.classList.remove('open'); };

// ===== Toast =====
function toast(msg, icon = '✓') {
    const t = document.createElement('div');
    t.className = 'toast';
    t.innerHTML = `<span>${icon}</span> ${msg}`;
    document.body.appendChild(t);
    requestAnimationFrame(() => t.classList.add('show'));
    setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 2000);
}

// ===== Bind =====
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
        if (e.key === 'Escape') {
            favModal.classList.remove('open');
            $('review-modal').classList.remove('open');
            $('progress-modal').classList.remove('open');
            $('goal-modal').classList.remove('open');
        }
    };
}

init();
