import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL;

class AuthService {
    async login(username, password, remember = false) {
        try {
            const response = await axios.post(`${API_URL}/auth/login/`, {
                username,
                password
            });
            if (response.data.token) {
                const storage = remember ? localStorage : sessionStorage;
                storage.setItem('user', JSON.stringify(response.data));
            }
            return response.data;
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    }

    logout() {
        localStorage.removeItem('user');
        sessionStorage.removeItem('user');
    }

    async register(username, email, password, preferred_language) {
        try {
            const response = await axios.post(`${API_URL}/auth/register/`, {
                username,
                email,
                password,
                preferred_language
            });
            return response.data;
        } catch (error) {
            throw error.response?.data || { error: 'Registration failed' };
        }
    }

    getCurrentUser() {
        const user = localStorage.getItem('user') || sessionStorage.getItem('user');
        // console.log('User information from storage: ', user);
        return user ? JSON.parse(user) : null;
    }

    getToken() {
        const user = this.getCurrentUser();
        return user ? user.token : null;
    }

    async requestPasswordReset(email) {
        try {
            const response = await axios.post(`${API_URL}/auth/request-reset/`, { email });
            return response.data;
        } catch (error) {
            throw error.response?.data || { error: 'Failed to send reset email' };
        }
    }

    async resetPassword(uidb64, token, newPassword) {
        try {
            console.log("Resetting password with token: ", token)
            const response = await axios.post(`${API_URL}/auth/reset-password/${uidb64}/${token}/`, {
                token,
                new_password: newPassword
            });
            return response.data;
        } catch (error) {
            throw error.response?.data || { error: 'Failed to reset password' };
        }
    }

    setUser(userData, rememberMe = false) {
        const storage = rememberMe ? localStorage : sessionStorage;
        storage.setItem('user', JSON.stringify(userData));
    }
}

export default new AuthService(); 