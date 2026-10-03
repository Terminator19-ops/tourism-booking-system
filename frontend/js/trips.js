// Uses shared api.js for auth, API calls, and error handling

let currentTripId = null;

const listView = document.getElementById('listView');
const detailView = document.getElementById('detailView');
const tripListContainer = document.getElementById('tripListContainer');
const createTripForm = document.getElementById('createTripForm');
const createTripMsg = document.getElementById('createTripMsg');

document.addEventListener('DOMContentLoaded', async () => {
    const user = await loadCurrentUser();
    if (!user) return;

    if (!requireRole(['CUSTOMER', 'ADMIN'])) return;

    setupRoleNavigation();

    await loadTrips();

    // Create trip
    document.getElementById('createTripBtn').addEventListener('click', () => {
        createTripForm.classList.toggle('hidden');
        createTripMsg.textContent = '';
    });
    document.getElementById('cancelTripBtn').addEventListener('click', () => {
        createTripForm.classList.add('hidden');
    });
    document.getElementById('saveTripBtn').addEventListener('click', async () => {
        await createTrip();
    });

    // Back to list
    document.getElementById('backToListBtn').addEventListener('click', () => {
        detailView.classList.add('hidden');
        listView.classList.remove('hidden');
        currentTripId = null;
    });

    // Add destination
    document.getElementById('addDestBtn').addEventListener('click', async () => {
        document.getElementById('addDestForm').classList.toggle('hidden');
        if (!document.getElementById('addDestForm').classList.contains('hidden')) {
            await loadDestinationsForSelect();
        }
    });
    document.getElementById('cancelDestBtn').addEventListener('click', () => {
        document.getElementById('addDestForm').classList.add('hidden');
    });
    document.getElementById('saveDestBtn').addEventListener('click', async () => {
        await addTripDestination();
    });

    // Review
    document.getElementById('addReviewBtn').addEventListener('click', () => {
        document.getElementById('reviewForm').classList.toggle('hidden');
    });
    document.getElementById('cancelReviewBtn').addEventListener('click', () => {
        document.getElementById('reviewForm').classList.add('hidden');
    });
    document.getElementById('saveReviewBtn').addEventListener('click', async () => {
        await submitReview();
    });
});

async function loadTrips() {
    tripListContainer.innerHTML = '<p style="color:#888;">Loading trips...</p>';
    try {
        const trips = await apiFetch('/customer/trips');
        renderTripList(trips);
    } catch (error) {
        tripListContainer.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load trips.')}</p>`;
    }
}

function renderTripList(trips) {
    tripListContainer.innerHTML = '';
    if (!trips.length) {
        tripListContainer.innerHTML = '<p style="color:#888;">No trips yet. Create one!</p>';
        return;
    }
    trips.forEach(t => {
        const d = document.createElement('div');
        d.className = 'list-item';
        d.innerHTML = `
            <strong>${t.trip_name}</strong>
            <p>${formatDate(t.start_date)} → ${formatDate(t.end_date)}</p>
            <p style="font-size:0.8rem;color:#888;">Status: ${t.status}</p>
            <button onclick="openDetail(${t.trip_id})">View Details</button>
        `;
        tripListContainer.appendChild(d);
    });
}

async function createTrip() {
    const name = document.getElementById('tripNameInput').value.trim();
    const desc = document.getElementById('tripDescInput').value.trim();
    const start = document.getElementById('tripStartInput').value;
    const end = document.getElementById('tripEndInput').value;

    if (!name) { 
        showMessage('createTripMsg', 'Trip name required.', 'error'); 
        return; 
    }
    if (!start || !end) {
        showMessage('createTripMsg', 'Start and end dates are required.', 'error');
        return;
    }
    if (end < start) {
        showMessage('createTripMsg', 'End date must be after start date.', 'error');
        return;
    }

    const btn = document.getElementById('saveTripBtn');
    showLoading(btn, true);
    showMessage('createTripMsg', '', 'success');

    try {
        const data = await apiFetch('/customer/trips', {
            method: 'POST',
            body: JSON.stringify({
                trip_name: name,
                start_date: start,
                end_date: end
            })
        });

        showMessage('createTripMsg', `Trip created! ID: ${data.trip_id}`, 'success');
        document.getElementById('tripNameInput').value = '';
        document.getElementById('tripDescInput').value = '';
        document.getElementById('tripStartInput').value = '';
        document.getElementById('tripEndInput').value = '';
        createTripForm.classList.add('hidden');
        await loadTrips();
        
        if (typeof loadDashboardData === 'function') {
            loadDashboardData();
        }
    } catch (error) {
        showMessage('createTripMsg', handleApiError(error, 'Failed to create trip.'), 'error');
    } finally {
        showLoading(btn, false);
    }
}

