document.addEventListener('DOMContentLoaded', async () => {
    const user = await loadCurrentUser();
    if (!user || !requireRole(['CUSTOMER'])) { window.location.href = 'login.html'; return; }
    renderNavigation();
    await loadBookings();
});

async function loadBookings() {
    const container = document.getElementById('bookingsList');
    try {
        const bookings = await apiFetch('/customer/bookings');
        if (!bookings.length) {
            container.innerHTML = '<p style="color:#888;">No bookings yet.</p>';
            return;
        }
        container.innerHTML = bookings.map(b => {
            const total = Number(b.total_amount || 0);
            const paid = Number(b.paid_amount || 0);
            const balance = Math.max(total - paid, 0);
            const cancelled = b.status === 'CANCELLED';
            const completed = b.status === 'COMPLETED';
            return `
            <div class="list-item">
                <strong>#${b.booking_id} · ${escapeHtml(b.booking_type)}</strong>
                <p>Booked ${formatDate(b.booking_date)} | Trip: ${escapeHtml(b.trip_name || 'N/A')}</p>
                <p>Total ${formatCurrency(total)} | Paid ${formatCurrency(paid)} |
                   Balance ${cancelled ? '—' : formatCurrency(balance)} | Status: <strong>${escapeHtml(b.status)}</strong></p>
                <button onclick="toggleDetails(${b.booking_id})">Details</button>
                ${!cancelled && balance > 0 ? `<button class="primary" onclick="togglePay(${b.booking_id}, ${balance})">Pay</button>` : ''}
                ${!cancelled && !completed ? `<button class="danger" onclick="cancelBooking(${b.booking_id})">Cancel</button>` : ''}
                <div id="details-${b.booking_id}" class="hidden section-sep"></div>
                <div id="pay-${b.booking_id}" class="hidden section-sep"></div>
            </div>`;
        }).join('');
    } catch (error) {
        container.innerHTML = `<p style="color:red;">${escapeHtml(handleApiError(error, 'Failed to load bookings.'))}</p>`;
    }
}

function formatDetailValue(key, value) {
    if (value === null || value === undefined) return 'N/A';
    if (/time/.test(key)) return formatDateTime(value);
    if (/date/.test(key)) return formatDate(value);
    return escapeHtml(String(value));
}

async function toggleDetails(id) {
    const panel = document.getElementById(`details-${id}`);
    if (!panel.classList.contains('hidden')) { panel.classList.add('hidden'); return; }
    panel.classList.remove('hidden');
    panel.innerHTML = '<p style="color:#888;">Loading...</p>';
    try {
        const data = await apiFetch(`/customer/bookings/${id}`);
        const entries = Object.entries(data.details || {});
        panel.innerHTML = entries.length
            ? entries.map(([k, v]) => `<p style="font-size:0.85rem;"><strong>${escapeHtml(k.replace(/_/g, ' ').toLowerCase())}:</strong> ${formatDetailValue(k, v)}</p>`).join('')
            : '<p style="color:#888;">No extra details.</p>';
    } catch (error) {
        panel.innerHTML = `<p style="color:red;">${escapeHtml(handleApiError(error, 'Failed to load details.'))}</p>`;
    }
}

function togglePay(id, balance) {
    const panel = document.getElementById(`pay-${id}`);
    if (!panel.classList.contains('hidden')) { panel.classList.add('hidden'); return; }
    panel.classList.remove('hidden');
    panel.innerHTML = `
        <label style="font-size:0.85rem;">Amount (balance ${formatCurrency(balance)})</label>
        <input type="number" id="payAmount-${id}" min="0.01" max="${balance}" step="0.01" value="${balance.toFixed(2)}">
        <select id="payMethod-${id}">
            <option value="UPI">UPI</option>
            <option value="CREDIT_CARD">Credit card</option>
            <option value="DEBIT_CARD">Debit card</option>
            <option value="NET_BANKING">Net banking</option>
            <option value="WALLET">Wallet</option>
            <option value="CASH">Cash</option>
        </select>
        <button class="primary" onclick="submitPayment(${id})">Confirm payment</button>`;
}

async function submitPayment(id) {
    const amount = parseFloat(document.getElementById(`payAmount-${id}`).value);
    const payment_method = document.getElementById(`payMethod-${id}`).value;
    if (!amount || amount <= 0) { showMessage('pageMsg', 'Enter a valid amount.', 'error'); return; }
    try {
        const p = await apiFetch('/customer/payments', {
            method: 'POST',
            body: JSON.stringify({ booking_id: id, amount, payment_method })
        });
        await loadBookings();
        showMessage('pageMsg', `Payment successful. Ref: ${p.transaction_reference}`, 'success');
    } catch (error) {
        showMessage('pageMsg', handleApiError(error, 'Payment failed.'), 'error');
    }
}

async function cancelBooking(id) {
    if (!confirm('Cancel this booking? Successful payments will be refunded.')) return;
    try {
        const res = await apiFetch(`/customer/bookings/${id}`, { method: 'DELETE' });
        await loadBookings();
        showMessage('pageMsg', res.message, 'success');
    } catch (error) {
        showMessage('pageMsg', handleApiError(error, 'Could not cancel booking.'), 'error');
    }
}