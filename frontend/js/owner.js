// Uses shared api.js for auth, API calls, and error handling

let currentHotelId = null;

document.addEventListener('DOMContentLoaded', async () => {
    const user = await loadCurrentUser();
    if (!user) return;

    if (!requireRole(['OWNER', 'ADMIN'])) return;

    setupRoleNavigation();

    document.getElementById('welcomeMessage').textContent = `Owner Dashboard - ${user.first_name} ${user.last_name}`;

    await loadDestinationsForSelect();
    await loadHotels();
    await loadBookings();
    await loadTrips();

    // Create hotel
    document.getElementById('createHotelBtn').addEventListener('click', () => {
        document.getElementById('createHotelForm').classList.remove('hidden');
        document.getElementById('createHotelMsg').textContent = '';
    });
    document.getElementById('cancelHotelBtn').addEventListener('click', () => {
        document.getElementById('createHotelForm').classList.add('hidden');
    });
    document.getElementById('saveHotelBtn').addEventListener('click', async () => {
        await createHotel();
    });

    // Back to hotels
    document.getElementById('backToHotelsBtn').addEventListener('click', () => {
        document.getElementById('hotelDetailSection').classList.add('hidden');
        document.getElementById('hotelsSection').classList.remove('hidden');
        currentHotelId = null;
    });

    // Create room
    document.getElementById('createRoomBtn').addEventListener('click', () => {
        document.getElementById('createRoomForm').classList.remove('hidden');
        document.getElementById('createRoomMsg').textContent = '';
    });
    document.getElementById('cancelRoomBtn').addEventListener('click', () => {
        document.getElementById('createRoomForm').classList.add('hidden');
    });
    document.getElementById('saveRoomBtn').addEventListener('click', async () => {
        await createRoom();
    });

    // Hotel actions
    document.getElementById('updateHotelBtn').addEventListener('click', async () => {
        await updateHotel();
    });
    document.getElementById('deactivateHotelBtn').addEventListener('click', async () => {
        await deactivateHotel();
    });

    document.getElementById('logoutBtn').addEventListener('click', async () => {
        await logout();
    });
});

async function loadDestinationsForSelect() {
    try {
        // Get destinations from hotels endpoint which includes destination info
        const hotels = await apiFetch('/customer/hotels');
        const destinations = [...new Map(hotels.map(h => [h.destination_id, {id: h.destination_id, name: h.destination_name, city: h.city, country: h.country}])).values()];
        
        const select = document.getElementById('hotelDestinationId');
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
    }
}

async function loadHotels() {
    const container = document.getElementById('hotelsList');
    container.innerHTML = '<p style="color:#888;">Loading hotels...</p>';
    try {
        const hotels = await apiFetch('/owner/hotels');
        renderHotels(hotels);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load hotels.')}</p>`;
    }
}

function renderHotels(hotels) {
    const container = document.getElementById('hotelsList');
    container.innerHTML = '';
    if (!hotels.length) { 
        container.innerHTML = '<p style="color:#888;">No hotels yet. Create one!</p>'; 
        return; 
    }
    hotels.forEach(h => {
        const d = document.createElement('div');
        d.className = 'list-item';
        d.innerHTML = `
            <strong>${h.name}</strong>
            <p>${h.address} | ${h.destination_name || 'N/A'} | ${'★'.repeat(h.star_rating || 0)} (${h.star_rating || 0})</p>
            <p style="font-size:0.8rem;color:#888;">Status: ${h.status} | Rooms: ${h.room_count || 0}</p>
            <button onclick="openHotelDetail(${h.hotel_id})">Manage</button>
        `;
        container.appendChild(d);
    });
}

window.openHotelDetail = async function(hotelId) {
    currentHotelId = hotelId;
    document.getElementById('hotelsSection').classList.add('hidden');
    document.getElementById('hotelDetailSection').classList.remove('hidden');
    
    try {
        const hotel = await apiFetch(`/owner/hotels/${hotelId}`);
        
        document.getElementById('hotelDetailName').textContent = hotel.name;
        document.getElementById('hotelDetailAddress').textContent = hotel.address;
        document.getElementById('hotelDetailStatus').textContent = `Status: ${hotel.status} | ${hotel.destination_name || 'N/A'} | ${'★'.repeat(hotel.star_rating || 0)}`;
        
        await loadRooms(hotelId);
    } catch (error) {
        showMessage('hotelActionMsg', handleApiError(error, 'Failed to load hotel details.'), 'error');
    }
};

