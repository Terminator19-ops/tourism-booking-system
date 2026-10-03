const API_BASE = 'http://127.0.0.1:8000/api';

function getAuthToken() {
    return localStorage.getItem('authToken');
}

function getStoredUser() {
    const userStr = localStorage.getItem('user');
    if (userStr) {
        try {
            return JSON.parse(userStr);
        } catch {
            return null;
        }
    }
    return null;
}

function setAuthState(user, token) {
    localStorage.setItem('authToken', token);
    localStorage.setItem('user', JSON.stringify(user));
}

function clearAuthState() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
}

async function apiFetch(path, options = {}) {
    const token = getAuthToken();
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {})
    };
    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers
    });

    let data = null;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
        data = await response.json().catch(() => ({}));
    } else {
        data = await response.text().catch(() => ({}));
    }

    if (!response.ok) {
        const error = new Error(data?.detail || data?.message || `Request failed with status ${response.status}`);
        error.status = response.status;
        error.data = data;
        throw error;
    }

    return data;
}

function handleApiError(error, defaultMessage = 'An error occurred') {
    if (error.status === 401) {
        clearAuthState();
        window.location.href = 'login.html';
        return 'Please log in again.';
    }
    if (error.status === 403) {
        return 'You do not have permission to perform this action.';
    }
    if (error.status === 404) {
        return 'Requested item was not found.';
    }
    if (error.status === 409) {
        return 'That item already exists.';
    }
    if (error.status === 422 && error.data?.detail) {
        // Validation errors from FastAPI
        const details = error.data.detail;
        if (Array.isArray(details)) {
            return details.map(d => `${d.loc?.join('.') || 'field'}: ${d.msg}`).join('; ');
        }
        return error.data.detail;
    }
    return error.message || defaultMessage;
}

function showMessage(elementId, message, type = 'success') {
    const element = document.getElementById(elementId);
    if (!element) return;
    element.textContent = message;
    element.className = type === 'error' ? 'msg-error' : 'msg-success';
}

function showLoading(elementId, isLoading) {
    const element = document.getElementById(elementId);
    if (!element) return;
    if (isLoading) {
        element.classList.add('loading');
        element.disabled = true;
    } else {
        element.classList.remove('loading');
        element.disabled = false;
    }
}

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString();
    } catch {
        return dateStr;
    }
}

function formatDateTime(dateStr) {
    if (!dateStr) return 'N/A';
    try {
        const date = new Date(dateStr);
        return date.toLocaleString();
    } catch {
        return dateStr;
    }
}

function formatCurrency(amount) {
    if (amount === null || amount === undefined) return 'N/A';
    return `$${Number(amount).toFixed(2)}`;
}

function getRole() {
    const user = getStoredUser();
    return user?.role || null;
}

function requireRole(allowedRoles) {
    const role = getRole();
    if (!role || !allowedRoles.includes(role)) {
        window.location.href = 'login.html';
        return false;
    }
    return true;
}

function setupRoleNavigation() {
    const role = getRole();
    const adminNavLink = document.getElementById('adminNavLink');
    if (adminNavLink) {
        if (role === 'ADMIN') {
            adminNavLink.classList.remove('hidden');
        } else {
            adminNavLink.classList.add('hidden');
        }
    }
}

async function loadCurrentUser() {
    const token = getAuthToken();
    if (!token) {
        return null;
    }

    try {
        const response = await fetch(`${API_BASE}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` }
        });

        if (!response.ok) {
            clearAuthState();
            return null;
        }

        const user = await response.json();
        localStorage.setItem('user', JSON.stringify(user));
        return user;
    } catch (error) {
        console.error('Failed to load current user:', error);
        clearAuthState();
        return null;
    }
}

async function logout() {
    const token = getAuthToken();
    if (token) {
        try {
            await apiFetch('/auth/logout', { method: 'POST' });
        } catch (error) {
            console.warn('Logout API call failed:', error);
        }
    }
    clearAuthState();
    window.location.href = 'login.html';
}