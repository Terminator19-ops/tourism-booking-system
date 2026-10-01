document.addEventListener('DOMContentLoaded', () => {
    // If already logged in, skip to dashboard
    if (localStorage.getItem('user')) {
        window.location.href = 'dashboard.html';
        return;
    }

    const loginSection    = document.getElementById('loginSection');
    const registerSection = document.getElementById('registerSection');
    const loginMsg        = document.getElementById('loginMsg');
    const registerMsg     = document.getElementById('registerMsg');

    document.getElementById('showRegister').addEventListener('click', e => {
        e.preventDefault();
        loginSection.classList.add('hidden');
        registerSection.classList.remove('hidden');
    });

    document.getElementById('showLogin').addEventListener('click', e => {
        e.preventDefault();
        registerSection.classList.add('hidden');
        loginSection.classList.remove('hidden');
    });

    document.getElementById('loginBtn').addEventListener('click', () => {
        const email    = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        if (!email || !password) {
            loginMsg.textContent = 'Please enter email and password.';
            loginMsg.className = 'msg-error';
            return;
        }

        // Check if user was registered in localStorage
        const users = JSON.parse(localStorage.getItem('users') || '[]');
        const found = users.find(u => u.email === email && u.password === password);

        if (found) {
            localStorage.setItem('user', JSON.stringify({ name: found.name, email: found.email }));
        } else if (email === 'admin@test.com' && password === 'admin') {
            // Default mock user
            localStorage.setItem('user', JSON.stringify({ name: 'Admin User', email: 'admin@test.com' }));
        } else {
            loginMsg.textContent = 'Invalid email or password.';
            loginMsg.className = 'msg-error';
            return;
        }

        window.location.href = 'dashboard.html';
    });

    document.getElementById('registerBtn').addEventListener('click', () => {
        const name     = document.getElementById('regName').value.trim();
        const email    = document.getElementById('regEmail').value.trim();
        const password = document.getElementById('regPassword').value;

        if (!name || !email || !password) {
            registerMsg.textContent = 'All fields are required.';
            registerMsg.className = 'msg-error';
            return;
        }

        const users = JSON.parse(localStorage.getItem('users') || '[]');
        if (users.find(u => u.email === email)) {
            registerMsg.textContent = 'Email already registered.';
            registerMsg.className = 'msg-error';
            return;
        }

        users.push({ name, email, password });
        localStorage.setItem('users', JSON.stringify(users));

        registerMsg.textContent = 'Registered successfully! Please log in.';
        registerMsg.className = 'msg-success';

        setTimeout(() => {
            registerSection.classList.add('hidden');
            loginSection.classList.remove('hidden');
        }, 1000);
    });
});

