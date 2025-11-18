const mongoose = require('mongoose');
const { initGridFS } = require('../utils/gridfs');

const connectDB = async () => {
  try {
    const conn = await mongoose.connect(process.env.MONGODB_URI, {
      useNewUrlParser: true,
      useUnifiedTopology: true,
    });

    console.log(`MongoDB Connected: ${conn.connection.host}`);
    console.log(`Database Name: ${conn.connection.name}`);

    // Initialize GridFS after connection is established
    mongoose.connection.once('open', () => {
      initGridFS();
      console.log('GridFS initialized successfully');
    });

  } catch (error) {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  }
};

module.exports = connectDB;