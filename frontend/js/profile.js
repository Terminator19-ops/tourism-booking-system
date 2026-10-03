// Uses shared api.js for auth, API calls, and error handling

document.addEventListener('DOMContentLoaded', async () => {
    const user = await loadCurrentUser();
    if (!user) return;

    renderNavigation();

    document.getElementById('userFirstName').textContent = user.first_name;
    document.getElementById('userLastName').textContent = user.last_name;
    document.getElementById('userEmail').textContent = user.email;
    document.getElementById('userPhone').textContent = user.phone || 'N/A';
    document.getElementById('userRole').textContent = user.role;

    document.getElementById('editProfileBtn').addEventListener('click', () => {
        document.getElementById('editFirstName').value = user.first_name;
        document.getElementById('editLastName').value = user.last_name;
        document.getElementById('editPhone').value = user.phone || '';
        document.getElementById('editProfileForm').classList.remove('hidden');
    });

    document.getElementById('cancelEditBtn').addEventListener('click', () => {
        document.getElementById('editProfileForm').classList.add('hidden');
    });

    document.getElementById('saveProfileBtn').addEventListener('click', async () => {
        const firstName = document.getElementById('editFirstName').value.trim();
        const lastName = document.getElementById('editLastName').value.trim();
        const phone = document.getElementById('editPhone').value.trim();

        if (!firstName || !lastName || !phone) {
            showMessage('editMsg', 'First name, last name and phone are required.', 'error');
            return;
        }

        const btn = document.getElementById('saveProfileBtn');
        showLoading(btn, true);
        showMessage('editMsg', '', 'success');

        try {
            const data = await apiFetch('/auth/me', {
                method: 'PUT',
                body: JSON.stringify({ first_name: firstName, last_name: lastName, phone })
            });

            localStorage.setItem('user', JSON.stringify(data));
            showMessage('editMsg', 'Profile updated successfully!', 'success');
            document.getElementById('userFirstName').textContent = data.first_name;
            document.getElementById('userLastName').textContent = data.last_name;
            document.getElementById('userPhone').textContent = data.phone || 'N/A';
            setTimeout(() => document.getElementById('editProfileForm').classList.add('hidden'), 800);
        } catch (error) {
            showMessage('editMsg', handleApiError(error, 'Profile update failed.'), 'error');
        } finally {
            showLoading(btn, false);
        }
    });

    document.getElementById('changePwdBtn').addEventListener('click', async () => {
        const oldPwd = document.getElementById('oldPassword').value;
        const newPwd = document.getElementById('newPassword').value;
        const confPwd = document.getElementById('confirmPassword').value;

        if (!oldPwd || !newPwd || !confPwd) {
            showMessage('pwdMsg', 'All fields are required.', 'error');
            return;
        }

        if (newPwd !== confPwd) {
            showMessage('pwdMsg', 'New passwords do not match.', 'error');
            return;
        }

        if (newPwd.length < 8) {
            showMessage('pwdMsg', 'Password must be at least 8 characters.', 'error');
            return;
        }

        const btn = document.getElementById('changePwdBtn');
        showLoading(btn, true);
        showMessage('pwdMsg', '', 'success');

        try {
            await apiFetch('/auth/change-password', {
                method: 'PUT',
                body: JSON.stringify({ current_password: oldPwd, new_password: newPwd, confirm_password: confPwd })
            });

            showMessage('pwdMsg', 'Password changed successfully!', 'success');
            document.getElementById('oldPassword').value = '';
            document.getElementById('newPassword').value = '';
            document.getElementById('confirmPassword').value = '';
        } catch (error) {
            showMessage('pwdMsg', handleApiError(error, 'Password change failed.'), 'error');
        } finally {
            showLoading(btn, false);
        }
    });

    document.getElementById('logoutBtn').addEventListener('click', async () => {
        await logout();
    });
});

