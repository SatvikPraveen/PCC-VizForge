"""Earthquake data generator."""

from datetime import datetime, timedelta
from typing import Dict

import numpy as np
import pandas as pd

from pcc_vizforge.utils.io import get_data_directory, load_config, save_data


class EarthquakeGenerator:
    """Generator for synthetic earthquake data."""
    
    def __init__(self, config_name: str = "quakes"):
        """Initialize the generator with configuration."""
        self.config = load_config(config_name)
        self.data_config = self.config["data_generation"]
        
    def generate(self, save_to_file: bool = True) -> pd.DataFrame:
        """Generate earthquake data."""
        if "random_seed" in self.data_config:
            np.random.seed(self.data_config["random_seed"])
        
        n_earthquakes = self.data_config["n_earthquakes"]
        mag_range = self.data_config["magnitude_range"]
        depth_range = self.data_config["depth_range"]
        lat_range = self.data_config["lat_range"]
        lon_range = self.data_config["lon_range"]
        hotspots = self.data_config.get("hotspots", [])
        
        data = []
        base_date = datetime(2023, 1, 1)
        
        for i in range(n_earthquakes):
            # Determine if earthquake occurs in hotspot
            in_hotspot = False
            hotspot_name = "Global"
            
            if hotspots and np.random.random() < sum(h["probability"] for h in hotspots):
                # Choose hotspot based on probability
                hotspot_probs = [h["probability"] for h in hotspots]
                hotspot_idx = np.random.choice(len(hotspots), p=np.array(hotspot_probs)/sum(hotspot_probs))
                hotspot = hotspots[hotspot_idx]
                hotspot_name = hotspot["name"]
                in_hotspot = True
                
                # Generate coordinates within hotspot
                lat = np.random.normal(hotspot["lat_center"], hotspot["lat_range"]/6)
                lon = np.random.normal(hotspot["lon_center"], hotspot["lon_range"]/6)
                lat = np.clip(lat, lat_range[0], lat_range[1])
                lon = np.clip(lon, lon_range[0], lon_range[1])
            else:
                # Random global location
                lat = np.random.uniform(lat_range[0], lat_range[1])
                lon = np.random.uniform(lon_range[0], lon_range[1])
            
            # Magnitude follows Gutenberg-Richter law (exponential distribution)
            magnitude = np.random.exponential(1.5) + mag_range[0]
            magnitude = np.clip(magnitude, mag_range[0], mag_range[1])
            
            # Depth distribution (most earthquakes are shallow)
            if np.random.random() < 0.7:  # 70% shallow
                depth = np.random.exponential(20)
            else:  # 30% deeper
                depth = np.random.uniform(50, depth_range[1])
            depth = np.clip(depth, depth_range[0], depth_range[1])
            
            # Random timestamp within year
            days_offset = np.random.randint(0, 365)
            hours_offset = np.random.randint(0, 24)
            minutes_offset = np.random.randint(0, 60)
            timestamp = base_date + timedelta(days=days_offset, hours=hours_offset, minutes=minutes_offset)
            
            data.append({
                "earthquake_id": i,
                "timestamp": timestamp,
                "latitude": lat,
                "longitude": lon,
                "magnitude": magnitude,
                "depth_km": depth,
                "region": hotspot_name,
                "in_hotspot": in_hotspot,
                "day_of_year": timestamp.timetuple().tm_yday,
                "hour": timestamp.hour,
            })
        
        df = pd.DataFrame(data)
        
        # Add derived metrics
        df["magnitude_category"] = df["magnitude"].apply(self._categorize_magnitude)
        df["depth_category"] = df["depth_km"].apply(self._categorize_depth)
        df["energy_joules"] = 10 ** (1.5 * df["magnitude"] + 4.8)  # Seismic energy
        df["distance_from_equator"] = abs(df["latitude"])
        
        if save_to_file:
            data_dir = get_data_directory("quakes")
            save_data(df, data_dir / "earthquake_data.csv", "csv")
        
        return df
    
    def _categorize_magnitude(self, mag: float) -> str:
        """Categorize earthquake by magnitude."""
        if mag < 3.0:
            return "Micro"
        elif mag < 4.0:
            return "Minor"
        elif mag < 5.0:
            return "Light"
        elif mag < 6.0:
            return "Moderate"
        elif mag < 7.0:
            return "Strong"
        elif mag < 8.0:
            return "Major"
        else:
            return "Great"
    
    def _categorize_depth(self, depth: float) -> str:
        """Categorize earthquake by depth."""
        if depth < 70:
            return "Shallow"
        elif depth < 300:
            return "Intermediate"
        else:
            return "Deep"
    
    def calculate_statistics(self, data: pd.DataFrame) -> Dict[str, any]:
        """Calculate earthquake statistics."""
        stats = {
            "total_earthquakes": len(data),
            "magnitude_stats": {
                "mean": data["magnitude"].mean(),
                "median": data["magnitude"].median(),
                "max": data["magnitude"].max(),
                "min": data["magnitude"].min(),
                "std": data["magnitude"].std(),
            },
            "depth_stats": {
                "mean": data["depth_km"].mean(),
                "median": data["depth_km"].median(),
                "max": data["depth_km"].max(),
                "min": data["depth_km"].min(),
            },
            "regional_distribution": data["region"].value_counts().to_dict(),
            "magnitude_categories": data["magnitude_category"].value_counts().to_dict(),
            "depth_categories": data["depth_category"].value_counts().to_dict(),
            "total_energy_released": data["energy_joules"].sum(),
        }
        return stats