"""Dice simulation data generator."""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from collections import Counter

from pcc_vizforge.utils.io import load_config, save_data, get_data_directory


class DiceGenerator:
    """Generator for dice simulation data."""
    
    def __init__(self, config_name: str = "dice"):
        """Initialize the generator with configuration.
        
        Args:
            config_name: Name of configuration file to use
        """
        self.config = load_config(config_name)
        self.data_config = self.config["data_generation"]
        
    def generate(self, save_to_file: bool = True) -> pd.DataFrame:
        """Generate dice roll data.
        
        Args:
            save_to_file: Whether to save generated data to file
            
        Returns:
            DataFrame with dice roll data
        """
        # Set random seed for reproducibility
        if "random_seed" in self.data_config:
            np.random.seed(self.data_config["random_seed"])
        
        n_rolls = self.data_config["n_rolls"]
        n_dice = self.data_config["n_dice"]
        dice_sides = self.data_config["dice_sides"]
        
        data = []
        
        for roll_id in range(n_rolls):
            # Roll dice
            dice_values = np.random.randint(1, dice_sides + 1, size=n_dice)
            roll_sum = np.sum(dice_values)
            
            # Store individual dice results
            for die_id, value in enumerate(dice_values):
                data.append({
                    "roll_id": roll_id,
                    "die_id": die_id,
                    "die_value": value,
                    "roll_sum": roll_sum,
                    "roll_sequence": roll_id + 1,
                })
        
        df = pd.DataFrame(data)
        
        # Add derived metrics
        df["is_max_value"] = df["die_value"] == dice_sides
        df["is_min_value"] = df["die_value"] == 1
        
        # Add rolling statistics
        roll_sums = df.groupby("roll_id")["die_value"].sum().reset_index()
        roll_sums.columns = ["roll_id", "sum_check"]
        
        # Add cumulative statistics
        df_rolls = df.groupby("roll_id").agg({
            "roll_sum": "first",
            "roll_sequence": "first"
        }).reset_index()
        
        df_rolls["cumulative_sum"] = df_rolls["roll_sum"].cumsum()
        df_rolls["rolling_avg"] = df_rolls["roll_sum"].expanding().mean()
        df_rolls["is_doubles"] = (n_dice == 2) & (df.groupby("roll_id")["die_value"].nunique() == 1).values
        
        # Merge back
        df = df.merge(df_rolls[["roll_id", "cumulative_sum", "rolling_avg", "is_doubles"]], 
                     on="roll_id", how="left")
        
        if save_to_file:
            data_dir = get_data_directory("dice")
            save_data(df, data_dir / "dice_data.csv", "csv")
        
        return df
    
    def calculate_probabilities(self, data: pd.DataFrame) -> Dict[str, Dict]:
        """Calculate theoretical and observed probabilities.
        
        Args:
            data: Dice roll DataFrame
            
        Returns:
            Dictionary containing probability analysis
        """
        n_dice = self.data_config["n_dice"]
        dice_sides = self.data_config["dice_sides"]
        
        # Observed frequencies
        roll_sums = data.groupby("roll_id")["roll_sum"].first()
        sum_counts = Counter(roll_sums)
        
        # Individual die frequencies
        die_counts = Counter(data["die_value"])
        
        # Theoretical probabilities for sums
        theoretical_probs = {}
        min_sum = n_dice
        max_sum = n_dice * dice_sides
        
        for s in range(min_sum, max_sum + 1):
            # Calculate number of ways to get sum s with n_dice dice
            ways = self._count_ways_to_sum(s, n_dice, dice_sides)
            total_outcomes = dice_sides ** n_dice
            theoretical_probs[s] = ways / total_outcomes
        
        # Observed probabilities
        total_rolls = len(roll_sums)
        observed_probs = {s: count / total_rolls for s, count in sum_counts.items()}
        
        return {
            "theoretical_sum_probabilities": theoretical_probs,
            "observed_sum_probabilities": observed_probs,
            "individual_die_frequencies": dict(die_counts),
            "sum_frequency_counts": dict(sum_counts),
            "total_rolls": total_rolls,
            "chi_square_statistic": self._chi_square_test(theoretical_probs, sum_counts, total_rolls)
        }
    
    def _count_ways_to_sum(self, target_sum: int, n_dice: int, dice_sides: int) -> int:
        """Count the number of ways to achieve a target sum with n dice.
        
        Args:
            target_sum: Target sum value
            n_dice: Number of dice
            dice_sides: Number of sides per die
            
        Returns:
            Number of ways to achieve the target sum
        """
        if n_dice == 1:
            return 1 if 1 <= target_sum <= dice_sides else 0
        
        ways = 0
        for first_die in range(1, min(dice_sides + 1, target_sum)):
            remaining_sum = target_sum - first_die
            ways += self._count_ways_to_sum(remaining_sum, n_dice - 1, dice_sides)
        
        return ways
    
    def _chi_square_test(self, theoretical_probs: Dict[int, float], 
                        observed_counts: Dict[int, int], total_rolls: int) -> float:
        """Perform chi-square goodness of fit test.
        
        Args:
            theoretical_probs: Theoretical probabilities
            observed_counts: Observed frequency counts
            total_rolls: Total number of rolls
            
        Returns:
            Chi-square test statistic
        """
        chi_square = 0.0
        
        for sum_value, theoretical_prob in theoretical_probs.items():
            expected = theoretical_prob * total_rolls
            observed = observed_counts.get(sum_value, 0)
            
            if expected > 0:
                chi_square += ((observed - expected) ** 2) / expected
        
        return chi_square
    
    def generate_streak_analysis(self, data: pd.DataFrame) -> Dict[str, any]:
        """Analyze streaks and patterns in dice rolls.
        
        Args:
            data: Dice roll DataFrame
            
        Returns:
            Dictionary containing streak analysis
        """
        roll_sums = data.groupby("roll_id")["roll_sum"].first().values
        
        # Find streaks of identical sums
        streaks = []
        current_streak = 1
        current_value = roll_sums[0]
        
        for i in range(1, len(roll_sums)):
            if roll_sums[i] == current_value:
                current_streak += 1
            else:
                if current_streak > 1:
                    streaks.append({"value": current_value, "length": current_streak})
                current_value = roll_sums[i]
                current_streak = 1
        
        # Don't forget the last streak
        if current_streak > 1:
            streaks.append({"value": current_value, "length": current_streak})
        
        # Analyze runs (sequences of increasing or decreasing values)
        runs_up = []
        runs_down = []
        current_run_up = 1
        current_run_down = 1
        
        for i in range(1, len(roll_sums)):
            if roll_sums[i] > roll_sums[i-1]:
                current_run_up += 1
                if current_run_down > 1:
                    runs_down.append(current_run_down)
                current_run_down = 1
            elif roll_sums[i] < roll_sums[i-1]:
                current_run_down += 1
                if current_run_up > 1:
                    runs_up.append(current_run_up)
                current_run_up = 1
            else:
                if current_run_up > 1:
                    runs_up.append(current_run_up)
                if current_run_down > 1:
                    runs_down.append(current_run_down)
                current_run_up = 1
                current_run_down = 1
        
        return {
            "identical_value_streaks": streaks,
            "longest_streak": max([s["length"] for s in streaks], default=0),
            "total_streaks": len(streaks),
            "increasing_runs": runs_up,
            "decreasing_runs": runs_down,
            "longest_increasing_run": max(runs_up, default=0),
            "longest_decreasing_run": max(runs_down, default=0),
        }