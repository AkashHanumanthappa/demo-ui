const express = require('express');
const dotenv = require('dotenv');
const cors = require('cors');
const path = require('path');
const http = require('http');
const { Server } = require('socket.io');
const connectDB = require('./db/db');
const multer = require('multer');

// Load environment variables
dotenv.config();

// Initialize express app
const app = express();
const server = http.createServer(app);

// Initialize Socket.IO with CORS
const io = new Server(server, {
  cors: {
    origin: ['http://localhost:3000', 'http://localhost:4200', 'http://localhost:4201', 'http://localhost:4202'],
    methods: ['GET', 'POST'],
    credentials: true
  }
});

// Make io available globally for use in other modules
global.io = io;

// Socket.IO connection handling
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

// Connect to MongoDB
connectDB();

// Middleware
app.use(cors({
  origin: ['http://localhost:3000', 'http://localhost:4200', 'http://localhost:4201', 'http://localhost:4202'], // allow frontend ports
  credentials: true
}));

// Increase body parser limits
app.use(express.json({ limit: '200mb' }));
app.use(express.urlencoded({ limit: '200mb', extended: true }));

// Multer setup for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, 'uploads/'),
  filename: (req, file, cb) => cb(null, Date.now() + '-' + file.originalname)
});

const upload = multer({
  storage,
  limits: { fileSize: 200 * 1024 * 1024 } // 200MB
});

// Make `upload` available in routes
app.use((req, res, next) => {
  req.upload = upload;
  next();
});

// Request logging middleware
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
  next();
});

// Import routes
const userRoutes = require('./routes/userRoutes');
const fileRoutes = require('./routes/fileRoutes');

// API Routes
app.use('/api/users', userRoutes);
app.use('/api/files', fileRoutes);

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.status(200).json({
    success: true,
    message: 'Server is running',
    timestamp: new Date().toISOString()
  });
});

// Root endpoint
app.get('/', (req, res) => {
  res.status(200).json({
    success: true,
    message: 'Welcome to the File Processing API',
    version: '1.0.0',
    endpoints: {
      users: '/api/users',
      files: '/api/files',
      health: '/api/health'
    }
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    message: 'Route not found'
  });
});

// Global error handler
app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(err.status || 500).json({
    success: false,
    message: err.message || 'Internal server error',
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
  });
});

// Start server
const PORT = process.env.PORT || 5000;
server.listen(PORT, () => {
  console.log(`
TPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPW
Q   Server running on port ${PORT}                       Q
Q   Environment: ${process.env.NODE_ENV || 'development'}                     Q
Q   MongoDB: ${process.env.MONGODB_URI ? 'Connected' : 'Not configured'}                           Q
Q   WebSocket: Enabled                                   Q
ZPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP]
  `);
});

// Handle unhandled promise rejections
process.on('unhandledRejection', (err) => {
  console.error('Unhandled Promise Rejection:', err);
  process.exit(1);
});

module.exports = app;