window.openDetail = async function(id) {
    currentTripId = id;
    
    try {
        const trip = await apiFetch(`/customer/trips/${id}`);
        
        document.getElementById('detailTripName').textContent = trip.trip_name;
        document.getElementById('detailTripDesc').textContent = 'Trip details';
        document.getElementById('detailTripDates').textContent = `${formatDate(trip.start_date)} → ${formatDate(trip.end_date)} (Status: ${trip.status})`;

        // Destinations
        renderDestinations(trip.destinations || []);
        // Bookings
        renderBookings(trip.bookings || []);
        // Review
        renderReview(trip);

        listView.classList.add('hidden');
        detailView.classList.remove('hidden');
        
        // Reset forms
        document.getElementById('addDestForm').classList.add('hidden');
        document.getElementById('reviewForm').classList.add('hidden');
        document.getElementById('destNameInput').value = '';
        document.getElementById('destVisitOrder').value = '';
        document.getElementById('destArrivalDate').value = '';
        document.getElementById('destDepartureDate').value = '';
    } catch (error) {
        showMessage('bookingMsg', handleApiError(error, 'Failed to load trip details.'), 'error');
    }
};

function renderDestinations(destinations) {
    const ul = document.getElementById('destList');
    if (!destinations.length) {
        ul.innerHTML = '<li style="color:#888;">No destinations added.</li>';
        return;
    }
    ul.innerHTML = destinations.map(d => 
        `<li>${d.name} (Day ${d.visit_order}, ${formatDate(d.arrival_date)} → ${formatDate(d.departure_date)})</li>`
    ).join('');
}

function renderBookings(bookings) {
    const div = document.getElementById('bookingList');
    if (!bookings.length) {
        div.innerHTML = '<p style="color:#888;">No bookings yet.</p>';
        return;
    }
    div.innerHTML = bookings.map(b => {
        let detail = '';
        if (b.booking_type === 'HOTEL') {
            detail = `${b.hotel_name || 'Hotel'} - Room ${b.room_number || ''} (${formatDate(b.check_in_date)} → ${formatDate(b.check_out_date)}, ${b.number_of_guests} guests)`;
        } else if (b.booking_type === 'PACKAGE') {
            detail = `${b.package_name || 'Package'} (${formatDate(b.travel_date)}, ${b.number_of_people} people)`;
        } else if (b.booking_type === 'ACTIVITY') {
            detail = `${b.activity_name || 'Activity'} (${formatDate(b.activity_date)}, ${b.act_people || b.number_of_people} people)`;
        } else if (b.booking_type === 'TRAVEL') {
            detail = `${b.transport_type || 'Travel'} ${b.origin || ''} → ${b.destination || ''} (${formatDateTime(b.departure_time)}, ${b.number_of_passengers} passengers)`;
        }
        return `
            <div class="list-item">
                <strong>${b.booking_type} Booking</strong>
                <p>${detail}</p>
                <p style="font-size:0.8rem;color:#888;">${formatCurrency(b.total_amount)} | Status: ${b.status} | Booking ID: ${b.booking_id}</p>
            </div>
        `;
    }).join('');
}

function renderReview(trip) {
    const div = document.getElementById('reviewDisplay');
    // Check if trip has a review (would need a separate API call or be included in trip details)
    // For now, show a placeholder
    div.innerHTML = '<p style="color:#888;">No review yet. Click "Write Review" to add one.</p>';
}

