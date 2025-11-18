/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        // R2Library-inspired professional blue theme (your existing colors - kept as is)
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',  // Main brand blue
          600: '#2563eb',  // Primary action color
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        secondary: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        },
        // Additional colors for status indicators
        accent: {
          teal: '#14b8a6',
          cyan: '#06b6d4',
        },
        // EXACT R2 Digital Library Navigation Colors (from image analysis)
        r2: {
          'nav-light': '#7b9ec4',    // Navigation gradient - top
          'nav-main': '#6890b8',     // Navigation gradient - middle
          'nav-dark': '#5882ab',     // Navigation gradient - bottom
          'tab-inactive': '#4f7299', // Inactive tab background
          'tab-active': '#5882ab',   // Active tab background
          'tab-border': '#3d5b7a',   // Tab border color
        },
        // R2 Digital Library slate blue navigation color (legacy - keep for compatibility)
        slate: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#6890b8',  // Updated to exact R2 main color
          700: '#4f7299',  // Updated to exact R2 tab color
          800: '#3d5b7a',  // Updated to exact R2 border color
          900: '#1e293b',
        },
        success: {
          50: '#f0fdf4',
          100: '#dcfce7',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
        },
        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
        },
        error: {
          50: '#fef2f2',
          100: '#fee2e2',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
        },
      },
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Arial', 'sans-serif'],
      },
      backgroundImage: {
        // Gradient backgrounds for sections
        'gradient-r2': 'linear-gradient(to bottom right, #f8fafc, #e0f2fe)',
        'gradient-blue': 'linear-gradient(to right, #2563eb, #1e40af)',
        'gradient-teal': 'linear-gradient(135deg, #2563eb, #14b8a6)',
        'gradient-download': 'linear-gradient(to bottom right, #eff6ff, #dbeafe)',
        'gradient-delete': 'linear-gradient(to bottom right, #fef2f2, #fee2e2)',
        // EXACT R2 Navigation Gradient
        'r2-nav': 'linear-gradient(180deg, #7b9ec4 0%, #6890b8 50%, #5882ab 100%)',
      },
      boxShadow: {
        // Your existing shadows
        'soft': '0 2px 8px rgba(0, 0, 0, 0.08)',
        'card': '0 1px 3px rgba(0, 0, 0, 0.1)',
        // New shadows for enhanced effects
        'card-hover': '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
        'glow-blue': '0 0 20px rgba(37, 99, 235, 0.3)',
        'glow-green': '0 0 20px rgba(16, 185, 129, 0.3)',
        'glow-yellow': '0 0 20px rgba(245, 158, 11, 0.3)',
        // R2 Tab shadows
        'r2-tab-inactive': 'inset 0 1px 2px rgba(255, 255, 255, 0.1)',
        'r2-tab-active': 'inset 0 2px 4px rgba(0, 0, 0, 0.2), 0 2px 4px rgba(0, 0, 0, 0.1)',
      },
      animation: {
        // Custom animations for manuscript tracking
        'pulse-glow': 'pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-in': 'slide-in 0.3s ease-out',
        'progress-bar': 'progress-bar 2s linear infinite',
        'spin-slow': 'spin 0.8s linear infinite',
        'status-pulse': 'status-pulse 2s ease-in-out infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        'slide-in': {
          from: {
            opacity: '0',
            transform: 'translateY(10px)',
          },
          to: {
            opacity: '1',
            transform: 'translateY(0)',
          },
        },
        'progress-bar': {
          '0%': { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '50px 50px' },
        },
        'status-pulse': {
          '0%, 100%': {
            transform: 'scale(1)',
            opacity: '1',
          },
          '50%': {
            transform: 'scale(1.1)',
            opacity: '0.8',
          },
        },
      },
      transitionProperty: {
        'height': 'height',
        'spacing': 'margin, padding',
      },
    },
  },
  plugins: [
    function({ addUtilities }) {
      const newUtilities = {
        // Custom scrollbar styling
        '.scrollbar-thin': {
          'scrollbar-width': 'thin',
          'scrollbar-color': '#cbd5e1 #f1f5f9',
        },
        '.scrollbar-webkit': {
          '&::-webkit-scrollbar': {
            width: '8px',
            height: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: '#f1f5f9',
            borderRadius: '4px',
          },
          '&::-webkit-scrollbar-thumb': {
            background: '#cbd5e1',
            borderRadius: '4px',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: '#94a3b8',
          },
        },
        // Progress bar with stripes
        '.progress-bar-striped': {
          backgroundImage: 'linear-gradient(45deg, rgba(255, 255, 255, 0.15) 25%, transparent 25%, transparent 50%, rgba(255, 255, 255, 0.15) 50%, rgba(255, 255, 255, 0.15) 75%, transparent 75%, transparent)',
          backgroundSize: '50px 50px',
        },
        // Gradient text effect
        '.text-gradient': {
          background: 'linear-gradient(135deg, #2563eb, #14b8a6)',
          '-webkit-background-clip': 'text',
          '-webkit-text-fill-color': 'transparent',
          'background-clip': 'text',
        },
        // Card hover effect
        '.card-hover': {
          transition: 'all 0.3s ease',
          '&:hover': {
            boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
            transform: 'translateY(-2px)',
          },
        },
        // R2 Tab button styles
        '.r2-tab': {
          padding: '10px 24px',
          borderRadius: '0.375rem',
          fontWeight: '600',
          color: '#ffffff',
          transition: 'all 0.2s ease',
        },
        '.r2-tab-inactive': {
          backgroundColor: '#4f7299',
          border: '2px solid #3d5b7a',
          boxShadow: 'inset 0 1px 2px rgba(255, 255, 255, 0.1)',
        },
        '.r2-tab-active': {
          backgroundColor: '#5882ab',
          border: '2px solid #3d5b7a',
          boxShadow: 'inset 0 2px 4px rgba(0, 0, 0, 0.2), 0 2px 4px rgba(0, 0, 0, 0.1)',
        },
      }
      addUtilities(newUtilities)
    },
  ],
};