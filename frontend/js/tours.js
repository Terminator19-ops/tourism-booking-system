document.addEventListener('DOMContentLoaded', () => {
    const user = JSON.parse(localStorage.getItem('user'));
    if (!user) { window.location.href = 'login.html'; return; }

    const mockTours = [
        {
            id: 1, name: 'European Highlights', desc: '10 days across France, Italy and Switzerland.',
            price: 2500, duration: '10 days',
            destinations: ['Paris', 'Rome', 'Zurich'],
            activities: ['Eiffel Tower Tour', 'Colosseum Visit', 'Swiss Alps Hike']
        },
        {
            id: 2, name: 'Asian Adventure', desc: '14 days exploring East Asia.',
            price: 3200, duration: '14 days',
            destinations: ['Beijing', 'Tokyo'],
            activities: ['Great Wall Trek', 'Mount Fuji Day Trip', 'Tokyo Street Food Tour']
        },
        {
            id: 3, name: 'India Heritage', desc: '7 days through Rajasthan & Agra.',
            price: 1100, duration: '7 days',
            destinations: ['Jaipur', 'Agra', 'Delhi'],
            activities: ['Taj Mahal Visit', 'Amber Fort Tour', 'Camel Safari']
        }
    ];

    const listView   = document.getElementById('listView');
    const detailView = document.getElementById('detailView');
    const container  = document.getElementById('tourListContainer');
    const bookMsg    = document.getElementById('bookingMsg');

    function renderList() {
        container.innerHTML = '';
        mockTours.forEach(t => {
            const d = document.createElement('div');
            d.className = 'list-item';
            d.innerHTML = `
                <strong>${t.name}</strong>
                <p>${t.desc}</p>
                <p style="font-size:0.85rem;color:#555;">$${t.price} &nbsp;|&nbsp; ${t.duration}</p>
                <button onclick="openTour(${t.id})">View Details</button>
            `;
            container.appendChild(d);
        });
    }

    window.openTour = function(id) {
        const t = mockTours.find(x => x.id === id);
        if (!t) return;

        document.getElementById('detailName').textContent     = t.name;
        document.getElementById('detailDesc').textContent     = t.desc;
        document.getElementById('detailPrice').textContent    = `Price: $${t.price} per person`;
        document.getElementById('detailDuration').textContent = `Duration: ${t.duration}`;

        document.getElementById('destList').innerHTML = t.destinations.map(d => `<li>${d}</li>`).join('');
        document.getElementById('actList').innerHTML  = t.activities.map(a => `<li>${a}</li>`).join('');

        document.getElementById('bookingForm').classList.add('hidden');
        bookMsg.textContent = '';
        listView.classList.add('hidden');
        detailView.classList.remove('hidden');
    };

    document.getElementById('bookPackageBtn').addEventListener('click', () => {
        document.getElementById('bookingForm').classList.toggle('hidden');
    });

    document.getElementById('confirmBookBtn').addEventListener('click', () => {
        const date = document.getElementById('tourDate').value;
        const pax  = document.getElementById('tourPassengers').value;
        if (!date) { bookMsg.textContent = 'Please select a travel date.'; bookMsg.className = 'msg-error'; return; }
        bookMsg.textContent = `✓ Tour booked! Travel date: ${date}, Passengers: ${pax}`;
        bookMsg.className = 'msg-success';
        document.getElementById('bookingForm').classList.add('hidden');
    });

    document.getElementById('cancelBookBtn').addEventListener('click', () => {
        document.getElementById('bookingForm').classList.add('hidden');
    });

    document.getElementById('backBtn').addEventListener('click', () => {
        detailView.classList.add('hidden');
        listView.classList.remove('hidden');
    });

    renderList();
});

