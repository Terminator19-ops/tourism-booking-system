document.addEventListener('DOMContentLoaded', () => {
    const user = JSON.parse(localStorage.getItem('user'));
    if (!user) { window.location.href = 'login.html'; return; }

    const mockActivities = [
        { id: 1, name: 'Louvre Museum Tour',    dest: 'Paris',     duration: '3h',   price: 25 },
        { id: 2, name: 'Scuba Diving',           dest: 'Miami',     duration: '4h',   price: 110 },
        { id: 3, name: 'Colosseum Guided Tour',  dest: 'Rome',      duration: '2h',   price: 30 },
        { id: 4, name: 'Mount Fuji Day Trip',    dest: 'Tokyo',     duration: '8h',   price: 150 },
        { id: 5, name: 'Camel Safari',           dest: 'Jaipur',    duration: '3h',   price: 40 },
        { id: 6, name: 'Bungee Jumping',         dest: 'Queenstown',duration: '2h',   price: 200 }
    ];

    let filteredActivities = mockActivities;
    let currentActId = null;

    const listView    = document.getElementById('listView');
    const bookingView = document.getElementById('bookingView');
    const container   = document.getElementById('activityListContainer');
    const bookMsg     = document.getElementById('bookMsg');

    function renderList(acts) {
        container.innerHTML = '';
        if (!acts.length) { container.innerHTML = '<p style="color:#888;">No activities found.</p>'; return; }
        acts.forEach(a => {
            const d = document.createElement('div');
            d.className = 'list-item';
            d.innerHTML = `
                <strong>${a.name}</strong>
                <p>Destination: ${a.dest} &nbsp;|&nbsp; Duration: ${a.duration}</p>
                <p>Price: $${a.price} per person</p>
                <button onclick="startBook(${a.id})">Book</button>
            `;
            container.appendChild(d);
        });
    }

    window.startBook = function(id) {
        currentActId = id;
        const a = mockActivities.find(x => x.id === id);
        document.getElementById('bookActivityLabel').textContent =
            `${a.name} in ${a.dest} – $${a.price}/person`;
        bookMsg.textContent = '';
        listView.classList.add('hidden');
        bookingView.classList.remove('hidden');
    };

    document.getElementById('confirmBtn').addEventListener('click', () => {
        const date = document.getElementById('actDate').value;
        const pax  = document.getElementById('participants').value;
        if (!date) { bookMsg.textContent = 'Please select a date.'; bookMsg.className = 'msg-error'; return; }
        bookMsg.textContent = `✓ Booked! Date: ${date}, Participants: ${pax}`;
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
        const dest     = document.getElementById('filterDest').value.trim().toLowerCase();
        const maxPrice = parseFloat(document.getElementById('filterMaxPrice').value) || Infinity;
        filteredActivities = mockActivities.filter(a =>
            (!dest || a.dest.toLowerCase().includes(dest)) &&
            a.price <= maxPrice
        );
        renderList(filteredActivities);
    });

    document.getElementById('clearBtn').addEventListener('click', () => {
        document.getElementById('filterDest').value     = '';
        document.getElementById('filterMaxPrice').value = '';
        filteredActivities = mockActivities;
        renderList(filteredActivities);
    });

    renderList(mockActivities);
});

