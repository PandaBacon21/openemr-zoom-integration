"""
Planned but not yet implemented
NEEDS: 

Accept old key and new key as arguments
Loop through all ZoomAccount rows where key_version = old_version
Decrypt each encrypted field with the old key
Re-encrypt with the new key
Update key_version
Commit in batches
"""

