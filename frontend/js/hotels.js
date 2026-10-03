// Uses shared api.js for auth, API calls, and error handling

let currentHotelId = null;
let currentRoomId = null;
let allHotels = [];

const listView = document.getElementById('listView');
const detailView = document.getElementById('detailView');
const containerEl = document.getElementById('hotelListContainer');
const bookSection = document.getElementById('bookingSection');
const bookingMsg = document.getElementById('bookingMsg');

document.addEventListener('DOMContentLoaded', async () => {
    const user = await loadCurrentUser();
    if (!user) return;

    if (!requireRole(['CUSTOMER', 'ADMIN'])) return;

    setupRoleNavigation();

    await loadHotels();

    // Search
    document.getElementById('searchBtn').addEventListener('click', () => {
        const q = document.getElementById('searchInput').value.trim().toLowerCase();
        const filtered = q
            ? allHotels.filter(h => h.name.toLowerCase().includes(q) || 
                (h.city && h.city.toLowerCase().includes(q)) ||
                (h.country && h.country.toLowerCase().includes(q)))
            : allHotels;
        renderList(filtered);
    });

    document.getElementById('clearBtn').addEventListener('click', () => {
        document.getElementById('searchInput').value = '';
        renderList(allHotels);
    });

    document.getElementById('backBtn').addEventListener('click', () => {
        detailView.classList.add('hidden');
        listView.classList.remove('hidden');
        bookSection.classList.add('hidden');
    });

    document.getElementById('cancelBookBtn').addEventListener('click', () => {
        bookSection.classList.add('hidden');
    });

    document.getElementById('confirmBookBtn').addEventListener('click', async () => {
        await bookRoom();
    });
});

async function loadHotels() {
    containerEl.innerHTML = '<p style="color:#888;">Loading hotels...</p>';
    try {
        const hotels = await apiFetch('/customer/hotels');
        allHotels = hotels;
        renderList(hotels);
    } catch (error) {
        containerEl.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load hotels.')}</p>`;
    }
}

function renderList(hotels) {
    containerEl.innerHTML = '';
    if (!hotels.length) { 
        containerEl.innerHTML = '<p style="color:#888;">No hotels found.</p>'; 
        return; 
    }
    hotels.forEach(h => {
        const d = document.createElement('div');
        d.className = 'list-item';
        const location = [h.city, h.country].filter(Boolean).join(', ') || 'N/A';
        const stars = '★'.repeat(h.star_rating || 0);
        d.innerHTML = `
            <strong>${h.name}</strong>
            <p>Location: ${location} &nbsp;|&nbsp; ${stars}</p>
            <p style="font-size:0.8rem;color:#888;">${h.rooms ? h.rooms.filter(r => r.status === 'AVAILABLE').length : 0} room(s) available</p>
            <button onclick="openHotel(${h.hotel_id})">View Details</button>
        `;
        containerEl.appendChild(d);
    });
}

window.openHotel = async function(id) {
    currentHotelId = id;
    bookSection.classList.add('hidden');
    
    try {
        const hotel = await apiFetch(`/customer/hotels/${id}`);
        
        document.getElementById('detailName').textContent = hotel.name;
        const location = [hotel.city, hotel.country].filter(Boolean).join(', ') || hotel.address || 'N/A';
        document.getElementById('detailLocation').textContent = location;
        const stars = '★'.repeat(hotel.star_rating || 0);
        document.getElementById('detailStars').textContent = `${stars} (${hotel.star_rating || 0} stars)`;

        const roomDiv = document.getElementById('roomList');
        roomDiv.innerHTML = '';
        if (hotel.rooms && hotel.rooms.length > 0) {
            hotel.rooms.forEach(r => {
                const d = document.createElement('div');
                d.className = 'list-item';
                const available = r.status === 'AVAILABLE';
                d.innerHTML = `
                    <strong>${r.room_type} (Room ${r.room_number})</strong>
                    <p>${formatCurrency(r.price_per_night)}/night &nbsp;|&nbsp; Capacity: ${r.capacity} &nbsp;|&nbsp; ${available ? 'Available' : '<span style="color:red;">Not Available</span>'}</p>
                    ${available ? `<button onclick="startBook(${r.room_id})">Book This Room</button>` : ''}
                `;
                roomDiv.appendChild(d);
            });
        } else {
            roomDiv.innerHTML = '<p style="color:#888;">No available rooms.</p>';
        }

        listView.classList.add('hidden');
        detailView.classList.remove('hidden');
    } catch (error) {
        showMessage('bookingMsg', handleApiError(error, 'Failed to load hotel details.'), 'error');
    }
};

window.startBook = function(roomId) {
    currentRoomId = roomId;
    const roomDiv = document.getElementById('roomList');
    const roomElements = roomDiv.querySelectorAll('.list-item');
    let selectedRoom = null;
    roomElements.forEach(el => {
        const btn = el.querySelector('button');
        if (btn && btn.onclick && btn.onclick.toString().includes(roomId)) {
            const text = el.querySelector('strong').textContent;
            const priceMatch = el.textContent.match(/\$[\d.]+/);
            selectedRoom = { text, price: priceMatch ? priceMatch[0] : '' };
        }
    });
    document.getElementById('bookingRoomLabel').textContent = selectedRoom 
        ? `Room: ${selectedRoom.text} – ${selectedRoom.price}/night`
        : `Room ID: ${roomId}`;
    bookingMsg.textContent = '';
    bookSection.classList.remove('hidden');
    bookSection.scrollIntoView({ behavior: 'smooth' });
};

async function bookRoom() {
    const ci = document.getElementById('checkIn').value;
    const co = document.getElementById('checkOut').value;
    const g = document.getElementById('guests').value;
    
    if (!ci || !co) { 
        showMessage('bookingMsg', 'Please select check-in and check-out dates.', 'error'); 
        return; 
    }
    if (co <= ci) { 
        showMessage('bookingMsg', 'Check-out must be after check-in.', 'error'); 
        return; 
    }
    if (!currentRoomId) {
        showMessage('bookingMsg', 'Please select a room first.', 'error');
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
                trip_name: `Hotel Booking ${new Date().toLocaleDateString()}`,
                start_date: ci,
                end_date: co
            })
        });
        console.log('Trip created:', tripData);
        const tripId = tripData.trip_id;

        // Now create the booking with the trip_id
        console.log('Creating booking with trip_id:', tripId);
        const data = await apiFetch('/customer/bookings', {
            method: 'POST',
            body: JSON.stringify({
                booking_type: 'HOTEL',
                trip_id: tripId,
                room_id: currentRoomId,
                check_in_date: ci,
                check_out_date: co,
                number_of_guests: parseInt(g) || 1
            })
        });

        showMessage('bookingMsg', `✓ Booking confirmed! Booking ID: ${data.booking_id}, Total: ${formatCurrency(data.total_amount)}`, 'success');
        bookSection.classList.add('hidden');
        
        // Refresh dashboard data if on dashboard
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

