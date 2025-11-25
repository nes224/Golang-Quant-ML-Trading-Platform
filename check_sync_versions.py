"""
Quick script to check database sync versions
"""

import json
from pathlib import Path

def check_versions():
    """Check sync versions for both Windows and macOS"""
    
    base_dir = Path(__file__).parent / "data_sync"
    
    print("\n" + "="*60)
    print("DATABASE SYNC VERSION CHECK")
    print("="*60 + "\n")
    
    for os_name in ["windows", "macos"]:
        os_dir = base_dir / os_name
        metadata_file = os_dir / "sync_metadata.json"
        
        print(f"📁 {os_name.upper()}")
        print("-" * 60)
        
        if not metadata_file.exists():
            print("   ❌ No metadata found\n")
            continue
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        print(f"   Last Export: {metadata.get('last_export', 'Never')}")
        print(f"   Last Import: {metadata.get('last_import', 'Never')}")
        print()
        
        # Exported versions
        exported = metadata.get('versions', {})
        if exported:
            print("   📤 Exported Versions:")
            for table, version in exported.items():
                print(f"      • {table}: v{version}")
        else:
            print("   📤 No exports yet")
        
        print()
        
        # Imported versions
        imported = metadata.get('imported_versions', {})
        if imported:
            print("   📥 Imported Versions:")
            for table, version in imported.items():
                print(f"      • {table}: v{version}")
        else:
            print("   📥 No imports yet")
        
        print()
    
    # Cross-check
    print("="*60)
    print("SYNC STATUS")
    print("="*60 + "\n")
    
    win_meta_file = base_dir / "windows" / "sync_metadata.json"
    mac_meta_file = base_dir / "macos" / "sync_metadata.json"
    
    if win_meta_file.exists() and mac_meta_file.exists():
        with open(win_meta_file, 'r') as f:
            win_meta = json.load(f)
        with open(mac_meta_file, 'r') as f:
            mac_meta = json.load(f)
        
        win_versions = win_meta.get('versions', {})
        mac_versions = mac_meta.get('versions', {})
        
        all_tables = set(win_versions.keys()) | set(mac_versions.keys())
        
        for table in sorted(all_tables):
            win_v = win_versions.get(table, "0.0")
            mac_v = mac_versions.get(table, "0.0")
            
            if win_v == mac_v:
                status = "✅ In Sync"
            elif win_v > mac_v:
                status = f"⚠️  Windows ahead (v{win_v} > v{mac_v})"
            else:
                status = f"⚠️  macOS ahead (v{mac_v} > v{win_v})"
            
            print(f"{table:20} | Win: v{win_v:4} | Mac: v{mac_v:4} | {status}")
    else:
        print("⚠️  Not enough data to compare")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    check_versions()
