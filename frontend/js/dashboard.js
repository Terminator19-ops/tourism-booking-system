// Uses shared api.js for auth, API calls, and error handling

document.addEventListener('DOMContentLoaded', async () => {
    const user = await loadCurrentUser();
    if (!user) return;

    renderNavigation();

    document.getElementById('welcomeMessage').textContent = `Welcome, ${user.first_name} ${user.last_name}!`;

    // Load dashboard data
    await loadDashboardData();

    document.getElementById('logoutBtn').addEventListener('click', async () => {
        await logout();
    });
});

async function loadDashboardData() {
    try {
        // Load upcoming trips
        const trips = await apiFetch('/customer/trips');
        renderUpcomingTrips(trips);

        // Load recent bookings
        const bookings = await apiFetch('/customer/bookings');
        renderRecentBookings(bookings);

        // Load recent payments
        const payments = await apiFetch('/customer/payments');
        renderRecentPayments(payments);
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
        document.getElementById('upcomingTrips').innerHTML = '<p style="color:red;">Failed to load trips.</p>';
        document.getElementById('recentBookings').innerHTML = '<p style="color:red;">Failed to load bookings.</p>';
        document.getElementById('recentPayments').innerHTML = '<p style="color:red;">Failed to load payments.</p>';
    }
}

function renderUpcomingTrips(trips) {
    const container = document.getElementById('upcomingTrips');
    if (!trips || trips.length === 0) {
        container.innerHTML = '<p style="color:#888;">No upcoming trips.</p>';
        return;
    }

    // Filter for upcoming trips (status PLANNED or IN_PROGRESS)
    const upcoming = trips.filter(t => t.status === 'PLANNED' || t.status === 'IN_PROGRESS');
    if (upcoming.length === 0) {
        container.innerHTML = '<p style="color:#888;">No upcoming trips.</p>';
        return;
    }

    container.innerHTML = upcoming.map(trip => `
        <div class="list-item">
            <strong>${trip.trip_name}</strong>
            <p>${formatDate(trip.start_date)} → ${formatDate(trip.end_date)}</p>
            <p style="font-size:0.8rem;color:#888;">Status: ${trip.status}</p>
            <button onclick="window.location.href='trips.html#${trip.trip_id}'">View Details</button>
        </div>
    `).join('');
}

function renderRecentBookings(bookings) {
    const container = document.getElementById('recentBookings');
    if (!bookings || bookings.length === 0) {
        container.innerHTML = '<p style="color:#888;">No bookings yet.</p>';
        return;
    }

    // Show last 5 bookings
    const recent = bookings.slice(0, 5);
    container.innerHTML = recent.map(booking => `
        <div class="list-item">
            <strong>${booking.booking_type} Booking</strong>
            <p>${formatDate(booking.booking_date)} | ${formatCurrency(booking.total_amount)} | Status: ${booking.status}</p>
            <p style="font-size:0.8rem;color:#888;">Trip: ${booking.trip_name || 'N/A'}</p>
        </div>
    `).join('');
}

function renderRecentPayments(payments) {
    const container = document.getElementById('recentPayments');
    if (!payments || payments.length === 0) {
        container.innerHTML = '<p style="color:#888;">No payments yet.</p>';
        return;
    }

    // Show last 5 payments
    const recent = payments.slice(0, 5);
    container.innerHTML = recent.map(payment => `
        <div class="list-item">
            <strong>${payment.booking_type || 'Booking'} Payment</strong>
            <p>${formatDateTime(payment.payment_date)} | ${formatCurrency(payment.amount)} | ${payment.payment_method} | Status: ${payment.status}</p>
        </div>
    `).join('');
}

