// API base URL with fallback to local development server
export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8000/api';
export const API_ROOT_URL = process.env.REACT_APP_API_ROOT_URL || 'http://127.0.0.1:8000';

export const CONFIG = {
  apiBaseUrl: API_BASE_URL,
  apiRootUrl: API_ROOT_URL,
};

// Export a default config object
export default CONFIG;