// auth.js - Authentication helper functions

class AuthService {
    // Check if user is authenticated
    static isAuthenticated() {
        const token = localStorage.getItem('token');
        return !!token;
    }
    
    // Get current user
    static getCurrentUser() {
        const userStr = localStorage.getItem('user');
        if (userStr) {
            try {
                return JSON.parse(userStr);
            } catch (e) {
                return null;
            }
        }
        return null;
    }
    
    // Get authentication token
    static getToken() {
        return localStorage.getItem('token');
    }
    
    // Logout user
    static logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = 'login.html';
    }
    
    // Redirect to login if not authenticated
    static requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = 'login.html';
            return false;
        }
        return true;
    }
    
    // Make authenticated API request
    static async authenticatedFetch(url, options = {}) {
        const token = this.getToken();
        
        if (!token) {
            throw new Error('No authentication token found');
        }
        
        // Add token to headers
        const headers = {
            ...options.headers,
            'Authorization': `Bearer ${token}`
        };
        
        // For FormData requests, add token as form field
        if (options.body instanceof FormData) {
            options.body.append('token', token);
            return await fetch(url, options);
        } else {
            // For JSON requests
            return await fetch(url, {
                ...options,
                headers
            });
        }
    }
    
    // Check user type
    static isJobSeeker() {
        const user = this.getCurrentUser();
        return user && user.user_type === 'job_seeker';
    }
    
    static isEmployer() {
        const user = this.getCurrentUser();
        return user && user.user_type === 'employer';
    }
}

// Load this script in all dashboard pages
if (window.location.pathname.includes('dashboard') || 
    window.location.pathname.includes('recruiters')) {
    
    document.addEventListener('DOMContentLoaded', function() {
        // Check authentication on dashboard pages
        if (!AuthService.isAuthenticated()) {
            window.location.href = 'login.html';
            return;
        }
        
        const user = AuthService.getCurrentUser();
        
        // Display user info
        const userInfoElements = document.querySelectorAll('.user-name, .user-email');
        userInfoElements.forEach(el => {
            if (el.classList.contains('user-name')) {
                el.textContent = `${user.first_name} ${user.last_name}`;
            } else if (el.classList.contains('user-email')) {
                el.textContent = user.email;
            }
        });
        
        // Add logout functionality
        const logoutButtons = document.querySelectorAll('.logout-btn, #logoutBtn');
        logoutButtons.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                AuthService.logout();
            });
        });
    });
}