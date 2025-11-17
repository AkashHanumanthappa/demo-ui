# File Processing Backend API

A robust backend API for handling user authentication and file processing with MongoDB, featuring PDF and EPUB conversion using RittDocConverter.

## Features

- **User Management**
  - Admin-only user creation
  - JWT-based authentication
  - Role-based access control (Admin/User)
  - Secure password hashing with bcrypt

- **File Processing**
  - Upload PDF and EPUB files
  - Automatic file validation
  - Integration with RittDocConverter for document conversion
  - Asynchronous file processing
  - Track processing status (uploaded, processing, completed, failed)
  - Download converted files

## Tech Stack

- **Node.js** with Express.js
- **MongoDB** with Mongoose ODM
- **JWT** for authentication
- **Multer** for file uploads
- **bcryptjs** for password hashing
- **RittDocConverter** for document conversion

## Setup Instructions

### Prerequisites

- Node.js (v14 or higher)
- MongoDB (local or MongoDB Atlas)
- Python 3 (for RittDocConverter)
- RittDocConverter repository cloned locally

### Installation

1. **Install dependencies:**
   ```bash
   cd backend
   npm install
   ```

2. **Set up RittDocConverter:**
   ```bash
   # Clone RittDocConverter repository
   git clone https://github.com/Zentrovia/RittDocConverter.git

   # Install Python dependencies (if required by RittDocConverter)
   cd RittDocConverter
   pip install -r requirements.txt
   cd ..
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and update the following:
   - `MONGODB_URI`: Your MongoDB connection string
   - `JWT_SECRET`: A strong secret key for JWT
   - `CONVERTER_SCRIPT_PATH`: Path to RittDocConverter's integrated_pipelines.py
   - `FRONTEND_URL`: Your frontend URL (for CORS)

4. **Start the server:**
   ```bash
   npm start
   ```

   For development with auto-reload:
   ```bash
   npm run dev
   ```

## API Endpoints

### Authentication & Users

#### POST /api/users/login
Login with email and password
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

#### POST /api/users (Admin Only)
Create a new user
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "password123",
  "role": "user"
}
```

#### GET /api/users (Admin Only)
Get all users

#### GET /api/users/me
Get current user profile

#### PUT /api/users/:id (Admin Only)
Update user details

#### DELETE /api/users/:id (Admin Only)
Delete a user

### File Management

All file endpoints require authentication (Bearer token in Authorization header)

#### POST /api/files/upload
Upload a PDF or EPUB file
- Content-Type: multipart/form-data
- Field name: `file`
- Allowed types: PDF, EPUB
- Max size: 500MB

#### GET /api/files
Get all files uploaded by current user

#### GET /api/files/all (Admin Only)
Get all files from all users

#### GET /api/files/:id
Get file details by ID

#### GET /api/files/:id/download/:fileName
Download a converted output file

#### DELETE /api/files/:id
Delete a file and its outputs

### Health Check

#### GET /api/health
Check server status

## File Processing Flow

1. User uploads a PDF or EPUB file via `/api/files/upload`
2. File is saved to the `uploads` directory
3. File record is created in MongoDB with status "uploaded"
4. Response is sent to user immediately
5. File processing starts asynchronously:
   - Status changes to "processing"
   - RittDocConverter's `integrated_pipelines.py` is executed
   - Output files are saved to `outputs/:fileId/` directory
   - Status changes to "completed" with output file info
6. User can download converted files via `/api/files/:id/download/:fileName`

## Project Structure

```
backend/
├── controllers/       # Request handlers
│   ├── userController.js
│   └── fileController.js
├── db/               # Database configuration
│   └── db.js
├── middleware/       # Express middleware
│   ├── auth.js       # Authentication & authorization
│   └── upload.js     # File upload configuration
├── models/           # Mongoose schemas
│   ├── User.js
│   └── File.js
├── routes/           # API routes
│   ├── userRoutes.js
│   └── fileRoutes.js
├── utils/            # Utility functions
│   └── docConverter.js
├── uploads/          # Uploaded files (gitignored)
├── outputs/          # Converted files (gitignored)
├── .env.example      # Environment variables template
├── .gitignore
├── package.json
└── server.js         # Main application file
```

## Creating the First Admin User

Since user creation is restricted to admins, you need to create the first admin manually in MongoDB:

```javascript
// Connect to MongoDB shell or use MongoDB Compass
use fileprocessing

// Insert first admin user (password will be "admin123" hashed)
db.users.insertOne({
  username: "admin",
  email: "admin@example.com",
  password: "$2a$10$YourHashedPasswordHere",  // Hash "admin123" with bcrypt
  role: "admin",
  createdAt: new Date(),
  updatedAt: new Date()
})
```

Or use the provided script:
```bash
npm run create-admin
```

## Security Notes

- Change `JWT_SECRET` in production
- Use HTTPS in production
- Set appropriate CORS policies
- Regularly update dependencies
- Never commit `.env` file
- Implement rate limiting for production

## Error Handling

The API returns consistent error responses:
```json
{
  "success": false,
  "message": "Error description",
  "error": "Detailed error message (dev only)"
}
```

## License

ISC
