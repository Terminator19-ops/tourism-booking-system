document.addEventListener('DOMContentLoaded', async () => {
    const user = await loadCurrentUser();
    if (!user || !requireRole(['CUSTOMER'])) { window.location.href = 'login.html'; return; }
    renderNavigation();

    const list = document.getElementById('paymentsList');
    try {
        const payments = await apiFetch('/customer/payments');
        const paid = payments.filter(p => p.status === 'SUCCESS').reduce((s, p) => s + Number(p.amount), 0);
        const refunded = payments.reduce((s, p) => s + Number(p.refund_amount || 0), 0);
        document.getElementById('paymentSummary').innerHTML =
            `<p><strong>Total paid:</strong> ${formatCurrency(paid)} | <strong>Total refunded:</strong> ${formatCurrency(refunded)}</p>`;

        list.innerHTML = payments.length ? payments.map(p => `
            <div class="list-item">
                <strong>${escapeHtml(p.transaction_reference)}</strong>
                <p>Booking #${p.booking_id} (${escapeHtml(p.booking_type)}) | ${formatCurrency(p.amount)} | ${escapeHtml(p.payment_method)}</p>
                <p>${formatDateTime(p.payment_date)} | Status: ${escapeHtml(p.status)}
                   ${Number(p.refund_amount) > 0 ? ` | Refunded: ${formatCurrency(p.refund_amount)}` : ''}</p>
            </div>`).join('') : '<p style="color:#888;">No payments yet.</p>';
    } catch (error) {
        list.innerHTML = `<p style="color:red;">${escapeHtml(handleApiError(error, 'Failed to load payments.'))}</p>`;
    }
});