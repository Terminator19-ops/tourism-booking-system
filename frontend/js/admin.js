// Uses shared api.js for auth, API calls, and error handling

document.addEventListener('DOMContentLoaded', async () => {
    const user = await loadCurrentUser();
    if (!user) return;

    if (!requireRole(['ADMIN'])) return;

    renderNavigation();

    document.getElementById('welcomeMessage').textContent = `Admin Dashboard - ${user.first_name} ${user.last_name}`;

    document.getElementById('logoutBtn').addEventListener('click', async () => {
        await logout();
    });

    // Load destinations for select dropdowns first
    await loadDestinationsForSelect();

    // Load all admin data
    await loadAllAdminData();

    // Form handlers
    setupFormHandlers();
});

async function loadDestinationsForSelect() {
    try {
        const destinations = await apiFetch('/admin/destinations');
        const selects = ['hotelDestinationId', 'activityDestinationId', 'pkgDestDestinationId', 'tsOriginId', 'tsDestinationId'];
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (select) {
                select.innerHTML = '<option value="">Select destination</option>';
                destinations.forEach(d => {
                    if (d.status === 'ACTIVE') {
                        const option = document.createElement('option');
                        option.value = d.destination_id;
                        option.textContent = `${d.name}${d.city ? ', ' + d.city : ''}${d.state ? ', ' + d.state : ''}${d.country ? ', ' + d.country : ''}`;
                        select.appendChild(option);
                    }
                });
            }
        });
    } catch (error) {
        console.error('Failed to load destinations for select:', error);
    }
}

async function loadAllAdminData() {
    try {
        await Promise.all([
            loadUsers(),
            loadDestinations(),
            loadHotels(),
            loadRooms(),
            loadActivities(),
            loadPackages(),
            loadPackageDestinations(),
            loadPackageActivities(),
            loadTravelSegments(),
            loadTrips(),
            loadBookings(),
            loadReports(),
            loadAuditLogs()
        ]);
    } catch (error) {
        console.error('Failed to load admin data:', error);
    }
}

function setupFormHandlers() {
    // Users
    document.getElementById('userForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await createUser();
    });

    // Destinations
    document.getElementById('destinationForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await createDestination();
    });

    // Hotels
    document.getElementById('hotelForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await createHotel();
    });

    // Rooms
    document.getElementById('roomForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await createRoom();
    });

    // Activities
    document.getElementById('activityForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await createActivity();
    });

    // Packages
    document.getElementById('packageForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await createPackage();
    });

    // Package Destinations
    document.getElementById('packageDestinationForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await createPackageDestination();
    });

    // Package Activities
    document.getElementById('packageActivityForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await createPackageActivity();
    });

    // Travel Segments
    document.getElementById('travelSegmentForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await createTravelSegment();
    });

    // Reports
    document.getElementById('reportForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await createReport();
    });

    // Audit Log Filters
    document.getElementById('auditFilterBtn').addEventListener('click', () => loadAuditLogs());
    document.getElementById('auditClearBtn').addEventListener('click', () => {
        document.getElementById('auditEntityFilter').value = '';
        document.getElementById('auditActionFilter').value = '';
        document.getElementById('auditUserFilter').value = '';
        loadAuditLogs();
    });
}

// ============================================================
// USERS
// ============================================================
async function loadUsers() {
    const container = document.getElementById('userList');
    container.innerHTML = '<p style="color:#888;">Loading users...</p>';
    try {
        const users = await apiFetch('/admin/users');
        renderUsers(users);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load users.')}</p>`;
    }
}

function renderUsers(users) {
    const container = document.getElementById('userList');
    container.innerHTML = '';
    if (!users.length) { container.innerHTML = '<p style="color:#888;">No users found.</p>'; return; }
    users.forEach(u => {
        const d = document.createElement('div');
        d.className = 'list-item';
        d.innerHTML = `
            <strong>${u.first_name} ${u.last_name}</strong>
            <p>Email: ${u.email} | Phone: ${u.phone || 'N/A'} | Role: ${u.role} | Status: ${u.status}</p>
            <button onclick="editUser(${u.user_id})">Edit</button>
            <button class="danger" onclick="deleteUser(${u.user_id})">${u.status === 'ACTIVE' ? 'Deactivate' : 'Delete'}</button>
        `;
        container.appendChild(d);
    });
}

async function createUser() {
    const btn = document.querySelector('#userForm button[type="submit"]');
    showLoading(btn, true);
    try {
        await apiFetch('/admin/users', {
            method: 'POST',
            body: JSON.stringify({
                first_name: document.getElementById('userFirstName').value.trim(),
                last_name: document.getElementById('userLastName').value.trim(),
                email: document.getElementById('userEmail').value.trim(),
                phone: document.getElementById('userPhone').value.trim(),
                password: document.getElementById('userPassword').value,
                role: document.getElementById('userRole').value,
                status: document.getElementById('userStatus').value
            })
        });
        document.getElementById('userForm').reset();
        await loadUsers();
    } catch (error) {
        alert(handleApiError(error, 'Failed to create user.'));
    } finally {
        showLoading(btn, false);
    }
}

