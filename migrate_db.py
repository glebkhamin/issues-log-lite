#!/usr/bin/env python3
"""
Simple database migration script to add the display_order column
"""
import os
import sqlite3
from datetime import datetime

def migrate_database():
    """Add display_order column to existing issues table"""
    db_path = 'db.sqlite3'
    
    # Check if database exists
    if not os.path.exists(db_path):
        print("Database not found. This is normal for new deployments.")
        return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if display_order column already exists
        cursor.execute("PRAGMA table_info(issue)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'display_order' not in columns:
            print("Adding display_order column to issue table...")
            
            # Add the display_order column
            cursor.execute("ALTER TABLE issue ADD COLUMN display_order INTEGER DEFAULT 0")
            
            # Set display_order for existing issues based on their current order
            cursor.execute("SELECT id FROM issue ORDER BY date_reported ASC")
            issue_ids = cursor.fetchall()
            
            for index, (issue_id,) in enumerate(issue_ids):
                cursor.execute("UPDATE issue SET display_order = ? WHERE id = ?", (index, issue_id))
            
            conn.commit()
            print(f"Successfully migrated {len(issue_ids)} issues with display_order")
        else:
            print("display_order column already exists. No migration needed.")
        
        conn.close()
        
    except Exception as e:
        print(f"Migration failed: {e}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate_database()
