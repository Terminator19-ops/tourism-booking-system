// Uses shared api.js for auth, API calls, and error handling

let allActivities = [];
let currentActId = null;

const listView = document.getElementById('listView');
const bookingView = document.getElementById('bookingView');
const container = document.getElementById('activityListContainer');
const bookMsg = document.getElementById('bookMsg');

document.addEventListener('DOMContentLoaded', async () => {
    const user = await loadCurrentUser();
    if (!user) return;

    if (!requireRole(['CUSTOMER', 'ADMIN'])) return;

    renderNavigation();

    await loadActivities();

    document.getElementById('backBtn').addEventListener('click', () => {
        bookingView.classList.add('hidden');
        listView.classList.remove('hidden');
    });

    document.getElementById('cancelBtn').addEventListener('click', () => {
        bookingView.classList.add('hidden');
        listView.classList.remove('hidden');
    });

    document.getElementById('confirmBtn').addEventListener('click', async () => {
        await bookActivity();
    });

    // Filter
    document.getElementById('filterBtn').addEventListener('click', () => {
        const dest = document.getElementById('filterDest').value.trim().toLowerCase();
        const maxPrice = parseFloat(document.getElementById('filterMaxPrice').value) || Infinity;
        const filtered = allActivities.filter(a =>
            (!dest || (a.destination_name && a.destination_name.toLowerCase().includes(dest))) &&
            (a.price || 0) <= maxPrice
        );
        renderList(filtered);
    });

    document.getElementById('clearBtn').addEventListener('click', () => {
        document.getElementById('filterDest').value = '';
        document.getElementById('filterMaxPrice').value = '';
        renderList(allActivities);
    });
});

async function loadActivities() {
    container.innerHTML = '<p style="color:#888;">Loading activities...</p>';
    try {
        const activities = await apiFetch('/customer/activities');
        allActivities = activities;
        renderList(activities);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load activities.')}</p>`;
    }
}

function renderList(activities) {
    container.innerHTML = '';
    if (!activities.length) { 
        container.innerHTML = '<p style="color:#888;">No activities found.</p>'; 
        return; 
    }
    activities.forEach(a => {
        const d = document.createElement('div');
        d.className = 'list-item';
        const duration = a.duration_hours ? `${a.duration_hours}h` : 'N/A';
        d.innerHTML = `
            <strong>${a.name}</strong>
            <p>Destination: ${a.destination_name || 'N/A'} &nbsp;|&nbsp; Duration: ${duration}</p>
            <p>Price: ${formatCurrency(a.price)} per person</p>
            <button onclick="startBook(${a.activity_id})">Book</button>
        `;
        container.appendChild(d);
    });
}

window.startBook = function(id) {
    currentActId = id;
    const a = allActivities.find(x => x.activity_id === id);
    if (a) {
        document.getElementById('bookActivityLabel').textContent =
            `${a.name} in ${a.destination_name || 'N/A'} – ${formatCurrency(a.price)}/person`;
    }
    bookMsg.textContent = '';
    listView.classList.add('hidden');
    bookingView.classList.remove('hidden');
};

async function bookActivity() {
    const date = document.getElementById('actDate').value;
    const pax = document.getElementById('participants').value;
    
    if (!date) { 
        showMessage('bookMsg', 'Please select a date.', 'error'); 
        return; 
    }
    if (!currentActId) {
        showMessage('bookMsg', 'Please select an activity first.', 'error');
        return;
    }

    const btn = document.getElementById('confirmBtn');
    showLoading(btn, true);
    showMessage('bookMsg', '', 'success');

    try {
        // First, create a trip for this booking
        console.log('Creating trip...');
        const tripData = await apiFetch('/customer/trips', {
            method: 'POST',
            body: JSON.stringify({
                trip_name: `Activity Booking ${new Date().toLocaleDateString()}`,
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
                booking_type: 'ACTIVITY',
                trip_id: tripId,
                activity_id: currentActId,
                activity_date: date,
                number_of_people: parseInt(pax) || 1
            })
        });

        showMessage('bookMsg', `✓ Activity booked! Booking ID: ${data.booking_id}, Total: ${formatCurrency(data.total_amount)}`, 'success');
        
        if (typeof loadDashboardData === 'function') {
            loadDashboardData();
        }
    } catch (error) {
        console.error('Booking error:', error);
        showMessage('bookMsg', handleApiError(error, 'Booking failed.'), 'error');
    } finally {
        showLoading(btn, false);
    }
}

