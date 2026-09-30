document.addEventListener('DOMContentLoaded', () => {
    const user = JSON.parse(localStorage.getItem('user'));
    if (!user) { window.location.href = 'login.html'; return; }

    const mockHotels = [
        {
            id: 1, name: 'Grand Plaza Hotel', location: 'New York', stars: 5,
            rooms: [
                { id: 1, type: 'Standard',  price: 120, available: true },
                { id: 2, type: 'Deluxe',    price: 200, available: true },
                { id: 3, type: 'Suite',      price: 350, available: false }
            ]
        },
        {
            id: 2, name: 'Ocean View Resort', location: 'Miami', stars: 4,
            rooms: [
                { id: 1, type: 'Oceanfront', price: 250, available: true },
                { id: 2, type: 'Garden',      price: 180, available: true }
            ]
        },
        {
            id: 3, name: 'Mountain Lodge', location: 'Denver', stars: 3,
            rooms: [
                { id: 1, type: 'Standard',  price: 90,  available: true },
                { id: 2, type: 'Family',    price: 150, available: true }
            ]
        }
    ];

    let currentHotelId  = null;
    let currentRoomId   = null;
    let filteredHotels  = mockHotels;

    const listView    = document.getElementById('listView');
    const detailView  = document.getElementById('detailView');
    const containerEl = document.getElementById('hotelListContainer');
    const bookSection = document.getElementById('bookingSection');
    const bookingMsg  = document.getElementById('bookingMsg');

    function renderList(hotels) {
        containerEl.innerHTML = '';
        if (!hotels.length) { containerEl.innerHTML = '<p style="color:#888;">No hotels found.</p>'; return; }
        hotels.forEach(h => {
            const d = document.createElement('div');
            d.className = 'list-item';
            d.innerHTML = `
                <strong>${h.name}</strong>
                <p>Location: ${h.location} &nbsp;|&nbsp; ${'★'.repeat(h.stars)}</p>
                <p style="font-size:0.8rem;color:#888;">${h.rooms.filter(r=>r.available).length} room(s) available</p>
                <button onclick="openHotel(${h.id})">View Details</button>
            `;
            containerEl.appendChild(d);
        });
    }

    window.openHotel = function(id) {
        currentHotelId = id;
        const h = mockHotels.find(x => x.id === id);
        if (!h) return;

        document.getElementById('detailName').textContent     = h.name;
        document.getElementById('detailLocation').textContent = h.location;
        document.getElementById('detailStars').textContent    = '★'.repeat(h.stars) + ` (${h.stars} stars)`;

        const roomDiv = document.getElementById('roomList');
        roomDiv.innerHTML = '';
        h.rooms.forEach(r => {
            const d = document.createElement('div');
            d.className = 'list-item';
            d.innerHTML = `
                <strong>${r.type}</strong>
                <p>$${r.price}/night &nbsp;|&nbsp; ${r.available ? 'Available' : '<span style="color:red;">Not Available</span>'}</p>
                ${r.available ? `<button onclick="startBook(${r.id})">Book This Room</button>` : ''}
            `;
            roomDiv.appendChild(d);
        });

        bookSection.classList.add('hidden');
        listView.classList.add('hidden');
        detailView.classList.remove('hidden');
    };

    window.startBook = function(roomId) {
        currentRoomId = roomId;
        const h = mockHotels.find(x => x.id === currentHotelId);
        const r = h.rooms.find(x => x.id === roomId);
        document.getElementById('bookingRoomLabel').textContent = `Room: ${r.type} – $${r.price}/night`;
        bookingMsg.textContent = '';
        bookSection.classList.remove('hidden');
        bookSection.scrollIntoView({ behavior: 'smooth' });
    };

    document.getElementById('confirmBookBtn').addEventListener('click', () => {
        const ci = document.getElementById('checkIn').value;
        const co = document.getElementById('checkOut').value;
        const g  = document.getElementById('guests').value;
        if (!ci || !co) { bookingMsg.textContent = 'Please select check-in and check-out dates.'; bookingMsg.className = 'msg-error'; return; }
        if (co <= ci) { bookingMsg.textContent = 'Check-out must be after check-in.'; bookingMsg.className = 'msg-error'; return; }

        bookingMsg.textContent = `✓ Booking confirmed! Check-in: ${ci}, Check-out: ${co}, Guests: ${g}`;
        bookingMsg.className = 'msg-success';
    });

    document.getElementById('cancelBookBtn').addEventListener('click', () => {
        bookSection.classList.add('hidden');
    });

    document.getElementById('backBtn').addEventListener('click', () => {
        detailView.classList.add('hidden');
        listView.classList.remove('hidden');
    });

    // Search
    document.getElementById('searchBtn').addEventListener('click', () => {
        const q = document.getElementById('searchInput').value.trim().toLowerCase();
        filteredHotels = q
            ? mockHotels.filter(h => h.name.toLowerCase().includes(q) || h.location.toLowerCase().includes(q))
            : mockHotels;
        renderList(filteredHotels);
    });

    document.getElementById('clearBtn').addEventListener('click', () => {
        document.getElementById('searchInput').value = '';
        filteredHotels = mockHotels;
        renderList(filteredHotels);
    });

    renderList(mockHotels);
});

