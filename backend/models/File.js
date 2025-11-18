const mongoose = require('mongoose');

const fileSchema = new mongoose.Schema({
  originalName: {
    type: String,
    required: true
  },
  fileName: {
    type: String,
    required: true
  },
  filePath: {
    type: String,
    required: true
  },
  fileType: {
    type: String,
    enum: ['pdf', 'epub'],
    required: true
  },
  fileSize: {
    type: Number,
    required: true
  },
  mimeType: {
    type: String,
    required: true
  },
  uploadedBy: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  status: {
    type: String,
    enum: ['uploaded', 'processing', 'completed', 'failed'],
    default: 'uploaded'
  },
  processingStartedAt: {
    type: Date
  },
  processingCompletedAt: {
    type: Date
  },
  outputPath: {
    type: String
  },
  outputFiles: [{
    fileName: String,
    filePath: String,  // Deprecated - kept for backward compatibility
    fileType: String,
    fileSize: Number,
    gridfsFileId: mongoose.Schema.Types.ObjectId,  // GridFS file reference
    storedInGridFS: {
      type: Boolean,
      default: false
    }
  }],
  errorMessage: {
    type: String
  },
  conversionMetadata: {
    conversionType: String,
    outputFormats: [String],
    processingTime: Number
  }
}, {
  timestamps: true
});

// Index for faster queries
fileSchema.index({ uploadedBy: 1, createdAt: -1 });
fileSchema.index({ status: 1 });

// Method to update processing status
fileSchema.methods.updateStatus = function(status, additionalData = {}) {
  this.status = status;

  if (status === 'processing') {
    this.processingStartedAt = new Date();
  } else if (status === 'completed') {
    this.processingCompletedAt = new Date();
    if (this.processingStartedAt) {
      const processingTime = (this.processingCompletedAt - this.processingStartedAt) / 1000;
      this.conversionMetadata = {
        ...this.conversionMetadata,
        processingTime
      };
    }
  }

  Object.assign(this, additionalData);
  return this.save();
};

module.exports = mongoose.model('File', fileSchema);