async function loadRooms(hotelId) {
    const container = document.getElementById('roomsList');
    container.innerHTML = '<p style="color:#888;">Loading rooms...</p>';
    try {
        const rooms = await apiFetch(`/owner/hotels/${hotelId}/rooms`);
        renderRooms(rooms);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load rooms.')}</p>`;
    }
}

function renderRooms(rooms) {
    const container = document.getElementById('roomsList');
    container.innerHTML = '';
    if (!rooms.length) { 
        container.innerHTML = '<p style="color:#888;">No rooms yet. Add one!</p>'; 
        return; 
    }
    rooms.forEach(r => {
        const d = document.createElement('div');
        d.className = 'list-item';
        d.innerHTML = `
            <strong>Room ${r.room_number} - ${r.room_type}</strong>
            <p>Capacity: ${r.capacity} | ${formatCurrency(r.price_per_night)}/night | Status: ${r.status}</p>
            <button onclick="editRoom(${r.room_id})">Edit</button>
            <button class="danger" onclick="deactivateRoom(${r.room_id})">Deactivate</button>
        `;
        container.appendChild(d);
    });
}

async function createHotel() {
    const name = document.getElementById('hotelName').value.trim();
    const destinationId = document.getElementById('hotelDestinationId').value;
    const address = document.getElementById('hotelAddress').value.trim();
    const description = document.getElementById('hotelDescription').value.trim();
    const contactNumber = document.getElementById('hotelContact').value.trim();
    const email = document.getElementById('hotelEmail').value.trim();
    const starRating = parseFloat(document.getElementById('hotelStarRating').value) || 4.5;
    
    if (!name || !destinationId || !address) {
        showMessage('createHotelMsg', 'Name, destination, and address are required.', 'error');
        return;
    }

    const btn = document.getElementById('saveHotelBtn');
    showLoading(btn, true);
    showMessage('createHotelMsg', '', 'success');

    try {
        const data = await apiFetch('/owner/hotels', {
            method: 'POST',
            body: JSON.stringify({
                name,
                destination_id: parseInt(destinationId),
                address,
                description,
                contact_number: contactNumber,
                email,
                star_rating: starRating,
                status: 'ACTIVE'
            })
        });

        showMessage('createHotelMsg', `Hotel created! ID: ${data.hotel_id}`, 'success');
        document.getElementById('createHotelForm').classList.add('hidden');
        document.getElementById('hotelName').value = '';
        document.getElementById('hotelDestinationId').value = '';
        document.getElementById('hotelAddress').value = '';
        document.getElementById('hotelDescription').value = '';
        document.getElementById('hotelContact').value = '';
        document.getElementById('hotelEmail').value = '';
        document.getElementById('hotelStarRating').value = '4.5';
        await loadHotels();
    } catch (error) {
        showMessage('createHotelMsg', handleApiError(error, 'Failed to create hotel.'), 'error');
    } finally {
        showLoading(btn, false);
    }
}

async function createRoom() {
    if (!currentHotelId) return;
    
    const roomNumber = document.getElementById('roomNumber').value.trim();
    const roomType = document.getElementById('roomType').value.trim();
    const capacity = parseInt(document.getElementById('roomCapacity').value) || 1;
    const pricePerNight = parseFloat(document.getElementById('roomPrice').value) || 0;
    const status = document.getElementById('roomStatus').value;
    
    if (!roomNumber || !roomType) {
        showMessage('createRoomMsg', 'Room number and type are required.', 'error');
        return;
    }

    const btn = document.getElementById('saveRoomBtn');
    showLoading(btn, true);
    showMessage('createRoomMsg', '', 'success');

    try {
        const data = await apiFetch(`/owner/hotels/${currentHotelId}/rooms`, {
            method: 'POST',
            body: JSON.stringify({
                room_number: roomNumber,
                room_type: roomType,
                capacity: capacity,
                price_per_night: pricePerNight,
                status: status
            })
        });

        showMessage('createRoomMsg', `Room created! ID: ${data.room_id}`, 'success');
        document.getElementById('createRoomForm').classList.add('hidden');
        document.getElementById('roomNumber').value = '';
        document.getElementById('roomType').value = '';
        document.getElementById('roomCapacity').value = '2';
        document.getElementById('roomPrice').value = '100';
        document.getElementById('roomStatus').value = 'AVAILABLE';
        await loadRooms(currentHotelId);
    } catch (error) {
        showMessage('createRoomMsg', handleApiError(error, 'Failed to create room.'), 'error');
    } finally {
        showLoading(btn, false);
    }
}