async function addTripDestination() {
    if (!currentTripId) return;
    
    const destinationId = document.getElementById('destSelect').value;
    const visitOrder = document.getElementById('destVisitOrder').value;
    const arrivalDate = document.getElementById('destArrivalDate').value;
    const departureDate = document.getElementById('destDepartureDate').value;
    
    if (!destinationId || !visitOrder || !arrivalDate || !departureDate) {
        showMessage('bookingMsg', 'All fields are required.', 'error');
        return;
    }
    if (departureDate < arrivalDate) {
        showMessage('bookingMsg', 'Departure date must be after arrival date.', 'error');
        return;
    }

    const btn = document.getElementById('saveDestBtn');
    showLoading(btn, true);
    showMessage('bookingMsg', '', 'success');

    try {
        await apiFetch(`/customer/trips/${currentTripId}/destinations`, {
            method: 'POST',
            body: JSON.stringify({
                destination_id: parseInt(destinationId),
                visit_order: parseInt(visitOrder),
                arrival_date: arrivalDate,
                departure_date: departureDate
            })
        });

        showMessage('bookingMsg', 'Destination added to trip successfully!', 'success');
        document.getElementById('addDestForm').classList.add('hidden');
        document.getElementById('destSelect').value = '';
        document.getElementById('destVisitOrder').value = '1';
        document.getElementById('destArrivalDate').value = '';
        document.getElementById('destDepartureDate').value = '';
        
        // Reload trip to show new destination
        const trip = await apiFetch(`/customer/trips/${currentTripId}`);
        renderDestinations(trip.destinations || []);
    } catch (error) {
        showMessage('bookingMsg', handleApiError(error, 'Failed to add destination.'), 'error');
    } finally {
        showLoading(btn, false);
    }
}

async function loadDestinationsForSelect() {
    try {
        // We need to fetch destinations - there's no direct customer endpoint for this
        // But we can use the admin endpoint or we need to add one
        // For now, let's try to get destinations from the hotel list which includes destination info
        const hotels = await apiFetch('/customer/hotels');
        const destinations = [...new Map(hotels.map(h => [h.destination_id, {id: h.destination_id, name: h.destination_name, city: h.city, country: h.country}])).values()];
        
        const select = document.getElementById('destSelect');
        select.innerHTML = '<option value="">Select destination</option>';
        destinations.forEach(d => {
            if (d.name) {
                const option = document.createElement('option');
                option.value = d.id;
                option.textContent = `${d.name}${d.city ? ', ' + d.city : ''}${d.country ? ', ' + d.country : ''}`;
                select.appendChild(option);
            }
        });
    } catch (error) {
        console.error('Failed to load destinations:', error);
        const select = document.getElementById('destSelect');
        select.innerHTML = '<option value="">Failed to load destinations</option>';
    }
}

async function submitReview() {
    if (!currentTripId) return;
    
    const rating = parseInt(document.getElementById('reviewRating').value) || 0;
    const comment = document.getElementById('reviewComment').value.trim();
    
    if (rating < 1 || rating > 5) { 
        showMessage('reviewDisplay', 'Rating must be 1–5.', 'error'); 
        return; 
    }

    const btn = document.getElementById('saveReviewBtn');
    showLoading(btn, true);
    showMessage('reviewDisplay', '', 'success');

    try {
        await apiFetch('/customer/reviews', {
            method: 'POST',
            body: JSON.stringify({
                trip_id: currentTripId,
                rating: rating,
                comment: comment
            })
        });

        showMessage('reviewDisplay', 'Review submitted successfully!', 'success');
        document.getElementById('reviewForm').classList.add('hidden');
        document.getElementById('reviewRating').value = '';
        document.getElementById('reviewComment').value = '';
        
        // Reload trip to show review
        const trip = await apiFetch(`/customer/trips/${currentTripId}`);
        renderReview(trip);
    } catch (error) {
        showMessage('reviewDisplay', handleApiError(error, 'Failed to submit review.'), 'error');
    } finally {
        showLoading(btn, false);
    }
}

