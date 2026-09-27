"""GitHub statistics data generator."""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from pcc_vizforge.utils.io import load_config, save_data, get_data_directory


class GitHubGenerator:
    """Generator for synthetic GitHub repository statistics."""
    
    def __init__(self, config_name: str = "github"):
        """Initialize the generator with configuration."""
        self.config = load_config(config_name)
        self.data_config = self.config["data_generation"]
        
    def generate(self, save_to_file: bool = True) -> pd.DataFrame:
        """Generate GitHub repository data."""
        if "random_seed" in self.data_config:
            np.random.seed(self.data_config["random_seed"])
        
        n_repos = self.data_config["n_repositories"]
        languages = self.data_config["languages"]
        stars_range = self.data_config["stars_range"]
        forks_range = self.data_config["forks_range"]
        issues_range = self.data_config["issues_range"]
        commits_range = self.data_config["commits_range"]
        
        data = []
        repo_types = ["library", "application", "framework", "tool", "game", "website"]
        
        for i in range(n_repos):
            # Repository basic info
            primary_language = np.random.choice(languages)
            repo_type = np.random.choice(repo_types)
            
            # Stars follow power law (most repos have few stars)
            stars = int(np.random.pareto(0.5) * 10)
            stars = np.clip(stars, stars_range[0], stars_range[1])
            
            # Forks correlated with stars but lower
            forks = int(stars * np.random.uniform(0.1, 0.3) + np.random.exponential(2))
            forks = np.clip(forks, forks_range[0], forks_range[1])
            
            # Issues somewhat correlated with activity
            base_issues = stars * 0.1 + forks * 0.2
            issues = int(base_issues + np.random.exponential(5))
            issues = np.clip(issues, issues_range[0], issues_range[1])
            
            # Commits based on repo age and activity
            repo_age_days = np.random.randint(30, 1095)  # 1 month to 3 years
            commits_per_day = np.random.gamma(1, 2)
            commits = int(commits_per_day * repo_age_days)
            commits = np.clip(commits, commits_range[0], commits_range[1])
            
            # Repository size and activity metrics
            size_kb = int(np.random.lognormal(8, 2))  # Log-normal for file sizes
            contributors = max(1, int(np.random.pareto(1) + 1))
            contributors = min(contributors, 50)
            
            # Time-based metrics
            created_date = datetime.now() - timedelta(days=repo_age_days)
            last_updated = created_date + timedelta(days=np.random.randint(0, repo_age_days))
            
            # License popularity (realistic distribution)
            licenses = ["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause", "ISC", "None"]
            license_weights = [0.4, 0.2, 0.15, 0.1, 0.05, 0.1]
            license_type = np.random.choice(licenses, p=license_weights)
            
            data.append({
                "repo_id": i,
                "repo_name": f"project_{i:03d}",
                "primary_language": primary_language,
                "repo_type": repo_type,
                "stars": stars,
                "forks": forks,
                "watchers": max(1, int(stars * np.random.uniform(0.8, 1.2))),
                "issues": issues,
                "commits": commits,
                "contributors": contributors,
                "size_kb": size_kb,
                "license": license_type,
                "created_date": created_date,
                "last_updated": last_updated,
                "repo_age_days": repo_age_days,
                "is_active": (datetime.now() - last_updated).days < 30,
            })
        
        df = pd.DataFrame(data)
        
        # Add derived metrics
        df["stars_per_day"] = df["stars"] / df["repo_age_days"]
        df["commits_per_day"] = df["commits"] / df["repo_age_days"]
        df["popularity_score"] = (df["stars"] * 0.4 + df["forks"] * 0.3 + 
                                 df["watchers"] * 0.2 + df["contributors"] * 0.1)
        df["activity_score"] = df["commits_per_day"] * 10 + (df["is_active"].astype(int) * 5)
        df["fork_ratio"] = df["forks"] / (df["stars"] + 1)  # Avoid division by zero
        
        if save_to_file:
            data_dir = get_data_directory("github")
            save_data(df, data_dir / "github_data.csv", "csv")
        
        return df
    
    def generate_activity_timeline(self, n_days: int = 365, save_to_file: bool = True) -> pd.DataFrame:
        """Generate daily activity timeline data."""
        if "random_seed" in self.data_config:
            np.random.seed(self.data_config["random_seed"] + 1)
        
        base_date = datetime(2023, 1, 1)
        data = []
        
        for i in range(n_days):
            date = base_date + timedelta(days=i)
            day_of_week = date.weekday()  # 0 = Monday
            
            # Activity patterns (less on weekends)
            weekend_factor = 0.3 if day_of_week >= 5 else 1.0
            seasonal_factor = 0.8 + 0.4 * np.sin(2 * np.pi * i / 365)  # Yearly cycle
            
            # Generate realistic activity metrics
            commits = int(np.random.poisson(5 * weekend_factor * seasonal_factor))
            pull_requests = int(np.random.poisson(2 * weekend_factor))
            issues_opened = int(np.random.poisson(3 * weekend_factor))
            issues_closed = int(np.random.poisson(2.5 * weekend_factor))
            
            data.append({
                "date": date,
                "day_of_week": day_of_week,
                "commits": commits,
                "pull_requests": pull_requests,
                "issues_opened": issues_opened,
                "issues_closed": issues_closed,
                "net_issues": issues_opened - issues_closed,
                "total_activity": commits + pull_requests + issues_opened + issues_closed,
            })
        
        df = pd.DataFrame(data)
        df["cumulative_commits"] = df["commits"].cumsum()
        df["rolling_avg_activity"] = df["total_activity"].rolling(window=7).mean()
        
        if save_to_file:
            data_dir = get_data_directory("github")
            save_data(df, data_dir / "github_activity.csv", "csv")
        
        return df
    
    def calculate_language_statistics(self, data: pd.DataFrame) -> Dict[str, any]:
        """Calculate language-based statistics."""
        language_stats = data.groupby("primary_language").agg({
            "stars": ["count", "mean", "sum"],
            "forks": ["mean", "sum"],
            "commits": "mean",
            "contributors": "mean",
            "popularity_score": "mean",
        }).round(2)
        
        # Flatten column names
        language_stats.columns = ["_".join(col).strip() for col in language_stats.columns]
        
        return {
            "language_distribution": data["primary_language"].value_counts().to_dict(),
            "language_metrics": language_stats.to_dict(),
            "most_popular_language": data.groupby("primary_language")["stars"].sum().idxmax(),
            "most_active_language": data.groupby("primary_language")["commits"].sum().idxmax(),
        }