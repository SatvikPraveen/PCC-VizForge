"""Weather data generator."""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from pcc_vizforge.utils.io import get_data_directory, load_config, save_data


class WeatherGenerator:
    """Generator for synthetic weather data."""
    
    def __init__(self, config_name: str = "weather"):
        """Initialize the generator with configuration.
        
        Args:
            config_name: Name of configuration file to use
        """
        self.config = load_config(config_name)
        self.data_config = self.config["data_generation"]
        
    def generate(self, save_to_file: bool = True) -> pd.DataFrame:
        """Generate weather data.
        
        Args:
            save_to_file: Whether to save generated data to file
            
        Returns:
            DataFrame with weather data
        """
        # Set random seed for reproducibility
        if "random_seed" in self.data_config:
            np.random.seed(self.data_config["random_seed"])
        
        n_days = self.data_config["n_days"]
        base_temp = self.data_config["base_temperature"]
        temp_variation = self.data_config["temperature_variation"]
        seasonal_amplitude = self.data_config["seasonal_amplitude"]
        humidity_base = self.data_config["humidity_base"]
        humidity_variation = self.data_config["humidity_variation"]
        precip_prob = self.data_config["precipitation_probability"]
        
        # Generate date range
        start_date = datetime(2023, 1, 1)
        dates = [start_date + timedelta(days=i) for i in range(n_days)]
        
        data = []
        
        for i, date in enumerate(dates):
            day_of_year = date.timetuple().tm_yday
            
            # Temperature with seasonal variation
            seasonal_factor = np.sin(2 * np.pi * day_of_year / 365.25)
            daily_temp = (base_temp + 
                         seasonal_amplitude * seasonal_factor + 
                         np.random.normal(0, temp_variation))
            
            # Temperature variations throughout the day
            temp_morning = daily_temp - 3 + np.random.normal(0, 2)
            temp_afternoon = daily_temp + 5 + np.random.normal(0, 3)
            temp_evening = daily_temp + 1 + np.random.normal(0, 2)
            temp_night = daily_temp - 5 + np.random.normal(0, 2)
            
            # Humidity (inversely correlated with temperature)
            base_humidity = humidity_base - (daily_temp - base_temp) * 0.5
            humidity = np.clip(base_humidity + np.random.normal(0, humidity_variation), 0, 100)
            
            # Precipitation (higher probability with higher humidity)
            precip_chance = precip_prob + (humidity - 50) * 0.01
            has_precipitation = np.random.random() < precip_chance
            precipitation = np.random.exponential(5) if has_precipitation else 0
            
            # Wind speed (higher on days with precipitation)
            wind_base = 10 + (20 if has_precipitation else 0)
            wind_speed = np.random.gamma(2, wind_base / 2)
            
            # Pressure (correlated with weather patterns)
            pressure_base = 1013.25
            pressure_variation = -precipitation * 2 + np.random.normal(0, 10)
            pressure = pressure_base + pressure_variation
            
            # Cloud cover
            cloud_cover = min(100, humidity * 0.8 + precipitation * 10 + np.random.normal(0, 20))
            cloud_cover = max(0, cloud_cover)
            
            data.append({
                "date": date,
                "day_of_year": day_of_year,
                "temperature_avg": daily_temp,
                "temperature_morning": temp_morning,
                "temperature_afternoon": temp_afternoon,
                "temperature_evening": temp_evening,
                "temperature_night": temp_night,
                "temperature_min": min(temp_morning, temp_afternoon, temp_evening, temp_night),
                "temperature_max": max(temp_morning, temp_afternoon, temp_evening, temp_night),
                "humidity": humidity,
                "precipitation": precipitation,
                "wind_speed": wind_speed,
                "pressure": pressure,
                "cloud_cover": cloud_cover,
                "season": self._get_season(day_of_year),
                "weather_type": self._classify_weather(daily_temp, precipitation, wind_speed),
            })
        
        df = pd.DataFrame(data)
        
        # Add derived metrics
        df["temperature_range"] = df["temperature_max"] - df["temperature_min"]
        df["is_rainy_day"] = df["precipitation"] > 0
        df["heat_index"] = self._calculate_heat_index(df["temperature_max"], df["humidity"])
        df["comfort_index"] = self._calculate_comfort_index(df["temperature_avg"], df["humidity"])
        
        if save_to_file:
            data_dir = get_data_directory("weather")
            save_data(df, data_dir / "weather_data.csv", "csv")
        
        return df
    
    def _get_season(self, day_of_year: int) -> str:
        """Determine season from day of year."""
        if day_of_year < 80 or day_of_year > 355:
            return "Winter"
        elif day_of_year < 172:
            return "Spring"
        elif day_of_year < 266:
            return "Summer"
        else:
            return "Autumn"
    
    def _classify_weather(self, temp: float, precip: float, wind: float) -> str:
        """Classify weather type based on conditions."""
        if precip > 10:
            return "Heavy Rain"
        elif precip > 0:
            return "Light Rain"
        elif wind > 25:
            return "Windy"
        elif temp > 30:
            return "Hot"
        elif temp < 0:
            return "Freezing"
        else:
            return "Clear"
    
    def _calculate_heat_index(self, temp: pd.Series, humidity: pd.Series) -> pd.Series:
        """Calculate heat index."""
        # Simplified heat index calculation
        return temp + 0.5 * (humidity - 50) / 10
    
    def _calculate_comfort_index(self, temp: pd.Series, humidity: pd.Series) -> pd.Series:
        """Calculate comfort index (0-100, higher is more comfortable)."""
        temp_comfort = 100 - abs(temp - 22) * 4  # Optimal at 22°C
        humidity_comfort = 100 - abs(humidity - 45) * 2  # Optimal at 45%
        return np.clip((temp_comfort + humidity_comfort) / 2, 0, 100)
    
    def generate_monthly_summary(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate monthly weather summaries."""
        data["month"] = data["date"].dt.month
        data["year"] = data["date"].dt.year
        
        monthly_stats = data.groupby(["year", "month"]).agg({
            "temperature_avg": ["mean", "std"],
            "temperature_min": "min",
            "temperature_max": "max",
            "humidity": "mean",
            "precipitation": ["sum", "mean"],
            "wind_speed": "mean",
            "pressure": "mean",
            "is_rainy_day": "sum",
        }).round(2)
        
        # Flatten column names
        monthly_stats.columns = ["_".join(col).strip() for col in monthly_stats.columns]
        monthly_stats.reset_index(inplace=True)
        
        return monthly_stats