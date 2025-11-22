import pandas as pd
import numpy as np

def identify_sr_zones(df, zone_threshold=0.002, min_touches=2):
    """
    Identifies Support and Resistance Zones using Go API.
    Falls back to Python if unavailable.
    """
    if df is None or df.empty or len(df) < 20:
        return df, []
    
    # DISABLED: Go API doesn't return S/R zones yet
    # Try Go API first
    # try:
    #     from go_client import go_client
    #     
    #     if go_client.health_check():
    #         result = go_client.analyze_smc(df)
    #         
    #         if result and 'sr_zones' in result:
    #             # Normalize keys for compatibility (Rust uses zone_type, Python uses type)
    #             zones = result['sr_zones']
    #             current_price = df['Close'].iloc[-1]
    #             
    #             for zone in zones:
    #                 if 'zone_type' in zone:
    #                     zone['type'] = zone['zone_type']
    #                 # Ensure distance is calculated relative to current price
    #                 zone['distance'] = abs(current_price - zone['level'])
    #             
    #             # Sort by distance (nearest first)
    #             zones.sort(key=lambda x: x['distance'])
    #             
    #             return df, zones
    # except Exception as e:
    #     print(f"Go API unavailable for S/R zones, using Python fallback: {e}")

    # Python fallback (ALWAYS USE THIS FOR NOW)
    # Get all swing points
    swing_highs = df[df.get('Is_Swing_High', False) == True]['High'].values
    swing_lows = df[df.get('Is_Swing_Low', False) == True]['Low'].values
    
    # Combine all potential S/R levels
    all_levels = list(swing_highs) + list(swing_lows)
    
    if len(all_levels) == 0:
        return df, []
    
    # Cluster nearby levels into zones
    zones = []
    used_indices = set()
    
    for i, level in enumerate(all_levels):
        if i in used_indices:
            continue
        
        # Find all levels within threshold
        tolerance = level * zone_threshold
        cluster = [level]
        cluster_indices = [i]
        
        for j, other_level in enumerate(all_levels):
            if j <= i or j in used_indices:
                continue
            
            if abs(other_level - level) <= tolerance:
                cluster.append(other_level)
                cluster_indices.append(j)
        
        # Only create zone if minimum touches met
        if len(cluster) >= min_touches:
            zone_level = np.mean(cluster)
            zone_top = max(cluster)
            zone_bottom = min(cluster)
            
            # Determine if support or resistance based on current price
            current_price = df['Close'].iloc[-1]
            zone_type = 'support' if zone_level < current_price else 'resistance'
            
            zones.append({
                'level': round(zone_level, 2),
                'type': zone_type,
                'strength': len(cluster),
                'top': round(zone_top, 2),
                'bottom': round(zone_bottom, 2),
                'distance': abs(current_price - zone_level)
            })
            
            # Mark as used
            used_indices.update(cluster_indices)
    
    # Sort by strength (most touches first)
    zones.sort(key=lambda x: x['strength'], reverse=True)
    
    # Keep only top 5 strongest zones
    zones = zones[:5]
    
    # Sort by distance from current price (nearest first)
    zones.sort(key=lambda x: x['distance'])
    
    return df, zones


def get_nearest_sr(df, zones, zone_type='both'):
    """
    Get nearest Support/Resistance zone to current price.
    
    Args:
        df: DataFrame
        zones: List of S/R zones
        zone_type: 'support', 'resistance', or 'both'
    
    Returns:
        Nearest zone or None
    """
    if not zones:
        return None
    
    current_price = df['Close'].iloc[-1]
    
    filtered_zones = zones
    if zone_type != 'both':
        filtered_zones = [z for z in zones if z['type'] == zone_type]
    
    if not filtered_zones:
        return None
    
    # Already sorted by distance
    return filtered_zones[0]
