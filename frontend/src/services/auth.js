import axios from 'axios';

const API_URL = 'http://localhost:8000/api/';

class AuthService {
    async login(username, password, remember = false) {
        const response = await axios.post(API_URL + 'auth/login/', {
            username,
            password
        });
        if (response.data.token) {
            const storage = remember ? localStorage : sessionStorage;
            storage.setItem('user', JSON.stringify(response.data));
        }
        return response.data;
    }

    logout() {
        localStorage.removeItem('user');
        sessionStorage.removeItem('user');
    }

    register(username, email, password) {
        return axios.post(API_URL + 'auth/register/', {
            username,
            email,
            password
        });
    }

    getCurrentUser() {
        const user = localStorage.getItem('user') || sessionStorage.getItem('user');
        return user ? JSON.parse(user) : null;
    }

    getToken() {
        const user = this.getCurrentUser();
        return user ? user.token : null;
    }
}

export default new AuthService(); 