async function editUser(userId) {
    const user = await apiFetch(`/admin/users/${userId}`);
    const firstName = prompt('First name:', user.first_name);
    if (firstName === null) return;
    const lastName = prompt('Last name:', user.last_name);
    if (lastName === null) return;
    const email = prompt('Email:', user.email);
    if (email === null) return;
    const phone = prompt('Phone:', user.phone || '');
    if (phone === null) return;
    const role = prompt('Role (CUSTOMER/OWNER/ADMIN):', user.role);
    if (role === null) return;
    const status = prompt('Status (ACTIVE/INACTIVE):', user.status);
    if (status === null) return;

    try {
        await apiFetch(`/admin/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify({
                first_name: firstName.trim(),
                last_name: lastName.trim(),
                email: email.trim(),
                phone: phone.trim(),
                role: role.trim().toUpperCase(),
                status: status.trim().toUpperCase()
            })
        });
        await loadUsers();
    } catch (error) {
        alert(handleApiError(error, 'Failed to update user.'));
    }
}

async function deleteUser(userId) {
    if (!confirm('Are you sure? This will deactivate or delete the user.')) return;
    try {
        await apiFetch(`/admin/users/${userId}`, { method: 'DELETE' });
        await loadUsers();
    } catch (error) {
        alert(handleApiError(error, 'Failed to delete user.'));
    }
}

// ============================================================
// DESTINATIONS
// ============================================================
async function loadDestinations() {
    const container = document.getElementById('destinationList');
    container.innerHTML = '<p style="color:#888;">Loading destinations...</p>';
    try {
        const destinations = await apiFetch('/admin/destinations');
        renderDestinations(destinations);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load destinations.')}</p>`;
    }
}

function renderDestinations(destinations) {
    const container = document.getElementById('destinationList');
    container.innerHTML = '';
    if (!destinations.length) { container.innerHTML = '<p style="color:#888;">No destinations found.</p>'; return; }
    destinations.forEach(d => {
        const div = document.createElement('div');
        div.className = 'list-item';
        div.innerHTML = `
            <strong>${d.name}</strong>
            <p>${d.city}, ${d.state || ''} ${d.country} | Status: ${d.status}</p>
            <button onclick="editDestination(${d.destination_id})">Edit</button>
            <button class="danger" onclick="deleteDestination(${d.destination_id})">${d.status === 'ACTIVE' ? 'Deactivate' : 'Delete'}</button>
        `;
        container.appendChild(div);
    });
}

async function createDestination() {
    const btn = document.querySelector('#destinationForm button[type="submit"]');
    showLoading(btn, true);
    try {
        await apiFetch('/admin/destinations', {
            method: 'POST',
            body: JSON.stringify({
                name: document.getElementById('destinationName').value.trim(),
                city: document.getElementById('destinationCity').value.trim(),
                country: document.getElementById('destinationCountry').value.trim(),
                state: document.getElementById('destinationState').value.trim() || null,
                description: document.getElementById('destinationDescription').value.trim() || null,
                status: document.getElementById('destinationStatus').value
            })
        });
        document.getElementById('destinationForm').reset();
        await loadDestinations();
    } catch (error) {
        alert(handleApiError(error, 'Failed to create destination.'));
    } finally {
        showLoading(btn, false);
    }
}

async function editDestination(id) {
    const dest = await apiFetch(`/admin/destinations/${id}`);
    const name = prompt('Name:', dest.name);
    if (name === null) return;
    const city = prompt('City:', dest.city);
    if (city === null) return;
    const country = prompt('Country:', dest.country);
    if (country === null) return;
    const state = prompt('State:', dest.state || '');
    if (state === null) return;
    const description = prompt('Description:', dest.description || '');
    if (description === null) return;
    const status = prompt('Status (ACTIVE/INACTIVE):', dest.status);
    if (status === null) return;

    try {
        await apiFetch(`/admin/destinations/${id}`, {
            method: 'PUT',
            body: JSON.stringify({
                name: name.trim(),
                city: city.trim(),
                country: country.trim(),
                state: state.trim() || null,
                description: description.trim() || null,
                status: status.trim().toUpperCase()
            })
        });
        await loadDestinations();
    } catch (error) {
        alert(handleApiError(error, 'Failed to update destination.'));
    }
}

async function deleteDestination(id) {
    if (!confirm('Are you sure?')) return;
    try {
        await apiFetch(`/admin/destinations/${id}`, { method: 'DELETE' });
        await loadDestinations();
    } catch (error) {
        alert(handleApiError(error, 'Failed to delete destination.'));
    }
}

// ============================================================
// HOTELS
// ============================================================
async function loadHotels() {
    const container = document.getElementById('hotelList');
    container.innerHTML = '<p style="color:#888;">Loading hotels...</p>';
    try {
        const hotels = await apiFetch('/admin/hotels');
        renderHotels(hotels);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load hotels.')}</p>`;
    }
}

function renderHotels(hotels) {
    const container = document.getElementById('hotelList');
    container.innerHTML = '';
    if (!hotels.length) { container.innerHTML = '<p style="color:#888;">No hotels found.</p>'; return; }
    hotels.forEach(h => {
        const div = document.createElement('div');
        div.className = 'list-item';
        div.innerHTML = `
            <strong>${h.name}</strong>
            <p>${h.address} | Owner: ${h.owner_name || 'N/A'} | Destination: ${h.destination_name || 'N/A'} | ${'★'.repeat(h.star_rating || 0)} | Status: ${h.status}</p>
            <button onclick="editHotel(${h.hotel_id})">Edit</button>
            <button class="danger" onclick="deleteHotel(${h.hotel_id})">${h.status === 'ACTIVE' ? 'Deactivate' : 'Delete'}</button>
        `;
        container.appendChild(div);
    });
}

async function createHotel() {
    const btn = document.querySelector('#hotelForm button[type="submit"]');
    showLoading(btn, true);
    try {
        await apiFetch('/admin/hotels', {
            method: 'POST',
            body: JSON.stringify({
                destination_id: Number(document.getElementById('hotelDestinationId').value),
                name: document.getElementById('hotelName').value.trim(),
                address: document.getElementById('hotelAddress').value.trim(),
                description: document.getElementById('hotelDescription').value.trim() || null,
                contact_number: document.getElementById('hotelContact').value.trim() || null,
                email: document.getElementById('hotelEmail').value.trim() || null,
                star_rating: parseFloat(document.getElementById('hotelStarRating').value) || 4.5,
                status: document.getElementById('hotelStatus').value
            })
        });
        document.getElementById('hotelForm').reset();
        await loadHotels();
    } catch (error) {
        alert(handleApiError(error, 'Failed to create hotel.'));
    } finally {
        showLoading(btn, false);
    }
}

async function editHotel(id) {
    const hotel = await apiFetch(`/admin/hotels/${id}`);
    const name = prompt('Name:', hotel.name);
    if (name === null) return;
    const address = prompt('Address:', hotel.address);
    if (address === null) return;
    const description = prompt('Description:', hotel.description || '');
    if (description === null) return;
    const contact = prompt('Contact:', hotel.contact_number || '');
    if (contact === null) return;
    const email = prompt('Email:', hotel.email || '');
    if (email === null) return;
    const starRating = prompt('Star rating:', hotel.star_rating || 4.5);
    if (starRating === null) return;
    const status = prompt('Status (ACTIVE/INACTIVE):', hotel.status);
    if (status === null) return;

    try {
        await apiFetch(`/admin/hotels/${id}`, {
            method: 'PUT',
            body: JSON.stringify({
                name: name.trim(),
                address: address.trim(),
                description: description.trim() || null,
                contact_number: contact.trim() || null,
                email: email.trim() || null,
                star_rating: parseFloat(starRating),
                status: status.trim().toUpperCase()
            })
        });
        await loadHotels();
    } catch (error) {
        alert(handleApiError(error, 'Failed to update hotel.'));
    }
}

async function deleteHotel(id) {
    if (!confirm('Are you sure?')) return;
    try {
        await apiFetch(`/admin/hotels/${id}`, { method: 'DELETE' });
        await loadHotels();
    } catch (error) {
        alert(handleApiError(error, 'Failed to delete hotel.'));
    }
}

// ============================================================
// ROOMS
// ============================================================
async function loadRooms() {
    const container = document.getElementById('roomList');
    container.innerHTML = '<p style="color:#888;">Loading rooms...</p>';
    try {
        const rooms = await apiFetch('/admin/rooms');
        renderRooms(rooms);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load rooms.')}</p>`;
    }
}

function renderRooms(rooms) {
    const container = document.getElementById('roomList');
    container.innerHTML = '';
    if (!rooms.length) { container.innerHTML = '<p style="color:#888;">No rooms found.</p>'; return; }
    rooms.forEach(r => {
        const div = document.createElement('div');
        div.className = 'list-item';
        div.innerHTML = `
            <strong>Room ${r.room_id} - ${r.room_type}</strong>
            <p>Hotel: ${r.hotel_name || 'N/A'} | ${formatCurrency(r.price_per_night)}/night | Capacity: ${r.capacity} | Status: ${r.status}</p>
            <button onclick="editRoom(${r.room_id})">Edit</button>
            <button class="danger" onclick="deleteRoom(${r.room_id})">${r.status === 'AVAILABLE' ? 'Deactivate' : 'Delete'}</button>
        `;
        container.appendChild(div);
    });
}

async function createRoom() {
    const btn = document.querySelector('#roomForm button[type="submit"]');
    showLoading(btn, true);
    try {
        await apiFetch('/admin/rooms', {
            method: 'POST',
            body: JSON.stringify({
                hotel_id: Number(document.getElementById('roomHotelId').value),
                room_type: document.getElementById('roomType').value.trim(),
                description: document.getElementById('roomDescription').value.trim() || null,
                price_per_night: parseFloat(document.getElementById('roomPrice').value),
                capacity: Number(document.getElementById('roomCapacity').value),
                amenities: document.getElementById('roomAmenities').value.trim() || null,
                status: document.getElementById('roomStatus').value
            })
        });
        document.getElementById('roomForm').reset();
        await loadRooms();
    } catch (error) {
        alert(handleApiError(error, 'Failed to create room.'));
    } finally {
        showLoading(btn, false);
    }
}

async function editRoom(id) {
    const room = await apiFetch(`/admin/rooms/${id}`);
    const roomType = prompt('Room type:', room.room_type);
    if (roomType === null) return;
    const description = prompt('Description:', room.description || '');
    if (description === null) return;
    const price = prompt('Price per night:', room.price_per_night);
    if (price === null) return;
    const capacity = prompt('Capacity:', room.capacity);
    if (capacity === null) return;
    const amenities = prompt('Amenities:', room.amenities || '');
    if (amenities === null) return;
    const status = prompt('Status (AVAILABLE/OCCUPIED/MAINTENANCE/INACTIVE):', room.status);
    if (status === null) return;

    try {
        await apiFetch(`/admin/rooms/${id}`, {
            method: 'PUT',
            body: JSON.stringify({
                room_type: roomType.trim(),
                description: description.trim() || null,
                price_per_night: parseFloat(price),
                capacity: Number(capacity),
                amenities: amenities.trim() || null,
                status: status.trim().toUpperCase()
            })
        });
        await loadRooms();
    } catch (error) {
        alert(handleApiError(error, 'Failed to update room.'));
    }
}

async function deleteRoom(id) {
    if (!confirm('Are you sure?')) return;
    try {
        await apiFetch(`/admin/rooms/${id}`, { method: 'DELETE' });
        await loadRooms();
    } catch (error) {
        alert(handleApiError(error, 'Failed to delete room.'));
    }
}

// ============================================================
// ACTIVITIES
// ============================================================
async function loadActivities() {
    const container = document.getElementById('activityList');
    container.innerHTML = '<p style="color:#888;">Loading activities...</p>';
    try {
        const activities = await apiFetch('/admin/activities');
        renderActivities(activities);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load activities.')}</p>`;
    }
}

function renderActivities(activities) {
    const container = document.getElementById('activityList');
    container.innerHTML = '';
    if (!activities.length) { container.innerHTML = '<p style="color:#888;">No activities found.</p>'; return; }
    activities.forEach(a => {
        const div = document.createElement('div');
        div.className = 'list-item';
        div.innerHTML = `
            <strong>${a.name}</strong>
            <p>Destination: ${a.destination_name || 'N/A'} | Category: ${a.category} | ${a.duration_hours}h | ${formatCurrency(a.price)} | Capacity: ${a.capacity} | Status: ${a.status}</p>
            <button onclick="editActivity(${a.activity_id})">Edit</button>
            <button class="danger" onclick="deleteActivity(${a.activity_id})">${a.status === 'ACTIVE' ? 'Deactivate' : 'Delete'}</button>
        `;
        container.appendChild(div);
    });
}

async function createActivity() {
    const btn = document.querySelector('#activityForm button[type="submit"]');
    showLoading(btn, true);
    try {
        await apiFetch('/admin/activities', {
            method: 'POST',
            body: JSON.stringify({
                destination_id: Number(document.getElementById('activityDestinationId').value),
                name: document.getElementById('activityName').value.trim(),
                description: document.getElementById('activityDescription').value.trim() || null,
                category: document.getElementById('activityCategory').value.trim() || 'General',
                duration_hours: parseFloat(document.getElementById('activityDuration').value) || 1,
                price: parseFloat(document.getElementById('activityPrice').value),
                capacity: Number(document.getElementById('activityCapacity').value) || 1,
                status: document.getElementById('activityStatus').value
            })
        });
        document.getElementById('activityForm').reset();
        await loadActivities();
    } catch (error) {
        alert(handleApiError(error, 'Failed to create activity.'));
    } finally {
        showLoading(btn, false);
    }
}

async function editActivity(id) {
    const act = await apiFetch(`/admin/activities/${id}`);
    const name = prompt('Name:', act.name);
    if (name === null) return;
    const description = prompt('Description:', act.description || '');
    if (description === null) return;
    const category = prompt('Category:', act.category);
    if (category === null) return;
    const duration = prompt('Duration (hours):', act.duration_hours);
    if (duration === null) return;
    const price = prompt('Price:', act.price);
    if (price === null) return;
    const capacity = prompt('Capacity:', act.capacity);
    if (capacity === null) return;
    const status = prompt('Status (ACTIVE/INACTIVE):', act.status);
    if (status === null) return;

    try {
        await apiFetch(`/admin/activities/${id}`, {
            method: 'PUT',
            body: JSON.stringify({
                name: name.trim(),
                description: description.trim() || null,
                category: category.trim(),
                duration_hours: parseFloat(duration),
                price: parseFloat(price),
                capacity: Number(capacity),
                status: status.trim().toUpperCase()
            })
        });
        await loadActivities();
    } catch (error) {
        alert(handleApiError(error, 'Failed to update activity.'));
    }
}

async function deleteActivity(id) {
    if (!confirm('Are you sure?')) return;
    try {
        await apiFetch(`/admin/activities/${id}`, { method: 'DELETE' });
        await loadActivities();
    } catch (error) {
        alert(handleApiError(error, 'Failed to delete activity.'));
    }
}

// ============================================================
// TOUR PACKAGES
// ============================================================
async function loadPackages() {
    const container = document.getElementById('packageList');
    container.innerHTML = '<p style="color:#888;">Loading packages...</p>';
    try {
        const packages = await apiFetch('/admin/tour-packages');
        renderPackages(packages);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load packages.')}</p>`;
    }
}

function renderPackages(packages) {
    const container = document.getElementById('packageList');
    container.innerHTML = '';
    if (!packages.length) { container.innerHTML = '<p style="color:#888;">No packages found.</p>'; return; }
    packages.forEach(p => {
        const div = document.createElement('div');
        div.className = 'list-item';
        div.innerHTML = `
            <strong>${p.name}</strong>
            <p>${p.description || 'No description'} | ${p.duration_days} days | ${formatCurrency(p.price)} | Max: ${p.max_capacity || 'N/A'} | Status: ${p.status}</p>
            <button onclick="editPackage(${p.package_id})">Edit</button>
            <button class="danger" onclick="deletePackage(${p.package_id})">${p.status === 'ACTIVE' ? 'Deactivate' : 'Delete'}</button>
        `;
        container.appendChild(div);
    });
}

async function createPackage() {
    const btn = document.querySelector('#packageForm button[type="submit"]');
    showLoading(btn, true);
    try {
        await apiFetch('/admin/tour-packages', {
            method: 'POST',
            body: JSON.stringify({
                name: document.getElementById('packageName').value.trim(),
                description: document.getElementById('packageDescription').value.trim() || null,
                duration_days: Number(document.getElementById('packageDays').value),
                price: parseFloat(document.getElementById('packagePrice').value),
                max_capacity: document.getElementById('packageMaxCapacity').value ? Number(document.getElementById('packageMaxCapacity').value) : null,
                status: document.getElementById('packageStatus').value
            })
        });
        document.getElementById('packageForm').reset();
        await loadPackages();
    } catch (error) {
        alert(handleApiError(error, 'Failed to create package.'));
    } finally {
        showLoading(btn, false);
    }
}

async function editPackage(id) {
    const pkg = await apiFetch(`/admin/tour-packages/${id}`);
    const name = prompt('Name:', pkg.name);
    if (name === null) return;
    const description = prompt('Description:', pkg.description || '');
    if (description === null) return;
    const days = prompt('Duration days:', pkg.duration_days);
    if (days === null) return;
    const price = prompt('Price:', pkg.price);
    if (price === null) return;
    const maxCap = prompt('Max capacity:', pkg.max_capacity || '');
    if (maxCap === null) return;
    const status = prompt('Status (ACTIVE/INACTIVE):', pkg.status);
    if (status === null) return;

    try {
        await apiFetch(`/admin/tour-packages/${id}`, {
            method: 'PUT',
            body: JSON.stringify({
                name: name.trim(),
                description: description.trim() || null,
                duration_days: Number(days),
                price: parseFloat(price),
                max_capacity: maxCap ? Number(maxCap) : null,
                status: status.trim().toUpperCase()
            })
        });
        await loadPackages();
    } catch (error) {
        alert(handleApiError(error, 'Failed to update package.'));
    }
}

async function deletePackage(id) {
    if (!confirm('Are you sure?')) return;
    try {
        await apiFetch(`/admin/tour-packages/${id}`, { method: 'DELETE' });
        await loadPackages();
    } catch (error) {
        alert(handleApiError(error, 'Failed to delete package.'));
    }
}

// ============================================================
// PACKAGE DESTINATIONS
// ============================================================
async function loadPackageDestinations() {
    const container = document.getElementById('packageDestinationList');
    container.innerHTML = '<p style="color:#888;">Loading package destinations...</p>';
    try {
        // We need to fetch all packages and their destinations
        const packages = await apiFetch('/admin/tour-packages');
        let allDestinations = [];
        for (const pkg of packages) {
            if (pkg.destinations) {
                pkg.destinations.forEach(d => {
                    allDestinations.push({...d, package_id: pkg.package_id, package_name: pkg.name});
                });
            }
        }
        renderPackageDestinations(allDestinations);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load package destinations.')}</p>`;
    }
}

function renderPackageDestinations(destinations) {
    const container = document.getElementById('packageDestinationList');
    container.innerHTML = '';
    if (!destinations.length) { container.innerHTML = '<p style="color:#888;">No package destinations found.</p>'; return; }
    destinations.forEach(d => {
        const div = document.createElement('div');
        div.className = 'list-item';
        div.innerHTML = `
            <strong>Package: ${d.package_name} (ID: ${d.package_id})</strong>
            <p>Destination: ${d.name} | Visit Order: ${d.visit_order} | Days: ${d.days}</p>
            <button class="danger" onclick="deletePackageDestination(${d.package_id}, ${d.destination_id})">Remove</button>
        `;
        container.appendChild(div);
    });
}

async function createPackageDestination() {
    const btn = document.querySelector('#packageDestinationForm button[type="submit"]');
    showLoading(btn, true);
    try {
        const packageId = Number(document.getElementById('pkgDestPackageId').value);
        await apiFetch(`/admin/tour-packages/${packageId}/destinations`, {
            method: 'POST',
            body: JSON.stringify({
                destination_id: Number(document.getElementById('pkgDestDestinationId').value),
                visit_order: Number(document.getElementById('pkgDestVisitOrder').value),
                days: Number(document.getElementById('pkgDestDays').value)
            })
        });
        document.getElementById('packageDestinationForm').reset();
        await loadPackageDestinations();
    } catch (error) {
        alert(handleApiError(error, 'Failed to add package destination.'));
    } finally {
        showLoading(btn, false);
    }
}

async function deletePackageDestination(packageId, destinationId) {
    if (!confirm('Are you sure?')) return;
    try {
        await apiFetch(`/admin/tour-packages/${packageId}/destinations/${destinationId}`, { method: 'DELETE' });
        await loadPackageDestinations();
    } catch (error) {
        alert(handleApiError(error, 'Failed to remove package destination.'));
    }
}

// ============================================================
// PACKAGE ACTIVITIES
// ============================================================
async function loadPackageActivities() {
    const container = document.getElementById('packageActivityList');
    container.innerHTML = '<p style="color:#888;">Loading package activities...</p>';
    try {
        const packages = await apiFetch('/admin/tour-packages');
        let allActivities = [];
        for (const pkg of packages) {
            if (pkg.activities) {
                pkg.activities.forEach(a => {
                    allActivities.push({...a, package_id: pkg.package_id, package_name: pkg.name});
                });
            }
        }
        renderPackageActivities(allActivities);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load package activities.')}</p>`;
    }
}

function renderPackageActivities(activities) {
    const container = document.getElementById('packageActivityList');
    container.innerHTML = '';
    if (!activities.length) { container.innerHTML = '<p style="color:#888;">No package activities found.</p>'; return; }
    activities.forEach(a => {
        const div = document.createElement('div');
        div.className = 'list-item';
        div.innerHTML = `
            <strong>Package: ${a.package_name} (ID: ${a.package_id})</strong>
            <p>Activity: ${a.name} | Day: ${a.activity_day}</p>
            <button class="danger" onclick="deletePackageActivity(${a.package_id}, ${a.activity_id})">Remove</button>
        `;
        container.appendChild(div);
    });
}

async function createPackageActivity() {
    const btn = document.querySelector('#packageActivityForm button[type="submit"]');
    showLoading(btn, true);
    try {
        const packageId = Number(document.getElementById('pkgActPackageId').value);
        await apiFetch(`/admin/tour-packages/${packageId}/activities`, {
            method: 'POST',
            body: JSON.stringify({
                activity_id: Number(document.getElementById('pkgActActivityId').value),
                activity_day: Number(document.getElementById('pkgActDay').value)
            })
        });
        document.getElementById('packageActivityForm').reset();
        await loadPackageActivities();
    } catch (error) {
        alert(handleApiError(error, 'Failed to add package activity.'));
    } finally {
        showLoading(btn, false);
    }
}

async function deletePackageActivity(packageId, activityId) {
    if (!confirm('Are you sure?')) return;
    try {
        await apiFetch(`/admin/tour-packages/${packageId}/activities/${activityId}`, { method: 'DELETE' });
        await loadPackageActivities();
    } catch (error) {
        alert(handleApiError(error, 'Failed to remove package activity.'));
    }
}

// ============================================================
// TRAVEL SEGMENTS
// ============================================================
async function loadTravelSegments() {
    const container = document.getElementById('travelSegmentList');
    container.innerHTML = '<p style="color:#888;">Loading travel segments...</p>';
    try {
        const segments = await apiFetch('/admin/travel-segments');
        renderTravelSegments(segments);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load travel segments.')}</p>`;
    }
}

function renderTravelSegments(segments) {
    const container = document.getElementById('travelSegmentList');
    container.innerHTML = '';
    if (!segments.length) { container.innerHTML = '<p style="color:#888;">No travel segments found.</p>'; return; }
    segments.forEach(s => {
        const div = document.createElement('div');
        div.className = 'list-item';
        div.innerHTML = `
            <strong>${s.origin_name} → ${s.destination_name}</strong>
            <p>${s.transport_type} | ${s.operator_name || 'N/A'} | ${formatDateTime(s.departure_time)} → ${formatDateTime(s.arrival_time)} | ${formatCurrency(s.price)} | Capacity: ${s.capacity} | Status: ${s.status}</p>
            <button onclick="editTravelSegment(${s.travel_segment_id})">Edit</button>
            <button class="danger" onclick="deleteTravelSegment(${s.travel_segment_id})">${s.status === 'SCHEDULED' ? 'Deactivate' : 'Delete'}</button>
        `;
        container.appendChild(div);
    });
}

async function createTravelSegment() {
    const btn = document.querySelector('#travelSegmentForm button[type="submit"]');
    showLoading(btn, true);
    try {
        await apiFetch('/admin/travel-segments', {
            method: 'POST',
            body: JSON.stringify({
                origin_destination_id: Number(document.getElementById('tsOriginId').value),
                destination_destination_id: Number(document.getElementById('tsDestinationId').value),
                transport_type: document.getElementById('tsTransportType').value.trim(),
                operator_name: document.getElementById('tsOperator').value.trim() || null,
                departure_time: document.getElementById('tsDeparture').value,
                arrival_time: document.getElementById('tsArrival').value,
                duration_hours: parseFloat(document.getElementById('tsDuration').value),
                price: parseFloat(document.getElementById('tsPrice').value),
                capacity: Number(document.getElementById('tsCapacity').value),
                status: document.getElementById('tsStatus').value
            })
        });
        document.getElementById('travelSegmentForm').reset();
        await loadTravelSegments();
    } catch (error) {
        alert(handleApiError(error, 'Failed to create travel segment.'));
    } finally {
        showLoading(btn, false);
    }
}

async function editTravelSegment(id) {
    const seg = await apiFetch(`/admin/travel-segments/${id}`);
    const transportType = prompt('Transport type:', seg.transport_type);
    if (transportType === null) return;
    const operator = prompt('Operator:', seg.operator_name || '');
    if (operator === null) return;
    const departure = prompt('Departure (ISO format):', seg.departure_time);
    if (departure === null) return;
    const arrival = prompt('Arrival (ISO format):', seg.arrival_time);
    if (arrival === null) return;
    const duration = prompt('Duration (hours):', seg.duration_hours);
    if (duration === null) return;
    const price = prompt('Price:', seg.price);
    if (price === null) return;
    const capacity = prompt('Capacity:', seg.capacity);
    if (capacity === null) return;
    const status = prompt('Status (SCHEDULED/CANCELLED/COMPLETED):', seg.status);
    if (status === null) return;

    try {
        await apiFetch(`/admin/travel-segments/${id}`, {
            method: 'PUT',
            body: JSON.stringify({
                transport_type: transportType.trim(),
                operator_name: operator.trim() || null,
                departure_time: departure,
                arrival_time: arrival,
                duration_hours: parseFloat(duration),
                price: parseFloat(price),
                capacity: Number(capacity),
                status: status.trim().toUpperCase()
            })
        });
        await loadTravelSegments();
    } catch (error) {
        alert(handleApiError(error, 'Failed to update travel segment.'));
    }
}

async function deleteTravelSegment(id) {
    if (!confirm('Are you sure?')) return;
    try {
        await apiFetch(`/admin/travel-segments/${id}`, { method: 'DELETE' });
        await loadTravelSegments();
    } catch (error) {
        alert(handleApiError(error, 'Failed to delete travel segment.'));
    }
}

// ============================================================
// TRIPS
// ============================================================
async function loadTrips() {
    const container = document.getElementById('tripList');
    container.innerHTML = '<p style="color:#888;">Loading trips...</p>';
    try {
        const trips = await apiFetch('/admin/trips');
        renderTrips(trips);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load trips.')}</p>`;
    }
}

function renderTrips(trips) {
    const container = document.getElementById('tripList');
    container.innerHTML = '';
    if (!trips.length) { container.innerHTML = '<p style="color:#888;">No trips found.</p>'; return; }
    trips.forEach(t => {
        const div = document.createElement('div');
        div.className = 'list-item';
        div.innerHTML = `
            <strong>${t.trip_name} (Customer: ${t.first_name} ${t.last_name})</strong>
            <p>${formatDate(t.start_date)} → ${formatDate(t.end_date)} | Status: ${t.status}</p>
            <button onclick="editTrip(${t.trip_id})">Edit</button>
            <button class="danger" onclick="deleteTrip(${t.trip_id})">${t.status !== 'CANCELLED' ? 'Cancel' : 'Delete'}</button>
        `;
        container.appendChild(div);
    });
}

async function editTrip(id) {
    const trip = await apiFetch(`/admin/trips/${id}`);
    const name = prompt('Trip name:', trip.trip_name);
    if (name === null) return;
    const startDate = prompt('Start date (YYYY-MM-DD):', trip.start_date);
    if (startDate === null) return;
    const endDate = prompt('End date (YYYY-MM-DD):', trip.end_date);
    if (endDate === null) return;
    const status = prompt('Status (PLANNED/IN_PROGRESS/COMPLETED/CANCELLED):', trip.status);
    if (status === null) return;

    try {
        await apiFetch(`/admin/trips/${id}`, {
            method: 'PUT',
            body: JSON.stringify({
                trip_name: name.trim(),
                start_date: startDate,
                end_date: endDate,
                status: status.trim().toUpperCase()
            })
        });
        await loadTrips();
    } catch (error) {
        alert(handleApiError(error, 'Failed to update trip.'));
    }
}

async function deleteTrip(id) {
    if (!confirm('Are you sure?')) return;
    try {
        await apiFetch(`/admin/trips/${id}`, { method: 'DELETE' });
        await loadTrips();
    } catch (error) {
        alert(handleApiError(error, 'Failed to delete trip.'));
    }
}

// ============================================================
// BOOKINGS
// ============================================================
async function loadBookings() {
    const container = document.getElementById('bookingList');
    container.innerHTML = '<p style="color:#888;">Loading bookings...</p>';
    try {
        const bookings = await apiFetch('/admin/bookings');
        renderBookings(bookings);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load bookings.')}</p>`;
    }
}

function renderBookings(bookings) {
    const container = document.getElementById('bookingList');
    container.innerHTML = '';
    if (!bookings.length) { container.innerHTML = '<p style="color:#888;">No bookings found.</p>'; return; }
    bookings.forEach(b => {
        const div = document.createElement('div');
        div.className = 'list-item';
        div.innerHTML = `
            <strong>Booking #${b.booking_id} (${b.booking_type})</strong>
            <p>Customer: ${b.first_name} ${b.last_name} (${b.email}) | ${formatCurrency(b.total_amount)} | Status: ${b.status}</p>
            <button onclick="editBooking(${b.booking_id})">Edit</button>
            <button class="danger" onclick="deleteBooking(${b.booking_id})">${b.status !== 'CANCELLED' ? 'Cancel' : 'Delete'}</button>
        `;
        container.appendChild(div);
    });
}

async function editBooking(id) {
    const booking = await apiFetch(`/admin/bookings/${id}`);
    const status = prompt('Status (PENDING/CONFIRMED/CANCELLED/COMPLETED):', booking.status);
    if (status === null) return;
    const totalAmount = prompt('Total amount:', booking.total_amount);
    if (totalAmount === null) return;

    try {
        await apiFetch(`/admin/bookings/${id}`, {
            method: 'PUT',
            body: JSON.stringify({
                status: status.trim().toUpperCase(),
                total_amount: parseFloat(totalAmount)
            })
        });
        await loadBookings();
    } catch (error) {
        alert(handleApiError(error, 'Failed to update booking.'));
    }
}

async function deleteBooking(id) {
    if (!confirm('Are you sure?')) return;
    try {
        await apiFetch(`/admin/bookings/${id}`, { method: 'DELETE' });
        await loadBookings();
    } catch (error) {
        alert(handleApiError(error, 'Failed to delete booking.'));
    }
}

// ============================================================
// REPORTS
// ============================================================
async function loadReports() {
    const container = document.getElementById('reportList');
    container.innerHTML = '<p style="color:#888;">Loading reports...</p>';
    try {
        const reports = await apiFetch('/admin/reports');
        renderReports(reports);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load reports.')}</p>`;
    }
}

function renderReports(reports) {
    const container = document.getElementById('reportList');
    container.innerHTML = '';
    if (!reports.length) { container.innerHTML = '<p style="color:#888;">No reports found.</p>'; return; }
    reports.forEach(r => {
        const div = document.createElement('div');
        div.className = 'list-item';
        div.innerHTML = `
            <strong>${r.title} (${r.report_type})</strong>
            <p>User: ${r.username || r.email || 'N/A'} | Status: ${r.status}</p>
            <button onclick="editReport(${r.report_id})">Edit</button>
            <button class="danger" onclick="deleteReport(${r.report_id})">Delete</button>
        `;
        container.appendChild(div);
    });
}

async function createReport() {
    const btn = document.querySelector('#reportForm button[type="submit"]');
    showLoading(btn, true);
    try {
        await apiFetch('/admin/reports', {
            method: 'POST',
            body: JSON.stringify({
                user_id: Number(document.getElementById('reportUserId').value),
                report_type: document.getElementById('reportType').value.trim(),
                title: document.getElementById('reportTitle').value.trim(),
                content: document.getElementById('reportContent').value.trim(),
                status: document.getElementById('reportStatus').value
            })
        });
        document.getElementById('reportForm').reset();
        await loadReports();
    } catch (error) {
        alert(handleApiError(error, 'Failed to create report.'));
    } finally {
        showLoading(btn, false);
    }
}

async function editReport(id) {
    const report = await apiFetch(`/admin/reports/${id}`);
    const title = prompt('Title:', report.title);
    if (title === null) return;
    const content = prompt('Content:', report.content);
    if (content === null) return;
    const status = prompt('Status (PENDING/COMPLETED/ARCHIVED):', report.status);
    if (status === null) return;

    try {
        await apiFetch(`/admin/reports/${id}`, {
            method: 'PUT',
            body: JSON.stringify({
                title: title.trim(),
                content: content.trim(),
                status: status.trim().toUpperCase()
            })
        });
        await loadReports();
    } catch (error) {
        alert(handleApiError(error, 'Failed to update report.'));
    }
}

async function deleteReport(id) {
    if (!confirm('Are you sure?')) return;
    try {
        await apiFetch(`/admin/reports/${id}`, { method: 'DELETE' });
        await loadReports();
    } catch (error) {
        alert(handleApiError(error, 'Failed to delete report.'));
    }
}

// ============================================================
// AUDIT LOGS
// ============================================================
async function loadAuditLogs() {
    const container = document.getElementById('auditLogList');
    container.innerHTML = '<p style="color:#888;">Loading audit logs...</p>';
    try {
        const entityName = document.getElementById('auditEntityFilter').value.trim();
        const action = document.getElementById('auditActionFilter').value.trim();
        const userId = document.getElementById('auditUserFilter').value;
        
        let url = '/admin/audit-logs?limit=100';
        if (entityName) url += `&entity_name=${encodeURIComponent(entityName)}`;
        if (action) url += `&action=${encodeURIComponent(action)}`;
        if (userId) url += `&user_id=${userId}`;
        
        const logs = await apiFetch(url);
        renderAuditLogs(logs);
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${handleApiError(error, 'Failed to load audit logs.')}</p>`;
    }
}

function renderAuditLogs(logs) {
    const container = document.getElementById('auditLogList');
    container.innerHTML = '';
    if (!logs.length) { container.innerHTML = '<p style="color:#888;">No audit logs found.</p>'; return; }
    logs.forEach(l => {
        const div = document.createElement('div');
        div.className = 'list-item';
        div.innerHTML = `
            <strong>${l.action} on ${l.entity_name} #${l.record_id}</strong>
            <p>User: ${l.user_id || 'System'} | ${formatDateTime(l.action_timestamp)}</p>
            <p style="font-size:0.8rem;color:#888;">Old: ${l.old_value ? l.old_value.substring(0, 100) + '...' : 'N/A'} | New: ${l.new_value ? l.new_value.substring(0, 100) + '...' : 'N/A'}</p>
        `;
        container.appendChild(div);
    });
}
