use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
pub struct SrZone {
    pub level: f64,
    pub zone_type: String,
    pub strength: usize,
    pub top: f64,
    pub bottom: f64,
    pub distance: f64,
}

/// Identify Support and Resistance Zones
pub fn identify_sr_zones(
    swing_highs: &[Option<f64>], 
    swing_lows: &[Option<f64>], 
    current_price: f64,
    zone_threshold: f64, 
    min_touches: usize
) -> Vec<SrZone> {
    let mut all_levels = Vec::new();
    
    // Collect all valid swing points
    for val in swing_highs {
        if let Some(v) = val {
            all_levels.push(*v);
        }
    }
    for val in swing_lows {
        if let Some(v) = val {
            all_levels.push(*v);
        }
    }
    
    if all_levels.is_empty() {
        return Vec::new();
    }
    
    let mut zones = Vec::new();
    let mut used_indices = vec![false; all_levels.len()];
    
    for i in 0..all_levels.len() {
        if used_indices[i] {
            continue;
        }
        
        let level = all_levels[i];
        let tolerance = level * zone_threshold;
        let mut cluster = vec![level];
        let mut cluster_indices = vec![i];
        
        for j in (i + 1)..all_levels.len() {
            if used_indices[j] {
                continue;
            }
            
            let other_level = all_levels[j];
            if (other_level - level).abs() <= tolerance {
                cluster.push(other_level);
                cluster_indices.push(j);
            }
        }
        
        if cluster.len() >= min_touches {
            let sum: f64 = cluster.iter().sum();
            let zone_level = sum / cluster.len() as f64;
            
            let mut max_val = cluster[0];
            let mut min_val = cluster[0];
            for &val in &cluster {
                if val > max_val { max_val = val; }
                if val < min_val { min_val = val; }
            }
            
            let zone_type = if zone_level < current_price {
                "support".to_string()
            } else {
                "resistance".to_string()
            };
            
            zones.push(SrZone {
                level: (zone_level * 100.0).round() / 100.0,
                zone_type,
                strength: cluster.len(),
                top: (max_val * 100.0).round() / 100.0,
                bottom: (min_val * 100.0).round() / 100.0,
                distance: (current_price - zone_level).abs(),
            });
            
            // Mark used
            for idx in cluster_indices {
                used_indices[idx] = true;
            }
        }
    }
    
    // Sort by strength (descending)
    zones.sort_by(|a, b| b.strength.cmp(&a.strength));
    
    // Keep top 5
    if zones.len() > 5 {
        zones.truncate(5);
    }
    
    // Sort by distance (ascending)
    zones.sort_by(|a, b| a.distance.partial_cmp(&b.distance).unwrap());
    
    zones
}
