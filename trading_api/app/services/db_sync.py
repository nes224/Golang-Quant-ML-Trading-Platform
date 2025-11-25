"""
Database Sync Service - Cross-Platform Data Synchronization

This service enables seamless data sync between Windows and macOS machines
by exporting/importing database tables to/from JSON files.

Features:
- Auto-export on shutdown
- Auto-import on startup
- Version tracking
- Merge strategy: Keep latest by timestamp
"""

import os
import json
import platform
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from app.core.database import db

# Detect current OS
CURRENT_OS = "windows" if platform.system() == "Windows" else "macos"

# Base sync directory (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SYNC_BASE_DIR = PROJECT_ROOT / "data_sync"
SYNC_DIR = SYNC_BASE_DIR / CURRENT_OS

# Tables to sync
TABLES_TO_SYNC = [
    "market_data",
    "journal_entries", 
    "checklist_monthly",
    "news_analysis"
]

# Metadata file
METADATA_FILE = SYNC_DIR / "sync_metadata.json"


def ensure_sync_directories():
    """
    Create sync directory structure if not exists
    """
    for os_name in ["windows", "macos"]:
        os_dir = SYNC_BASE_DIR / os_name
        os_dir.mkdir(parents=True, exist_ok=True)
        
        for table in TABLES_TO_SYNC:
            table_dir = os_dir / table
            table_dir.mkdir(exist_ok=True)
    
    print(f"[SYNC] Directories initialized at: {SYNC_BASE_DIR}")


def get_sync_metadata() -> Dict:
    """
    Get sync metadata (version tracking)
    """
    if METADATA_FILE.exists():
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {
            "os": CURRENT_OS,
            "last_export": None,
            "last_import": None,
            "versions": {},
            "imported_versions": {}
        }


def save_sync_metadata(metadata: Dict):
    """
    Save sync metadata
    """
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def get_next_version(table_name: str) -> str:
    """
    Get next version number for a table
    
    IMPORTANT: Only increment version if:
    1. This is the first export (version 0.0), OR
    2. The other OS has imported the latest version
    
    This prevents data loss when syncing between machines.
    
    Returns:
        Version string like "1.0", "1.1", etc.
    """
    metadata = get_sync_metadata()
    current_version = metadata.get("versions", {}).get(table_name, "0.0")
    
    # Check if this is first export
    if current_version == "0.0":
        # First export, start with 0.1
        return "0.1"
    
    # Check if other OS has imported the latest version
    source_os = "macos" if CURRENT_OS == "windows" else "windows"
    source_dir = SYNC_BASE_DIR / source_os
    
    if source_dir.exists():
        # Check other OS's imported_versions
        other_metadata_file = source_dir / "sync_metadata.json"
        if other_metadata_file.exists():
            with open(other_metadata_file, 'r', encoding='utf-8') as f:
                other_metadata = json.load(f)
            
            # Get what version the other OS imported from us
            other_imported = other_metadata.get("imported_versions", {}).get(table_name, "0.0")
            
            # If other OS hasn't imported our latest version yet, don't increment
            if other_imported < current_version:
                print(f"[VERSION] {table_name}: Keeping v{current_version} (waiting for {source_os} to import)")
                return current_version
    
    # Safe to increment - either no other OS or they've imported our latest
    major, minor = map(int, current_version.split('.'))
    minor += 1
    
    new_version = f"{major}.{minor}"
    print(f"[VERSION] {table_name}: {current_version} → {new_version}")
    return new_version


def export_table_to_file(table_name: str, df: pd.DataFrame, version: str) -> str:
    """
    Export DataFrame to JSON file with version
    
    Returns:
        Path to exported file
    """
    table_dir = SYNC_DIR / table_name
    table_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{table_name}_v{version}.json"
    filepath = table_dir / filename
    
    # Convert DataFrame to JSON
    # Handle datetime columns
    df_copy = df.copy()
    for col in df_copy.columns:
        if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
            df_copy[col] = df_copy[col].astype(str)
    
    # Export
    data = {
        "table": table_name,
        "version": version,
        "os": CURRENT_OS,
        "exported_at": datetime.now().isoformat(),
        "row_count": len(df),
        "data": df_copy.to_dict(orient='records')
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"[EXPORT] {table_name} v{version} → {filepath} ({len(df)} rows)")
    return str(filepath)


