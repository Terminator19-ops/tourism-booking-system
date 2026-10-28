document.addEventListener('DOMContentLoaded', () => {
    const submit = async () => {
        const email = document.getElementById('adminEmail').value.trim();
        const password = document.getElementById('adminPassword').value;
        if (!email || !password) {
            showMessage('adminLoginMsg', 'Enter email and password.', 'error');
            return;
        }
        showLoading('adminLoginBtn', true);
        try {
            const data = await apiFetch('/auth/admin/login', {
                method: 'POST',
                body: JSON.stringify({ email, password })
            });
            setAuthState(data.user, data.access_token);
            window.location.href = 'admin.html';
        } catch (error) {
            showMessage('adminLoginMsg', handleApiError(error, 'Admin login failed.'), 'error');
        } finally {
            showLoading('adminLoginBtn', false);
        }
    };
    document.getElementById('adminLoginBtn').addEventListener('click', submit);
    document.getElementById('adminPassword').addEventListener('keydown', e => { if (e.key === 'Enter') submit(); });
});