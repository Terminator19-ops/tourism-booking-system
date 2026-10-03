// Uses shared api.js for auth, API calls, and error handling

let allTours = [];

const listView = document.getElementById('listView');
const detailView = document.getElementById('detailView');
const container = document.getElementById('tourListContainer');
const bookMsg = document.getElementById('bookingMsg');

document.addEventListener('DOMContentLoaded', async () => {
    const user = await loadCurrentUser();
    if (!user) return;

    if (!requireRole(['CUSTOMER', 'ADMIN'])) return;

    setupRoleNavigation();

    await loadTours();

    document.getElementById('backBtn').addEventListener('click', () => {
        detailView.classList.add('hidden');
        listView.classList.remove('hidden');
        document.getElementById('bookingForm').classList.add('hidden');
    });

    document.getElementById('cancelBookBtn').addEventListener('click', () => {
        document.getElementById('bookingForm').classList.add('hidden');
    });

    document.getElementById('bookPackageBtn').addEventListener('click', () => {
        document.getElementById('bookingForm').classList.toggle('hidden');
    });

    document.getElementById('confirmBookBtn').addEventListener('click', async () => {
        await bookPackage();
    });
});

async function loadTours() {
    container.innerHTML = '<p style="color:#888;">Loading tour packages...</p>';
    try {
        const tours = await apiFetch('/customer/tour-packages');
        allTours = tours;
        renderList(tours);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load tour packages.')}</p>`;
    }
}

function renderList(tours) {
    container.innerHTML = '';
    if (!tours.length) { 
        container.innerHTML = '<p style="color:#888;">No tour packages found.</p>'; 
        return; 
    }
    tours.forEach(t => {
        const d = document.createElement('div');
        d.className = 'list-item';
        const destCount = t.destinations ? t.destinations.length : 0;
        const actCount = t.activities ? t.activities.length : 0;
        d.innerHTML = `
            <strong>${t.name}</strong>
            <p>${t.description || 'No description'}</p>
            <p style="font-size:0.85rem;color:#555;">${formatCurrency(t.price)} &nbsp;|&nbsp; ${t.duration_days} days &nbsp;|&nbsp; ${destCount} destinations, ${actCount} activities</p>
            <button onclick="openTour(${t.package_id})">View Details</button>
        `;
        container.appendChild(d);
    });
}

window.openTour = function(id) {
    const t = allTours.find(x => x.package_id === id);
    if (!t) return;

    document.getElementById('detailName').textContent = t.name;
    document.getElementById('detailDesc').textContent = t.description || 'No description';
    document.getElementById('detailPrice').textContent = `Price: ${formatCurrency(t.price)} per person`;
    document.getElementById('detailDuration').textContent = `Duration: ${t.duration_days} days`;

    const destList = document.getElementById('destList');
    if (t.destinations && t.destinations.length > 0) {
        destList.innerHTML = t.destinations.map(d => `<li>${d.name} (Day ${d.visit_order}, ${d.days} days)</li>`).join('');
    } else {
        destList.innerHTML = '<li style="color:#888;">No destinations listed.</li>';
    }

    const actList = document.getElementById('actList');
    if (t.activities && t.activities.length > 0) {
        actList.innerHTML = t.activities.map(a => `<li>${a.name} (Day ${a.activity_day})</li>`).join('');
    } else {
        actList.innerHTML = '<li style="color:#888;">No activities listed.</li>';
    }

    document.getElementById('bookingForm').classList.add('hidden');
    bookMsg.textContent = '';
    listView.classList.add('hidden');
    detailView.classList.remove('hidden');
};

async function bookPackage() {
    const date = document.getElementById('tourDate').value;
    const pax = document.getElementById('tourPassengers').value;
    
    if (!date) { 
        showMessage('bookingMsg', 'Please select a travel date.', 'error'); 
        return; 
    }

    // Get the current tour ID from the detail view
    const detailName = document.getElementById('detailName').textContent;
    const tour = allTours.find(t => t.name === detailName);
    if (!tour) {
        showMessage('bookingMsg', 'Please select a tour package first.', 'error');
        return;
    }

    const btn = document.getElementById('confirmBookBtn');
    showLoading(btn, true);
    showMessage('bookingMsg', '', 'success');

    try {
        // First, create a trip for this booking
        console.log('Creating trip...');
        const tripData = await apiFetch('/customer/trips', {
            method: 'POST',
            body: JSON.stringify({
                trip_name: `Package Booking ${new Date().toLocaleDateString()}`,
                start_date: date,
                end_date: date
            })
        });
        console.log('Trip created:', tripData);
        const tripId = tripData.trip_id;

        // Now create the booking with the trip_id
        console.log('Creating booking with trip_id:', tripId);
        const data = await apiFetch('/customer/bookings', {
            method: 'POST',
            body: JSON.stringify({
                booking_type: 'PACKAGE',
                trip_id: tripId,
                package_id: tour.package_id,
                number_of_people: parseInt(pax) || 1,
                travel_date: date
            })
        });

        showMessage('bookingMsg', `✓ Package booked! Booking ID: ${data.booking_id}, Total: ${formatCurrency(data.total_amount)}`, 'success');
        document.getElementById('bookingForm').classList.add('hidden');
        
        if (typeof loadDashboardData === 'function') {
            loadDashboardData();
        }
    } catch (error) {
        console.error('Booking error:', error);
        showMessage('bookingMsg', handleApiError(error, 'Booking failed.'), 'error');
    } finally {
        showLoading(btn, false);
    }
}

