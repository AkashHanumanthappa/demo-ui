// Environment configuration
const environment = {
  production: import.meta.env.PROD,
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:5000/api',
  isStatic: false,
};

export default environment;
