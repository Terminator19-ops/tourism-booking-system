document.addEventListener('DOMContentLoaded', () => {
    const user = JSON.parse(localStorage.getItem('user'));
    if (!user) { window.location.href = 'login.html'; return; }

    // Populate
    function refreshDisplay() {
        const u = JSON.parse(localStorage.getItem('user'));
        document.getElementById('userName').textContent  = u.name;
        document.getElementById('userEmail').textContent = u.email;
    }
    refreshDisplay();

    // Edit profile toggle
    document.getElementById('editProfileBtn').addEventListener('click', () => {
        document.getElementById('editName').value = JSON.parse(localStorage.getItem('user')).name;
        document.getElementById('editProfileForm').classList.toggle('hidden');
    });
    document.getElementById('cancelEditBtn').addEventListener('click', () => {
        document.getElementById('editProfileForm').classList.add('hidden');
    });
    document.getElementById('saveProfileBtn').addEventListener('click', () => {
        const name = document.getElementById('editName').value.trim();
        const editMsg = document.getElementById('editMsg');
        if (!name) { editMsg.textContent = 'Name cannot be empty.'; editMsg.className = 'msg-error'; return; }

        const u = JSON.parse(localStorage.getItem('user'));
        u.name = name;
        localStorage.setItem('user', JSON.stringify(u));

        editMsg.textContent = 'Profile updated!';
        editMsg.className = 'msg-success';
        refreshDisplay();
        setTimeout(() => document.getElementById('editProfileForm').classList.add('hidden'), 800);
    });

    // Change password
    document.getElementById('changePwdBtn').addEventListener('click', () => {
        const oldPwd  = document.getElementById('oldPassword').value;
        const newPwd  = document.getElementById('newPassword').value;
        const confPwd = document.getElementById('confirmPassword').value;
        const pwdMsg  = document.getElementById('pwdMsg');

        if (!oldPwd || !newPwd || !confPwd) {
            pwdMsg.textContent = 'All fields are required.'; pwdMsg.className = 'msg-error'; return;
        }

        // Check against stored users array (mock)
        const u = JSON.parse(localStorage.getItem('user'));
        const users = JSON.parse(localStorage.getItem('users') || '[]');
        const stored = users.find(x => x.email === u.email);

        if (stored && stored.password !== oldPwd) {
            pwdMsg.textContent = 'Current password is incorrect.'; pwdMsg.className = 'msg-error'; return;
        }
        if (newPwd !== confPwd) {
            pwdMsg.textContent = 'New passwords do not match.'; pwdMsg.className = 'msg-error'; return;
        }
        if (newPwd.length < 4) {
            pwdMsg.textContent = 'Password must be at least 4 characters.'; pwdMsg.className = 'msg-error'; return;
        }

        // Update in users store if registered
        if (stored) {
            stored.password = newPwd;
            localStorage.setItem('users', JSON.stringify(users));
        }

        pwdMsg.textContent = 'Password changed successfully!';
        pwdMsg.className = 'msg-success';
        document.getElementById('oldPassword').value  = '';
        document.getElementById('newPassword').value  = '';
        document.getElementById('confirmPassword').value = '';
    });

    // Logout
    document.getElementById('logoutBtn').addEventListener('click', () => {
        localStorage.removeItem('user');
        window.location.href = 'login.html';
    });
});

