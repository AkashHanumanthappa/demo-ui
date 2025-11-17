# Manuscript Processor

A full-stack application for processing and converting manuscript files (PDF/EPUB) with user authentication and role-based access control.

## Features

- **User Authentication**: JWT-based authentication with role-based access control
- **File Upload & Processing**: Upload PDF and EPUB files (up to 500MB) for processing
- **File Management**: View, download, and delete processed manuscripts
- **Admin Panel**: User management and system monitoring for administrators
- **Real-time Status**: Track file processing status in real-time
- **Multiple Output Formats**: Download processed files in various formats

## Tech Stack

### Backend
- Node.js with Express 5.1.0
- MongoDB with Mongoose 8.19.4
- JWT authentication
- Multer for file uploads
- Python integration for file conversion

### Frontend
- React 18.3.1
- React Router DOM 6.28.0
- Axios for API calls
- TailwindCSS for styling
- Vite for build tooling

## Prerequisites

- Node.js (v16 or higher)
- MongoDB (v5.0 or higher)
- Python 3.x (for file conversion)
- npm or yarn

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd demo-ui
```

### 2. Backend Setup

```bash
cd backend

# Install dependencies
npm install

# Create environment file
cp .env.example .env

# Edit .env file with your configuration
# Important: Change JWT_SECRET to a secure random string
# Update MONGODB_URI if using a different MongoDB connection

# Start MongoDB (if running locally)
# mongod

# Run the backend server
npm start
```

The backend will start on http://localhost:5000

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create environment file
cp .env.example .env

# The default configuration points to http://localhost:5000/api
# Update VITE_API_URL if your backend runs on a different URL

# Start the development server
npm run dev
```

The frontend will start on http://localhost:3000

## Initial Setup

### Create Admin User

Since user registration requires admin privileges, you need to create an initial admin user directly in MongoDB:

```javascript
// Connect to MongoDB
mongosh

// Switch to the database
use manuscript-processor

// Create admin user (update the values as needed)
db.users.insertOne({
  username: "admin",
  email: "admin@example.com",
  password: "$2a$10$YourHashedPasswordHere", // Use bcrypt to hash your password
  role: "admin",
  createdAt: new Date(),
  updatedAt: new Date()
})
```

### Hash a Password

To generate a bcrypt hash for the password:

```bash
cd backend
node -e "const bcrypt = require('bcryptjs'); console.log(bcrypt.hashSync('your-password', 10));"
```

## Environment Variables

### Backend (.env)

```env
PORT=5000                                           # Server port
NODE_ENV=development                                # Environment
MONGODB_URI=mongodb://localhost:27017/manuscript-processor  # MongoDB connection
JWT_SECRET=your-super-secret-jwt-key               # JWT secret key
FRONTEND_URL=http://localhost:3000                 # Frontend URL for CORS
MAX_FILE_SIZE=524288000                            # Max file size (500MB)
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:5000/api            # Backend API URL
```

## API Endpoints

### Authentication
- `POST /api/users/login` - User login
- `GET /api/users/me` - Get current user profile

### Files (Authenticated)
- `POST /api/files/upload` - Upload and process file
- `GET /api/files` - Get user's files
- `GET /api/files/:id` - Get specific file
- `GET /api/files/:id/download/:fileName` - Download output file
- `DELETE /api/files/:id` - Delete file

### Admin (Admin Only)
- `POST /api/users` - Create new user
- `GET /api/users` - Get all users
- `PUT /api/users/:id` - Update user
- `DELETE /api/users/:id` - Delete user
- `GET /api/files/all` - Get all files

### System
- `GET /api/health` - Health check

## Usage

### Login

1. Navigate to http://localhost:3000
2. Enter your credentials
3. Click "Sign in"

### Upload a Manuscript

1. After logging in, go to the Manuscripts page
2. Click "Upload Manuscript"
3. Select a PDF or EPUB file (max 500MB)
4. Wait for processing to complete

### Download Processed Files

1. Once processing is complete, the status will change to "completed"
2. Click on the file format buttons to download the processed files

### Admin Functions

If you're logged in as an admin:

1. Access the Admin panel from the navigation
2. Manage users (create, update, delete)
3. View all manuscripts across all users
4. Monitor system health

## File Structure

```
demo-ui/
├── backend/
│   ├── middleware/          # Authentication and upload middleware
│   ├── models/             # MongoDB models (User, File)
│   ├── routes/             # API routes
│   ├── db/                 # Database connection
│   ├── uploads/            # Uploaded files (temporary)
│   ├── outputs/            # Processed files
│   ├── server.js           # Main server file
│   └── .env.example        # Environment variables template
│
└── frontend/
    ├── src/
    │   ├── components/     # Reusable UI components
    │   ├── contexts/       # React contexts (Auth, Notifications)
    │   ├── hooks/          # Custom React hooks
    │   ├── pages/          # Page components
    │   ├── utils/          # Utility functions (API client)
    │   ├── config/         # Configuration files
    │   └── App.jsx         # Main App component
    ├── .env.example        # Environment variables template
    └── vite.config.js      # Vite configuration
```

## Security Notes

- **JWT Secret**: Always use a strong, random secret in production
- **CORS**: Configure FRONTEND_URL properly to restrict cross-origin requests
- **File Upload**: The application accepts only PDF and EPUB files
- **Authentication**: All file operations require authentication
- **Role-Based Access**: Admin operations are restricted to admin users only

## Troubleshooting

### Backend won't start
- Check if MongoDB is running
- Verify .env configuration
- Check if port 5000 is available

### Frontend can't connect to backend
- Verify backend is running on http://localhost:5000
- Check VITE_API_URL in frontend/.env
- Check browser console for CORS errors

### File upload fails
- Check file size (must be under 500MB)
- Verify file type (PDF or EPUB only)
- Check backend logs for errors
- Ensure uploads/ directory exists and is writable

### Authentication issues
- Clear browser localStorage
- Check JWT_SECRET is set in backend/.env
- Verify user exists in database

## Development

### Running in Development Mode

Both backend and frontend support hot reloading in development mode.

Backend:
```bash
cd backend
npm run dev  # Uses nodemon for auto-restart
```

Frontend:
```bash
cd frontend
npm run dev  # Vite dev server with HMR
```

### Building for Production

Frontend:
```bash
cd frontend
npm run build
npm run preview  # Preview production build
```

Backend:
```bash
cd backend
NODE_ENV=production npm start
```

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please open an issue on GitHub.