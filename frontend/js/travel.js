// Uses shared api.js for auth, API calls, and error handling

let allSegments = [];
let currentSegId = null;

const listView = document.getElementById('listView');
const bookingView = document.getElementById('bookingView');
const container = document.getElementById('travelListContainer');
const bookMsg = document.getElementById('bookMsg');

document.addEventListener('DOMContentLoaded', async () => {
    const user = await loadCurrentUser();
    if (!user) return;

    if (!requireRole(['CUSTOMER', 'ADMIN'])) return;

    renderNavigation();

    await loadTravelSegments();

    document.getElementById('backBtn').addEventListener('click', () => {
        bookingView.classList.add('hidden');
        listView.classList.remove('hidden');
    });

    document.getElementById('cancelBtn').addEventListener('click', () => {
        bookingView.classList.add('hidden');
        listView.classList.remove('hidden');
    });

    document.getElementById('confirmBtn').addEventListener('click', async () => {
        await bookTravel();
    });

    // Filter
    document.getElementById('filterBtn').addEventListener('click', () => {
        const origin = document.getElementById('filterOrigin').value.trim().toLowerCase();
        const dest = document.getElementById('filterDest').value.trim().toLowerCase();
        const type = document.getElementById('filterType').value;
        const filtered = allSegments.filter(s =>
            (!origin || (s.origin_name && s.origin_name.toLowerCase().includes(origin))) &&
            (!dest || (s.destination_name && s.destination_name.toLowerCase().includes(dest))) &&
            (!type || s.transport_type === type)
        );
        renderList(filtered);
    });

    document.getElementById('clearBtn').addEventListener('click', () => {
        document.getElementById('filterOrigin').value = '';
        document.getElementById('filterDest').value = '';
        document.getElementById('filterType').value = '';
        renderList(allSegments);
    });
});

async function loadTravelSegments() {
    container.innerHTML = '<p style="color:#888;">Loading travel options...</p>';
    try {
        const segments = await apiFetch('/customer/travel');
        allSegments = segments;
        renderList(segments);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load travel options.')}</p>`;
    }
}

function renderList(segments) {
    container.innerHTML = '';
    if (!segments.length) { 
        container.innerHTML = '<p style="color:#888;">No travel options found.</p>'; 
        return; 
    }
    segments.forEach(s => {
        const d = document.createElement('div');
        d.className = 'list-item';
        const departure = s.departure_time ? formatDateTime(s.departure_time) : 'N/A';
        const arrival = s.arrival_time ? formatDateTime(s.arrival_time) : 'N/A';
        d.innerHTML = `
            <strong>${s.origin_name || 'N/A'} → ${s.destination_name || 'N/A'}</strong>
            <p>Type: ${s.transport_type} &nbsp;|&nbsp; Operator: ${s.operator_name || 'N/A'}</p>
            <p>Departure: ${departure} &nbsp;|&nbsp; Arrival: ${arrival}</p>
            <p>Price: ${formatCurrency(s.price)} per seat &nbsp;|&nbsp; Capacity: ${s.capacity}</p>
            <button onclick="startBook(${s.travel_segment_id})">Book</button>
        `;
        container.appendChild(d);
    });
}

window.startBook = function(id) {
    currentSegId = id;
    const s = allSegments.find(x => x.travel_segment_id === id);
    if (s) {
        document.getElementById('bookSegmentLabel').textContent =
            `${s.origin_name || 'N/A'} → ${s.destination_name || 'N/A'} (${s.transport_type}) – ${formatCurrency(s.price)}/seat`;
    }
    bookMsg.textContent = '';
    listView.classList.add('hidden');
    bookingView.classList.remove('hidden');
};

async function bookTravel() {
    const name = document.getElementById('passengerName').value.trim();
    const date = document.getElementById('travelDate').value;
    const seats = document.getElementById('seats').value;
    
    if (!name || !date) { 
        showMessage('bookMsg', 'Please fill all fields.', 'error'); 
        return; 
    }
    if (!currentSegId) {
        showMessage('bookMsg', 'Please select a travel segment first.', 'error');
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
                trip_name: `Travel Booking ${new Date().toLocaleDateString()}`,
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
                booking_type: 'TRAVEL',
                trip_id: tripId,
                travel_segment_id: currentSegId,
                number_of_passengers: parseInt(seats) || 1
            })
        });

        showMessage('bookMsg', `✓ Travel booked! Booking ID: ${data.booking_id}, Total: ${formatCurrency(data.total_amount)}`, 'success');
        
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

