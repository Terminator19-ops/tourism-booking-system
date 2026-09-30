document.addEventListener('DOMContentLoaded', () => {
    const user = JSON.parse(localStorage.getItem('user'));
    if (!user) { window.location.href = 'login.html'; return; }

    // ── Persistent mock data (seed once) ──────────────────────────────────
    const TRIPS_KEY = 'mock_trips';

    function getTrips() {
        const stored = localStorage.getItem(TRIPS_KEY);
        if (stored) return JSON.parse(stored);
        const seed = [
            {
                id: 1, name: 'Summer Vacation', desc: 'Trip to Europe',
                start: '2026-06-01', end: '2026-06-15',
                destinations: ['Paris', 'Rome'],
                bookings: [
                    { type: 'Hotel',    detail: 'Grand Plaza, Paris – 5 nights' },
                    { type: 'Activity', detail: 'Eiffel Tower Tour' }
                ],
                review: null
            },
            {
                id: 2, name: 'Business Trip', desc: 'Conference in New York',
                start: '2026-08-10', end: '2026-08-14',
                destinations: ['New York'],
                bookings: [
                    { type: 'Hotel',  detail: 'Midtown Suites – 4 nights' },
                    { type: 'Travel', detail: 'London → New York (Flight)' }
                ],
                review: { rating: 4, comment: 'Great conference venue.' }
            }
        ];
        localStorage.setItem(TRIPS_KEY, JSON.stringify(seed));
        return seed;
    }

    function saveTrips(trips) { localStorage.setItem(TRIPS_KEY, JSON.stringify(trips)); }

    // ── DOM refs ─────────────────────────────────────────────────────────
    const listView         = document.getElementById('listView');
    const detailView       = document.getElementById('detailView');
    const tripListContainer= document.getElementById('tripListContainer');
    const createTripForm   = document.getElementById('createTripForm');
    const createTripMsg    = document.getElementById('createTripMsg');

    // ── Render trip list ──────────────────────────────────────────────────
    function renderList() {
        const trips = getTrips();
        tripListContainer.innerHTML = '';
        if (!trips.length) {
            tripListContainer.innerHTML = '<p style="color:#888;">No trips yet. Create one!</p>';
            return;
        }
        trips.forEach(t => {
            const d = document.createElement('div');
            d.className = 'list-item';
            d.innerHTML = `
                <strong>${t.name}</strong>
                <p>${t.desc}</p>
                <p style="font-size:0.8rem;color:#888;">${t.start} → ${t.end}</p>
                <button onclick="openDetail(${t.id})">View Details</button>
            `;
            tripListContainer.appendChild(d);
        });
    }

    // ── Create trip ───────────────────────────────────────────────────────
    document.getElementById('createTripBtn').addEventListener('click', () => {
        createTripForm.classList.toggle('hidden');
    });
    document.getElementById('cancelTripBtn').addEventListener('click', () => {
        createTripForm.classList.add('hidden');
    });
    document.getElementById('saveTripBtn').addEventListener('click', () => {
        const name  = document.getElementById('tripNameInput').value.trim();
        const desc  = document.getElementById('tripDescInput').value.trim();
        const start = document.getElementById('tripStartInput').value;
        const end   = document.getElementById('tripEndInput').value;

        if (!name) { createTripMsg.textContent = 'Trip name required.'; createTripMsg.className = 'msg-error'; return; }

        const trips = getTrips();
        trips.push({ id: Date.now(), name, desc, start, end, destinations: [], bookings: [], review: null });
        saveTrips(trips);

        createTripMsg.textContent = 'Trip created!';
        createTripMsg.className = 'msg-success';
        document.getElementById('tripNameInput').value = '';
        document.getElementById('tripDescInput').value = '';
        createTripForm.classList.add('hidden');
        renderList();
    });

    // ── Detail view ───────────────────────────────────────────────────────
    window.openDetail = function(id) {
        const trips = getTrips();
        const t = trips.find(x => x.id === id);
        if (!t) return;

        document.getElementById('detailTripName').textContent = t.name;
        document.getElementById('detailTripDesc').textContent = t.desc;
        document.getElementById('detailTripDates').textContent = `${t.start}  →  ${t.end}`;

        // Destinations
        renderDests(t);
        // Bookings
        renderBookings(t);
        // Review
        renderReview(t);

        listView.classList.add('hidden');
        detailView.classList.remove('hidden');

        // Wire add-dest
        document.getElementById('addDestBtn').onclick = () => document.getElementById('addDestForm').classList.toggle('hidden');
        document.getElementById('cancelDestBtn').onclick = () => document.getElementById('addDestForm').classList.add('hidden');
        document.getElementById('saveDestBtn').onclick = () => {
            const val = document.getElementById('destNameInput').value.trim();
            if (!val) return;
            const trips2 = getTrips();
            const t2 = trips2.find(x => x.id === id);
            t2.destinations.push(val);
            saveTrips(trips2);
            document.getElementById('destNameInput').value = '';
            document.getElementById('addDestForm').classList.add('hidden');
            renderDests(t2);
        };

        // Wire review
        document.getElementById('addReviewBtn').onclick = () => document.getElementById('reviewForm').classList.toggle('hidden');
        document.getElementById('cancelReviewBtn').onclick = () => document.getElementById('reviewForm').classList.add('hidden');
        document.getElementById('saveReviewBtn').onclick = () => {
            const rating  = parseInt(document.getElementById('reviewRating').value) || 0;
            const comment = document.getElementById('reviewComment').value.trim();
            if (rating < 1 || rating > 5) { alert('Rating must be 1–5.'); return; }
            const trips2 = getTrips();
            const t2 = trips2.find(x => x.id === id);
            t2.review = { rating, comment };
            saveTrips(trips2);
            document.getElementById('reviewForm').classList.add('hidden');
            renderReview(t2);
        };
    };

    function renderDests(t) {
        const ul = document.getElementById('destList');
        ul.innerHTML = t.destinations.length
            ? t.destinations.map(d => `<li>${d}</li>`).join('')
            : '<li style="color:#888;">No destinations added.</li>';
    }

    function renderBookings(t) {
        const div = document.getElementById('bookingList');
        div.innerHTML = t.bookings.length
            ? t.bookings.map(b => `<div class="list-item"><strong>${b.type}</strong><p>${b.detail}</p></div>`).join('')
            : '<p style="color:#888;">No bookings yet.</p>';
    }

    function renderReview(t) {
        const div = document.getElementById('reviewDisplay');
        div.innerHTML = t.review
            ? `<p><strong>Rating:</strong> ${t.review.rating}/5</p><p>${t.review.comment}</p>`
            : '<p style="color:#888;">No review yet.</p>';
    }

    document.getElementById('backToListBtn').addEventListener('click', () => {
        detailView.classList.add('hidden');
        listView.classList.remove('hidden');
        renderList();
    });

    // ── Init ─────────────────────────────────────────────────────────────
    renderList();
});

