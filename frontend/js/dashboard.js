document.addEventListener('DOMContentLoaded', () => {
    const user = JSON.parse(localStorage.getItem('user'));
    if (!user) { window.location.href = 'login.html'; return; }

    document.getElementById('welcomeMessage').textContent = `Welcome, ${user.name}!`;

    document.getElementById('logoutBtn').addEventListener('click', () => {
        localStorage.removeItem('user');
        window.location.href = 'login.html';
    });
});

