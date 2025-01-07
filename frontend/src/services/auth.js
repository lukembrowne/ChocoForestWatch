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
        const response = await axios.post(`${API_URL}/auth/register/`, {
            username,
            email,
            password,
            preferred_language
        });
        return response.data;
    }

    getCurrentUser() {
        const user = localStorage.getItem('user') || sessionStorage.getItem('user');
        // console.log('User information: ', user)
        return user ? JSON.parse(user) : null;
    }

    getToken() {
        const user = this.getCurrentUser();
        return user ? user.token : null;
    }
}

export default new AuthService(); 