async function updateHotel() {
    if (!currentHotelId) return;
    
    // For simplicity, we'll just allow updating basic fields
    // In a real app, you'd have a form
    const name = prompt('New hotel name (leave blank to keep current):');
    if (name === null) return; // User cancelled
    
    const btn = document.getElementById('updateHotelBtn');
    showLoading(btn, true);
    showMessage('hotelActionMsg', '', 'success');

    try {
        const payload = {};
        if (name.trim()) payload.name = name.trim();
        
        if (Object.keys(payload).length === 0) {
            showMessage('hotelActionMsg', 'No changes provided.', 'error');
            return;
        }

        await apiFetch(`/owner/hotels/${currentHotelId}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        });

        showMessage('hotelActionMsg', 'Hotel updated successfully!', 'success');
        await loadRooms(currentHotelId); // Reload to get updated hotel info
    } catch (error) {
        showMessage('hotelActionMsg', handleApiError(error, 'Failed to update hotel.'), 'error');
    } finally {
        showLoading(btn, false);
    }
}

async function deactivateHotel() {
    if (!currentHotelId) return;
    
    if (!confirm('Are you sure you want to deactivate this hotel? This will also deactivate all its rooms.')) {
        return;
    }

    const btn = document.getElementById('deactivateHotelBtn');
    showLoading(btn, true);
    showMessage('hotelActionMsg', '', 'success');

    try {
        await apiFetch(`/owner/hotels/${currentHotelId}`, {
            method: 'DELETE'
        });

        showMessage('hotelActionMsg', 'Hotel deactivated successfully!', 'success');
        document.getElementById('hotelDetailSection').classList.add('hidden');
        document.getElementById('hotelsSection').classList.remove('hidden');
        currentHotelId = null;
        await loadHotels();
    } catch (error) {
        showMessage('hotelActionMsg', handleApiError(error, 'Failed to deactivate hotel.'), 'error');
    } finally {
        showLoading(btn, false);
    }
}

async function loadBookings() {
    const container = document.getElementById('bookingsList');
    container.innerHTML = '<p style="color:#888;">Loading bookings...</p>';
    try {
        const bookings = await apiFetch('/owner/bookings');
        renderOwnerBookings(bookings);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load bookings.')}</p>`;
    }
}

function renderOwnerBookings(bookings) {
    const container = document.getElementById('bookingsList');
    container.innerHTML = '';
    if (!bookings.length) { 
        container.innerHTML = '<p style="color:#888;">No bookings for your hotels.</p>'; 
        return; 
    }
    bookings.forEach(b => {
        const d = document.createElement('div');
        d.className = 'list-item';
        d.innerHTML = `
            <strong>Booking #${b.booking_id} (${b.booking_type})</strong>
            <p>Customer: ${b.customer_name} (${b.customer_email})</p>
            <p>Hotel: ${b.hotel_name} | Room: ${b.room_number || 'N/A'}</p>
            <p>${formatDate(b.check_in_date)} → ${formatDate(b.check_out_date)} | ${formatCurrency(b.total_amount)} | Status: ${b.status}</p>
        `;
        container.appendChild(d);
    });
}

async function loadTrips() {
    const container = document.getElementById('tripsList');
    container.innerHTML = '<p style="color:#888;">Loading trips...</p>';
    try {
        const trips = await apiFetch('/owner/trips');
        renderOwnerTrips(trips);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load trips.')}</p>`;
    }
}

function renderOwnerTrips(trips) {
    const container = document.getElementById('tripsList');
    container.innerHTML = '';
    if (!trips.length) { 
        container.innerHTML = '<p style="color:#888;">No customer trips for your hotels.</p>'; 
        return; 
    }
    trips.forEach(t => {
        const d = document.createElement('div');
        d.className = 'list-item';
        const bookingsHtml = t.bookings && t.bookings.length > 0 
            ? t.bookings.map(b => `<div style="margin-left:20px;font-size:0.85rem;">${b.booking_type}: ${b.hotel_name} - Room ${b.room_number} (${formatDate(b.check_in_date)} → ${formatDate(b.check_out_date)})</div>`).join('')
            : '<div style="margin-left:20px;font-size:0.85rem;color:#888;">No bookings</div>';
        d.innerHTML = `
            <strong>${t.trip_name} (Customer: ${t.customer_name})</strong>
            <p>${formatDate(t.start_date)} → ${formatDate(t.end_date)} | Status: ${t.status}</p>
            <p style="font-size:0.85rem;color:#888;">Customer: ${t.customer_email}</p>
            <div style="margin-top:8px;"><strong>Bookings:</strong>${bookingsHtml}</div>
        `;
        container.appendChild(d);
    });
}