def export_all_tables() -> Dict[str, str]:
    """
    Export all database tables to files
    
    Returns:
        Dictionary mapping table names to file paths
    """
    ensure_sync_directories()
    metadata = get_sync_metadata()
    exported_files = {}
    
    print(f"\n{'='*60}")
    print(f"[SYNC] Starting Database Export ({CURRENT_OS.upper()})")
    print(f"{'='*60}\n")
    
    for table_name in TABLES_TO_SYNC:
        try:
            # Get data from database
            if table_name == "market_data":
                # Export market data (limit to recent data to avoid huge files)
                query = f"SELECT * FROM {table_name} ORDER BY timestamp DESC LIMIT 10000"
            else:
                query = f"SELECT * FROM {table_name}"
            
            df = db.execute_query(query)
            
            if df is None or df.empty:
                print(f"[SKIP] {table_name} - No data to export")
                continue
            
            # Get next version
            version = get_next_version(table_name)
            
            # Export to file
            filepath = export_table_to_file(table_name, df, version)
            exported_files[table_name] = filepath
            
            # Update metadata
            metadata["versions"][table_name] = version
            
            # Cleanup old versions (keep only latest 3)
            cleanup_old_versions(table_name, keep_count=3)
            
        except Exception as e:
            print(f"[ERROR] Failed to export {table_name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Update metadata
    metadata["last_export"] = datetime.now().isoformat()
    metadata["os"] = CURRENT_OS
    save_sync_metadata(metadata)
    
    print(f"\n{'='*60}")
    print(f"[SYNC] Export Complete - {len(exported_files)} tables exported")
    print(f"{'='*60}\n")
    
    return exported_files


def cleanup_old_versions(table_name: str, keep_count: int = 3):
    """
    Remove old version files, keeping only the latest N versions
    
    Args:
        table_name: Name of the table
        keep_count: Number of latest versions to keep
    """
    table_dir = SYNC_DIR / table_name
    if not table_dir.exists():
        return
    
    # Get all version files
    version_files = sorted(table_dir.glob(f"{table_name}_v*.json"))
    
    # Keep only latest N
    if len(version_files) > keep_count:
        files_to_delete = version_files[:-keep_count]
        for file in files_to_delete:
            try:
                file.unlink()
                print(f"[CLEANUP] Removed old version: {file.name}")
            except Exception as e:
                print(f"[WARNING] Failed to remove {file.name}: {e}")


def import_table_from_file(filepath: str) -> bool:
    """
    Import data from JSON file to database
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        table_name = data['table']
        version = data['version']
        source_os = data.get('os', 'unknown')
        records = data['data']
        
        if not records:
            print(f"[SKIP] {filepath} - No data")
            return False
        
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        # Import to database (upsert strategy)
        if table_name == "market_data":
            # For market_data, upsert row by row
            for _, row in df.iterrows():
                db.upsert_market_data_row(row.to_dict())
        elif table_name == "journal_entries":
            # For journal, use existing save method
            for _, row in df.iterrows():
                db.upsert_journal_entry(row.to_dict())
        elif table_name == "checklist_monthly":
            # For checklist, upsert row by row
            for _, row in df.iterrows():
                db.upsert_checklist_entry(row.to_dict())
        elif table_name == "news_analysis":
            # For news, upsert row by row
            for _, row in df.iterrows():
                db.upsert_news_entry(row.to_dict())
        
        print(f"[IMPORT] {table_name} v{version} from {source_os} → {len(df)} rows")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to import {filepath}: {e}")
        import traceback
        traceback.print_exc()
        return False


def import_from_other_os() -> Dict[str, int]:
    """
    Import data from the other OS (cross-platform sync)
    
    Returns:
        Dictionary with import statistics
    """
    ensure_sync_directories()
    
    # Determine source OS
    source_os = "macos" if CURRENT_OS == "windows" else "windows"
    source_dir = SYNC_BASE_DIR / source_os
    
    if not source_dir.exists():
        print(f"[SYNC] No data from {source_os} to import")
        return {}
    
    print(f"\n{'='*60}")
    print(f"[SYNC] Starting Import from {source_os.upper()} → {CURRENT_OS.upper()}")
    print(f"{'='*60}\n")
    
    metadata = get_sync_metadata()
    imported_versions = metadata.get("imported_versions", {})
    stats = {}
    
    for table_name in TABLES_TO_SYNC:
        table_dir = source_dir / table_name
        
        if not table_dir.exists():
            continue
        
        # Get all version files
        version_files = sorted(table_dir.glob(f"{table_name}_v*.json"))
        
        if not version_files:
            continue
        
        # Get last imported version
        last_imported = imported_versions.get(table_name, "0.0")
        
        # Import only newer versions
        imported_count = 0
        for filepath in version_files:
            # Extract version from filename
            filename = filepath.stem  # e.g., "market_data_v1.2"
            version = filename.split('_v')[-1]  # e.g., "1.2"
            
            # Compare versions
            if version > last_imported:
                success = import_table_from_file(str(filepath))
                if success:
                    imported_count += 1
                    imported_versions[table_name] = version
        
        stats[table_name] = imported_count
    
    # Update metadata
    metadata["imported_versions"] = imported_versions
    metadata["last_import"] = datetime.now().isoformat()
    save_sync_metadata(metadata)
    
    print(f"\n{'='*60}")
    print(f"[SYNC] Import Complete")
    for table, count in stats.items():
        print(f"  - {table}: {count} versions imported")
    print(f"{'='*60}\n")
    
    return stats


def auto_export_on_shutdown():
    """
    Auto-export database on application shutdown
    This should be called in the shutdown event handler
    """
    print("\n" + "="*70)
    print("💾 DATABASE SYNC - SHUTDOWN EXPORT")
    print("="*70 + "\n")
    
    print(f"📍 Current OS: {CURRENT_OS.upper()}")
    print(f"📁 Export Location: {SYNC_DIR}\n")
    
    exported_files = export_all_tables()
    
    print("\n" + "="*70)
    print("✅ EXPORT COMPLETE")
    print("="*70)
    
    if exported_files:
        print(f"\n   💾 Exported {len(exported_files)} table(s):")
        metadata = get_sync_metadata()
        for table, filepath in exported_files.items():
            version = metadata.get("versions", {}).get(table, "unknown")
            print(f"      ✓ {table} (v{version})")
        print(f"\n   📂 Files saved to: data_sync/{CURRENT_OS}/")
        print(f"   🔄 Ready to sync with other OS!")
    else:
        print(f"\n   ℹ️  No data to export")
    
    print("\n" + "="*70 + "\n")


def auto_import_on_startup():
    """
    Auto-import data from other OS on application startup
    This should be called in the startup event handler
    """
    print("\n" + "="*70)
    print("🔄 DATABASE SYNC - STARTUP CHECK")
    print("="*70)
    
    # Detect current and source OS
    source_os = "macos" if CURRENT_OS == "windows" else "windows"
    source_dir = SYNC_BASE_DIR / source_os
    
    print(f"\n📍 Current OS: {CURRENT_OS.upper()}")
    print(f"🔍 Checking for data from: {source_os.upper()}")
    
    if not source_dir.exists():
        print(f"\n✅ No sync data from {source_os.upper()} found")
        print("   This is normal if you haven't used the other OS yet.\n")
        print("="*70 + "\n")
        return
    
    # Get metadata
    metadata = get_sync_metadata()
    imported_versions = metadata.get("imported_versions", {})
    
    # Check for available updates
    available_updates = {}
    for table_name in TABLES_TO_SYNC:
        table_dir = source_dir / table_name
        if not table_dir.exists():
            continue
        
        version_files = sorted(table_dir.glob(f"{table_name}_v*.json"))
        if not version_files:
            continue
        
        # Get latest version from source
        latest_file = version_files[-1]
        latest_version = latest_file.stem.split('_v')[-1]
        
        # Get last imported version
        last_imported = imported_versions.get(table_name, "0.0")
        
        # Check if update available
        if latest_version > last_imported:
            available_updates[table_name] = {
                "current": last_imported,
                "available": latest_version,
                "file": str(latest_file)
            }
    
    # Report findings
    if not available_updates:
        print(f"\n✅ All data is up-to-date!")
        print(f"   No new data from {source_os.upper()} to import.\n")
        print("="*70 + "\n")
        return
    
    # Show available updates
    print(f"\n📦 AVAILABLE UPDATES FROM {source_os.upper()}:")
    print("-" * 70)
    
    for table, info in available_updates.items():
        print(f"   • {table:20} v{info['current']} → v{info['available']} (NEW)")
    
    print("\n🚀 Starting auto-import...")
    print("-" * 70)
    
    # Proceed with import
    stats = import_from_other_os()
    
    # Summary
    print("\n" + "="*70)
    print("✅ SYNC COMPLETE")
    print("="*70)
    
    total_imported = sum(stats.values())
    if total_imported > 0:
        print(f"\n   📥 Imported {total_imported} table(s) from {source_os.upper()}")
        for table, count in stats.items():
            if count > 0:
                print(f"      ✓ {table}: {count} version(s)")
        print(f"\n   💾 Your database is now synced with {source_os.upper()}!")
    else:
        print(f"\n   ℹ️  No new data was imported")
    
    print("\n" + "="*70 + "\n")


def get_sync_status() -> Dict:
    """
    Get current sync status for UI display
    
    Returns:
        Dictionary with sync information
    """
    metadata = get_sync_metadata()
    
    # Check for available imports from other OS
    source_os = "macos" if CURRENT_OS == "windows" else "windows"
    source_dir = SYNC_BASE_DIR / source_os
    
    available_imports = {}
    if source_dir.exists():
        for table_name in TABLES_TO_SYNC:
            table_dir = source_dir / table_name
            if table_dir.exists():
                version_files = list(table_dir.glob(f"{table_name}_v*.json"))
                if version_files:
                    # Get latest version
                    latest_file = sorted(version_files)[-1]
                    version = latest_file.stem.split('_v')[-1]
                    available_imports[table_name] = {
                        "version": version,
                        "file": str(latest_file),
                        "imported": version <= metadata.get("imported_versions", {}).get(table_name, "0.0")
                    }
    
    return {
        "current_os": CURRENT_OS,
        "last_export": metadata.get("last_export"),
        "last_import": metadata.get("last_import"),
        "exported_versions": metadata.get("versions", {}),
        "imported_versions": metadata.get("imported_versions", {}),
        "available_imports": available_imports,
        "sync_dir": str(SYNC_DIR)
    }

