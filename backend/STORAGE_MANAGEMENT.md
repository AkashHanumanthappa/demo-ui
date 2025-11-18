# Storage Management Guide

## Overview

This application uses MongoDB GridFS for file storage. MongoDB Atlas free tier has a 512 MB storage limit. This guide explains how to manage storage quota effectively.

## Quick Fix for "Storage Quota Exceeded" Error

If you're seeing the error `MongoServerError: you are over your space quota`, run the cleanup script immediately:

```bash
cd backend
node scripts/cleanupStorage.js --stats --cleanup --orphaned
```

This will:
1. Show current storage statistics
2. Clean up orphaned GridFS files (files not referenced in the database)
3. Delete old/failed files to free up space

## Storage Management Features

### 1. Automatic Quota Checking

The system now automatically checks storage availability before:
- Uploading new files
- Converting and storing output files

If storage is critical (>95% used), uploads will be blocked with a helpful error message.

### 2. Automatic Cleanup

When storage usage reaches 90%, the system automatically triggers background cleanup to delete:
- Failed conversions
- Files stuck in "processing" status for >30 days
- Old uploaded files that were never processed (>30 days)

### 3. Storage Status Levels

| Status | Usage | Action |
|--------|-------|--------|
| Normal | <85% | No action needed |
| Warning | 85-90% | Consider cleanup |
| High | 90-95% | Automatic cleanup triggered |
| Critical | >95% | New uploads blocked |

## CLI Script Usage

### View Storage Statistics

```bash
node scripts/cleanupStorage.js --stats
```

Output example:
```
Total Storage Used: 485.23 MB / 512.00 MB
Usage: 94.77%
Available: 26.77 MB
File Count: 156
Status: HIGH
```

### Perform Automatic Cleanup

```bash
node scripts/cleanupStorage.js --cleanup
```

This will clean up files until usage reaches 70% (default target).

To set a custom target (e.g., 60%):
```bash
node scripts/cleanupStorage.js --cleanup --target=0.60
```

### Clean Orphaned GridFS Files

Over time, GridFS files may become orphaned (not referenced in the database). Clean them up:

```bash
node scripts/cleanupStorage.js --orphaned
```

### Combine Operations

```bash
node scripts/cleanupStorage.js --stats --orphaned --cleanup
```

## Admin API Endpoints

All storage management endpoints require admin authentication.

### Get Storage Statistics

```http
GET /api/storage/stats
Authorization: Bearer <admin-token>
```

Response:
```json
{
  "success": true,
  "data": {
    "stats": {
      "totalSizeMB": "485.23",
      "maxStorageMB": "512.00",
      "usagePercent": "94.77",
      "fileCount": 156,
      "availableMB": "26.77",
      "status": "high"
    }
  }
}
```

### Get Storage Report

```http
GET /api/storage/report
Authorization: Bearer <admin-token>
```

Returns detailed statistics including:
- Overall storage stats
- File counts by status (uploaded, processing, completed, failed)
- File counts by user (top 10 users by storage)
- File counts by type

### Get Cleanup Candidates

```http
GET /api/storage/cleanup-candidates
Authorization: Bearer <admin-token>
```

Returns list of files recommended for deletion:
- Failed conversions
- Stuck processing files
- Old unprocessed files

### Get Oldest Files

```http
GET /api/storage/oldest-files?limit=50
Authorization: Bearer <admin-token>
```

Returns the oldest files (by creation date).

### Perform Cleanup

```http
POST /api/storage/cleanup
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "targetPercent": 0.70
}
```

Performs automatic cleanup to reach target usage (default: 70%).

### Clean Orphaned Files

```http
POST /api/storage/cleanup-orphaned
Authorization: Bearer <admin-token>
```

Removes GridFS files not referenced in the database.

### Delete Multiple Files

```http
DELETE /api/storage/files
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "fileIds": ["file_id_1", "file_id_2", "file_id_3"]
}
```

Deletes specific files by ID.

## User Error Handling

### Upload Blocked Due to Quota

When a user tries to upload but storage is critical, they receive:

```json
{
  "success": false,
  "message": "Storage quota critical. Please delete old files or contact administrator.",
  "quotaExceeded": true,
  "storageStats": {
    "usagePercent": "96.5",
    "availableMB": "17.9"
  }
}
```

HTTP Status Code: `507 Insufficient Storage`

### During Processing

If storage quota is exceeded during file processing, the file status is marked as "failed" with an appropriate error message.

## Best Practices

### For Users

1. **Delete old files**: Regularly delete files you no longer need using the DELETE endpoint
2. **Check file status**: Files stuck in "processing" or "failed" status can be safely deleted
3. **Download results promptly**: Download your converted files and then delete them

### For Administrators

1. **Monitor storage regularly**: Check `/api/storage/stats` or run the CLI script weekly
2. **Set up automated cleanup**: Consider running the cleanup script as a cron job
3. **Review cleanup candidates**: Use `/api/storage/cleanup-candidates` to see what will be deleted
4. **Clean orphaned files**: Run orphaned cleanup monthly

### Automated Cleanup (Cron Job)

Add to your server's crontab to run cleanup weekly:

```cron
# Run storage cleanup every Sunday at 2 AM
0 2 * * 0 cd /path/to/backend && node scripts/cleanupStorage.js --cleanup --orphaned >> /var/log/storage-cleanup.log 2>&1
```

## Cleanup Strategy

The automatic cleanup follows this priority:

1. **Phase 1: Failed and Orphaned Files**
   - Files with status "failed"
   - Files stuck in "uploaded" for >30 days
   - Files stuck in "processing" for >30 days
   - Orphaned GridFS files

2. **Phase 2: Oldest Completed Files** (if more space needed)
   - Deletes oldest files by creation date
   - Only if Phase 1 didn't free enough space

## Monitoring and Alerts

Consider setting up monitoring for:
- Storage usage percentage
- Number of files in "failed" status
- Number of orphaned GridFS files
- Available storage space

## Troubleshooting

### "Storage quota exceeded" during upload

**Solution**: Run cleanup script or delete old files
```bash
node scripts/cleanupStorage.js --cleanup
```

### "Storage quota exceeded" during processing

**Solution**: File processing creates output files. If quota is exceeded mid-process:
1. The file will be marked as "failed"
2. Partial uploads are cleaned up
3. Run cleanup to free space

### Orphaned files taking up space

**Solution**: Run orphaned cleanup
```bash
node scripts/cleanupStorage.js --orphaned
```

### Storage shows high usage but few files

**Possible causes**:
- Many output files per input file
- Large file sizes
- Orphaned GridFS chunks

**Solution**: Run full cleanup
```bash
node scripts/cleanupStorage.js --stats --cleanup --orphaned
```

## Storage Limits Configuration

Storage limits are configured in `backend/utils/storageManager.js`:

```javascript
const STORAGE_LIMITS = {
  MAX_STORAGE: 512 * 1024 * 1024,      // 512 MB (Atlas free tier)
  WARNING_THRESHOLD: 0.85,              // 85% - start warning
  CLEANUP_THRESHOLD: 0.90,              // 90% - start automatic cleanup
  CRITICAL_THRESHOLD: 0.95,             // 95% - prevent new uploads
  TARGET_AFTER_CLEANUP: 0.70            // 70% - target after cleanup
};
```

Adjust these values if you upgrade to a paid MongoDB Atlas tier.

## Support

For issues or questions about storage management:
1. Check this documentation
2. Review server logs for detailed error messages
3. Run `node scripts/cleanupStorage.js --stats` for current status
4. Contact your system administrator
