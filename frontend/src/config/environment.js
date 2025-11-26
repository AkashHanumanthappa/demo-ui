// Environment configuration
const environment = {
  production: import.meta.env.PROD,
  apiUrl: import.meta.env.VITE_API_URL || 'https://demo-ui-32dt.onrender.com/api',
  isStatic: false,
};

export default environment;
