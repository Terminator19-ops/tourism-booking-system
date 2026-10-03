// Uses shared api.js for auth, error handling, and API calls

document.addEventListener('DOMContentLoaded', async () => {
    const existingToken = localStorage.getItem('authToken');
    if (existingToken) {
        try {
            const response = await fetch(`${API_BASE}/auth/me`, {
                headers: { Authorization: `Bearer ${existingToken}` }
            });
            if (response.ok) {
                const user = await response.json();
                localStorage.setItem('user', JSON.stringify(user));
                if (user.role === 'ADMIN') {
                    window.location.href = 'admin.html';
                } else if (user.role === 'OWNER') {
                    window.location.href = 'owner.html';
                } else {
                    window.location.href = 'dashboard.html';
                }
                return;
            }
        } catch (error) {
            console.warn(error);
        }
        clearAuthState();
    }

    const loginSection = document.getElementById('loginSection');
    const registerSection = document.getElementById('registerSection');
    const registerTitle = document.getElementById('registerTitle');
    let registrationRole = 'CUSTOMER';

    function showRegister(role) {
        registrationRole = role;
        registerTitle.textContent = role === 'CUSTOMER' ? 'Register as Customer' : 'Register as Owner';
        loginSection.classList.add('hidden');
        registerSection.classList.remove('hidden');
    }

    document.getElementById('registerCustomerBtn').addEventListener('click', () => showRegister('CUSTOMER'));
    document.getElementById('registerOwnerBtn').addEventListener('click', () => showRegister('OWNER'));

    document.getElementById('showLogin').addEventListener('click', e => {
        e.preventDefault();
        registerSection.classList.add('hidden');
        loginSection.classList.remove('hidden');
    });

    document.getElementById('loginBtn').addEventListener('click', async () => {
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        const role = document.getElementById('loginRole').value;

        if (!email || !password) {
            showMessage('loginMsg', 'Please enter email and password.', 'error');
            return;
        }

        const btn = document.getElementById('loginBtn');
        showLoading(btn, true);
        showMessage('loginMsg', '', 'success');

        try {
            const data = await apiFetch('/auth/login', {
                method: 'POST',
                body: JSON.stringify({ email, password, role })
            });

            setAuthState(data.user, data.access_token);
            window.location.href = data.user.role === 'ADMIN' ? 'admin.html' : 
                                   data.user.role === 'OWNER' ? 'owner.html' : 'dashboard.html';
        } catch (error) {
            showMessage('loginMsg', handleApiError(error, 'Login failed.'), 'error');
        } finally {
            showLoading(btn, false);
        }
    });

    document.getElementById('registerBtn').addEventListener('click', async () => {
        const firstName = document.getElementById('regFirstName').value.trim();
        const lastName = document.getElementById('regLastName').value.trim();
        const email = document.getElementById('regEmail').value.trim();
        const phone = document.getElementById('regPhone').value.trim();
        const password = document.getElementById('regPassword').value;

        if (!firstName || !lastName || !email || !phone || !password) {
            showMessage('registerMsg', 'All fields are required.', 'error');
            return;
        }

        const btn = document.getElementById('registerBtn');
        showLoading(btn, true);
        showMessage('registerMsg', '', 'success');

        try {
            const endpoint = registrationRole === 'CUSTOMER' ? '/auth/register/customer' : '/auth/register/owner';
            const data = await apiFetch(endpoint, {
                method: 'POST',
                body: JSON.stringify({ first_name: firstName, last_name: lastName, email, phone, password })
            });

            setAuthState(data.user, data.access_token);
            showMessage('registerMsg', 'Registration successful. Redirecting...', 'success');
            window.location.href = data.user.role === 'ADMIN' ? 'admin.html' : 
                                   data.user.role === 'OWNER' ? 'owner.html' : 'dashboard.html';
        } catch (error) {
            showMessage('registerMsg', handleApiError(error, 'Registration failed.'), 'error');
        } finally {
            showLoading(btn, false);
        }
    });
});

