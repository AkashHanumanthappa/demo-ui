#!/usr/bin/env node

/**
 * Storage Cleanup CLI Script
 *
 * This script helps clean up MongoDB storage to free up space.
 * Run this when you're experiencing storage quota issues.
 *
 * Usage:
 *   node scripts/cleanupStorage.js [options]
 *
 * Options:
 *   --stats              Show current storage statistics
 *   --cleanup            Perform automatic cleanup
 *   --orphaned           Clean up orphaned GridFS files
 *   --target=<percent>   Target usage percent after cleanup (default: 70)
 *   --help               Show help
 */

const dotenv = require('dotenv');
const mongoose = require('mongoose');
const path = require('path');

// Load environment variables from backend directory
dotenv.config({ path: path.join(__dirname, '../.env') });

const {
  getStorageStats,
  performAutoCleanup,
  cleanupOrphanedGridFSFiles
} = require('../utils/storageManager');

// Parse command line arguments
const args = process.argv.slice(2);
const options = {
  stats: args.includes('--stats'),
  cleanup: args.includes('--cleanup'),
  orphaned: args.includes('--orphaned'),
  help: args.includes('--help'),
  target: parseFloat(args.find(arg => arg.startsWith('--target='))?.split('=')[1]) || 0.70
};

// Show help
if (options.help || args.length === 0) {
  console.log(`
Storage Cleanup CLI Script

Usage:
  node scripts/cleanupStorage.js [options]

Options:
  --stats              Show current storage statistics
  --cleanup            Perform automatic cleanup
  --orphaned           Clean up orphaned GridFS files
  --target=<percent>   Target usage percent after cleanup (default: 0.70 = 70%)
  --help               Show this help message

Examples:
  node scripts/cleanupStorage.js --stats
  node scripts/cleanupStorage.js --cleanup
  node scripts/cleanupStorage.js --cleanup --target=0.60
  node scripts/cleanupStorage.js --orphaned
  node scripts/cleanupStorage.js --stats --cleanup --orphaned
  `);
  process.exit(0);
}

// Main function
async function main() {
  try {
    console.log('Connecting to MongoDB...');

    await mongoose.connect(process.env.MONGODB_URI);

    console.log('Connected to MongoDB successfully\n');

    // Show storage stats
    if (options.stats) {
      console.log('=== Storage Statistics ===');
      const stats = await getStorageStats();

      console.log(`Total Storage Used: ${stats.totalSizeMB} MB / ${stats.maxStorageMB} MB`);
      console.log(`Usage: ${stats.usagePercent}%`);
      console.log(`Available: ${stats.availableMB} MB`);
      console.log(`File Count: ${stats.fileCount}`);
      console.log(`Status: ${stats.status.toUpperCase()}`);

      if (stats.status === 'critical') {
        console.log('\n⚠️  WARNING: Storage is at critical level! Immediate cleanup recommended.');
      } else if (stats.status === 'high') {
        console.log('\n⚠️  WARNING: Storage usage is high. Cleanup recommended.');
      } else if (stats.status === 'warning') {
        console.log('\nℹ️  Storage usage is approaching limit. Consider cleanup.');
      }
      console.log('');
    }

    // Clean up orphaned files
    if (options.orphaned) {
      console.log('=== Cleaning Orphaned GridFS Files ===');
      const result = await cleanupOrphanedGridFSFiles();

      console.log(`✓ ${result.message}`);
      console.log(`  Deleted: ${result.deletedCount} files`);
      console.log(`  Freed: ${result.freedSizeMB} MB\n`);
    }

    // Perform cleanup
    if (options.cleanup) {
      console.log('=== Performing Automatic Cleanup ===');
      console.log(`Target usage: ${(options.target * 100).toFixed(0)}%\n`);

      const result = await performAutoCleanup(options.target);

      console.log(`✓ ${result.message}`);
      console.log(`  Files deleted: ${result.deletedFiles.length}`);
      console.log(`  Space freed: ${result.freedSizeMB} MB`);
      console.log(`  Initial usage: ${result.initialStats.usagePercent}%`);
      console.log(`  Final usage: ${result.finalStats.usagePercent}%`);
      console.log(`  Available now: ${result.finalStats.availableMB} MB\n`);

      if (result.deletedFiles.length > 0) {
        console.log('Deleted files:');
        result.deletedFiles.forEach(file => {
          console.log(`  - ${file.fileName} (${(file.deletedSize / 1024).toFixed(2)} KB)`);
        });
        console.log('');
      }
    }

    // Show final stats if any action was taken
    if (options.cleanup || options.orphaned) {
      console.log('=== Final Storage Statistics ===');
      const finalStats = await getStorageStats();

      console.log(`Total Storage Used: ${finalStats.totalSizeMB} MB / ${finalStats.maxStorageMB} MB`);
      console.log(`Usage: ${finalStats.usagePercent}%`);
      console.log(`Available: ${finalStats.availableMB} MB`);
      console.log(`File Count: ${finalStats.fileCount}`);
      console.log(`Status: ${finalStats.status.toUpperCase()}\n`);
    }

    console.log('✓ Done!');

  } catch (error) {
    console.error('\n❌ Error:', error.message);
    console.error('\nFull error:', error);
    process.exit(1);
  } finally {
    await mongoose.disconnect();
  }
}

// Run the script
main();
