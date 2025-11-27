# SOX Dashboard - Testing Guide

## Quick Start Testing

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
streamlit run app.py
```

### 3. Check Logs
After starting, verify logging is working:
```bash
# Check if logs directory was created
ls logs/

# View the log file
cat logs/sox_dashboard_*.log
```

You should see:
```
2025-11-26 XX:XX:XX - __main__ - INFO - Application started
2025-11-26 XX:XX:XX - __main__ - INFO - Database directory initialized: data
2025-11-26 XX:XX:XX - __main__ - INFO - Database schema initialized successfully
```

## Test Scenarios

### Test 1: Upload Valid Excel File ✅
1. Click "Carregar arquivo Excel"
2. Upload a valid .xlsx file
3. Check logs for: `INFO - Loading Excel file: filename.xlsx`
4. Verify file loads successfully
5. Click "Salvar arquivo na base"
6. Check logs for: `INFO - Successfully saved upload {uuid}`
7. Verify success message appears

### Test 2: Error Handling - Empty File ❌
1. Create an empty Excel file
2. Try to upload it
3. **Expected:** Red error message "❌ Excel file is empty"
4. **Check logs:** `ERROR - Excel validation failed: Excel file is empty`

### Test 3: Error Handling - Corrupted File ❌
1. Upload a non-Excel file renamed to .xlsx
2. **Expected:** Error message displayed
3. **Check logs:** Error with full stack trace
4. **Verify:** Application doesn't crash

### Test 4: Database Operations ✅
1. Load uploaded data
2. Click "Carregar TODOS"
3. **Check logs:** `INFO - Loading all data from database`
4. Verify data displays correctly
5. Apply filters
6. **Check logs:** Filter operations logged

### Test 5: Delete Operation ✅
1. Select an upload to delete
2. Click "Excluir upload"
3. **Expected:** Success message "✅ Removidas X linhas"
4. **Check logs:** `INFO - Deleted X rows for upload_id: {uuid}`

### Test 6: Download Operations ✅
1. Filter data
2. Click "Download CSV"
3. **Check logs:** `INFO - Preparing download files`
4. Click "Download Excel"
5. Verify both downloads work

### Test 7: Large File Handling ❌
1. Create or upload file with > 100,000 rows
2. **Expected:** Error "File too large: X rows (max 100,000)"
3. **Check logs:** Validation error logged

## Log Verification Checklist

After each operation, verify logs contain:

- [ ] Timestamp
- [ ] Module name (`__main__`)
- [ ] Log level (INFO, ERROR, etc.)
- [ ] Clear message describing the operation
- [ ] For errors: Full stack trace

Example good log entry:
```
2025-11-26 18:30:20 - __main__ - INFO - Successfully saved upload abc-123 with 1250 rows
```

## Common Issues and Solutions

### Issue: Logs directory not created
**Solution:** Check file permissions in project directory

### Issue: No logs being written
**Solution:**
1. Check LOG_LEVEL in config.py
2. Verify logging configuration loaded
3. Check disk space

### Issue: Database errors
**Solution:**
1. Check logs for specific error
2. Verify `data/` directory permissions
3. Check if database is locked by another process

## Performance Testing

### Monitor Log File Size
```bash
# Check log file size
ls -lh logs/

# Rotate logs if too large (manual)
mv logs/sox_dashboard_20251126.log logs/sox_dashboard_20251126_backup.log
```

### Test with Multiple Users
1. Open multiple browser tabs
2. Upload files simultaneously
3. Check for database locking errors in logs
4. Verify all operations complete successfully

## Error Message Validation

Verify these error messages display correctly:

- ✅ "Upload salvo com ID: {uuid}"
- ✅ "Removidas X linhas"
- ❌ "Error loading Excel file: {details}"
- ❌ "Error saving to database: {details}"
- ❌ "Excel file is empty"
- ❌ "File too large: X rows (max 100,000)"
- ⚠️ "Envie um arquivo primeiro"
- ⚠️ "Nenhuma linha foi removida"

## Success Criteria

The application is working correctly if:

1. ✅ All operations logged to file
2. ✅ Errors display user-friendly messages
3. ✅ Application doesn't crash on invalid input
4. ✅ Database operations succeed
5. ✅ Log files readable and informative
6. ✅ Filters work correctly
7. ✅ Downloads work correctly
8. ✅ No data loss on errors

## Next Steps After Testing

1. Review all log files for unexpected errors
2. Test with real production data (if available)
3. Set up log monitoring/alerting (optional)
4. Configure backup strategy for database
5. Document any custom configurations

## Debugging Tips

### Enable Debug Logging
Edit `config.py`:
```python
LOG_LEVEL = "DEBUG"
```

### Find Specific Errors
```bash
# Find all errors
grep ERROR logs/*.log

# Find errors for specific operation
grep "saving to database" logs/*.log

# Count errors
grep -c ERROR logs/*.log
```

### Monitor Real-Time
```bash
# Watch logs as they happen
tail -f logs/sox_dashboard_*.log

# Filter for errors only
tail -f logs/sox_dashboard_*.log | grep ERROR
```
