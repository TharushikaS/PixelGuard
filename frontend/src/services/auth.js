// Authentication service

const AUTH_TOKEN_KEY = 'pixelguard_token';
const USER_KEY = 'pixelguard_user';

export const authService = {
  // Set authentication token
  setToken: (token) => {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  },

  // Get authentication token
  getToken: () => {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  },

  // Remove authentication token
  removeToken: () => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  },

  // Set user info
  setUser: (user) => {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },

  // Get user info
  getUser: () => {
    const user = localStorage.getItem(USER_KEY);
    return user ? JSON.parse(user) : null;
  },

  // Clear all auth data
  logout: () => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },

  // Check if user is authenticated
  isAuthenticated: () => {
    return !!localStorage.getItem(AUTH_TOKEN_KEY);
  },
};

export default authService;
