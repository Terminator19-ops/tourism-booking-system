document.addEventListener('DOMContentLoaded', () => {
    const user = JSON.parse(localStorage.getItem('user'));
    if (!user) { window.location.href = 'login.html'; return; }

    const mockSegments = [
        { id: 1, origin: 'New York',  dest: 'London',    type: 'Flight', price: 320, duration: '7h' },
        { id: 2, origin: 'London',    dest: 'Paris',     type: 'Train',  price: 55,  duration: '2h 15m' },
        { id: 3, origin: 'Paris',     dest: 'Rome',      type: 'Train',  price: 80,  duration: '3h' },
        { id: 4, origin: 'Mumbai',    dest: 'Dubai',     type: 'Flight', price: 180, duration: '3h' },
        { id: 5, origin: 'Delhi',     dest: 'Jaipur',    type: 'Bus',    price: 15,  duration: '5h' },
        { id: 6, origin: 'Singapore', dest: 'Bangkok',   type: 'Flight', price: 95,  duration: '2h 30m' }
    ];

    let currentSegId = null;
    let filtered     = mockSegments;

    const listView    = document.getElementById('listView');
    const bookingView = document.getElementById('bookingView');
    const container   = document.getElementById('travelListContainer');
    const bookMsg     = document.getElementById('bookMsg');

    function renderList(segments) {
        container.innerHTML = '';
        if (!segments.length) { container.innerHTML = '<p style="color:#888;">No results found.</p>'; return; }
        segments.forEach(s => {
            const d = document.createElement('div');
            d.className = 'list-item';
            d.innerHTML = `
                <strong>${s.origin} → ${s.dest}</strong>
                <p>Type: ${s.type} &nbsp;|&nbsp; Duration: ${s.duration}</p>
                <p>Price: $${s.price} per seat</p>
                <button onclick="startBook(${s.id})">Book</button>
            `;
            container.appendChild(d);
        });
    }

    window.startBook = function(id) {
        currentSegId = id;
        const s = mockSegments.find(x => x.id === id);
        document.getElementById('bookSegmentLabel').textContent =
            `${s.origin} → ${s.dest} (${s.type}) – $${s.price}/seat`;
        document.getElementById('passengerName').value = user.name;
        bookMsg.textContent = '';
        listView.classList.add('hidden');
        bookingView.classList.remove('hidden');
    };

    document.getElementById('confirmBtn').addEventListener('click', () => {
        const name = document.getElementById('passengerName').value.trim();
        const date = document.getElementById('travelDate').value;
        const seats= document.getElementById('seats').value;
        if (!name || !date) { bookMsg.textContent = 'Please fill all fields.'; bookMsg.className = 'msg-error'; return; }
        bookMsg.textContent = `✓ Booked! Passenger: ${name}, Date: ${date}, Seats: ${seats}`;
        bookMsg.className = 'msg-success';
    });

    document.getElementById('cancelBtn').addEventListener('click', () => {
        bookingView.classList.add('hidden');
        listView.classList.remove('hidden');
    });

    document.getElementById('backBtn').addEventListener('click', () => {
        bookingView.classList.add('hidden');
        listView.classList.remove('hidden');
    });

    // Filter
    document.getElementById('filterBtn').addEventListener('click', () => {
        const origin = document.getElementById('filterOrigin').value.trim().toLowerCase();
        const dest   = document.getElementById('filterDest').value.trim().toLowerCase();
        const type   = document.getElementById('filterType').value;
        filtered = mockSegments.filter(s =>
            (!origin || s.origin.toLowerCase().includes(origin)) &&
            (!dest   || s.dest.toLowerCase().includes(dest)) &&
            (!type   || s.type === type)
        );
        renderList(filtered);
    });

    document.getElementById('clearBtn').addEventListener('click', () => {
        document.getElementById('filterOrigin').value = '';
        document.getElementById('filterDest').value   = '';
        document.getElementById('filterType').value   = '';
        filtered = mockSegments;
        renderList(filtered);
    });

    renderList(mockSegments);
});

