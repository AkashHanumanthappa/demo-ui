const mongoose = require('mongoose');
const dotenv = require('dotenv');
const readline = require('readline');
const User = require('../models/User');

// Load environment variables
dotenv.config();

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const question = (query) => new Promise((resolve) => rl.question(query, resolve));

const createAdmin = async () => {
  try {
    // Connect to MongoDB
    await mongoose.connect(process.env.MONGODB_URI, {
      useNewUrlParser: true,
      useUnifiedTopology: true,
    });

    console.log('Connected to MongoDB');
    console.log('\n=== Create Admin User ===\n');

    // Get admin details from user
    const username = await question('Enter admin username: ');
    const email = await question('Enter admin email: ');
    const password = await question('Enter admin password: ');

    // Validate input
    if (!username || !email || !password) {
      console.error('\nError: All fields are required');
      process.exit(1);
    }

    // Check if user already exists
    const existingUser = await User.findOne({
      $or: [{ email }, { username }]
    });

    if (existingUser) {
      console.error('\nError: User with this email or username already exists');
      process.exit(1);
    }

    // Create admin user
    const admin = await User.create({
      username,
      email,
      password,
      role: 'admin'
    });

    console.log('\n✓ Admin user created successfully!');
    console.log('\nAdmin Details:');
    console.log('- Username:', admin.username);
    console.log('- Email:', admin.email);
    console.log('- Role:', admin.role);
    console.log('- ID:', admin._id);

    process.exit(0);
  } catch (error) {
    console.error('\nError creating admin user:', error.message);
    process.exit(1);
  } finally {
    rl.close();
  }
};

createAdmin();
