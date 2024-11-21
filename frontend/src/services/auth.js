import axios from 'axios';

const API_URL = 'http://localhost:8000/api/';

class AuthService {
    async login(username, password) {
        const response = await axios.post(API_URL + 'auth/login/', {
            username,
            password
        });
        if (response.data.token) {
            localStorage.setItem('user', JSON.stringify(response.data));
        }
        return response.data;
    }

    logout() {
        localStorage.removeItem('user');
    }

    register(username, email, password) {
        return axios.post(API_URL + 'auth/register/', {
            username,
            email,
            password
        });
    }

    getCurrentUser() {
        return JSON.parse(localStorage.getItem('user'));
    }

    getToken() {
        const user = this.getCurrentUser();
        return user ? user.token : null;
    }
}

export default new AuthService(); 