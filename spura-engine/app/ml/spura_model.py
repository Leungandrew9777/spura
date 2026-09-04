# spura-engine/ml/spura_model.py
import numpy as np
import pandas as pd
from typing import Dict, List
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
import joblib
import os

class SpuraPredictionModel:
    def __init__(self, league_code: str):
        self.league_code = league_code
        self.model = None
        self.feature_columns = [
            'rolling_xg_5', 'rolling_xg_10', 'rolling_xg_20',
            'opp_defense_rating', 'is_home', 'is_penalty_taker',
            'match_expected_goals', 'player_shots_per90',
            'player_sot_per90', 'minutes_played'
        ]
    
    def prepare_features(self, player_data: List[Dict]) -> pd.DataFrame:
        """Prepare feature matrix from player statistics"""
        df = pd.DataFrame(player_data)
        
        # Calculate rolling averages
        df['rolling_xg_5'] = df.groupby('player_id')['xg'].rolling(5).mean().reset_index(0, drop=True)
        df['rolling_xg_10'] = df.groupby('player_id')['xg'].rolling(10).mean().reset_index(0, drop=True)
        df['rolling_xg_20'] = df.groupby('player_id')['xg'].rolling(20).mean().reset_index(0, drop=True)
        
        # Calculate opponent defense rating (Dixon-Coles style)
        df['opp_defense_rating'] = df.apply(self._calculate_defense_rating, axis=1)
        
        # Convert to expected goals
        df['match_expected_goals'] = df['opp_defense_rating'] * 2.5
        
        # Add penalty taker indicator
        df['is_penalty_taker'] = df['is_penalty_taker'].astype(int)
        
        return df[self.feature_columns]
    
    def _calculate_defense_rating(self, row) -> float:
        """Calculate opponent defensive strength based on historical data"""
        # This would use the Dixon-Coles approach with opponent's
        # goals conceded and shots conceded data
        # Simplified implementation
        return 1.2
    
    def train(self, training_data: pd.DataFrame) -> Dict:
        """Train the prediction model"""
        # Split data
        X = training_data[self.feature_columns]
        y = training_data['goal_scored']
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Create and train model
        base_model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=3
        )
        
        # Calibrate probabilities
        self.model = CalibratedClassifierCV(
            base_model, method='isotonic', cv=3
        )
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict_proba(X_test)[:, 1]
        
        metrics = {
            'brier_score': brier_score_loss(y_test, y_pred),
            'log_loss': log_loss(y_test, y_pred),
            'training_samples': len(X_train),
            'test_samples': len(X_test)
        }
        
        # Save model
        self.save_model()
        
        return metrics
    
    def predict(self, features: pd.DataFrame) -> List[Dict]:
        """Make predictions for players"""
        probabilities = self.model.predict_proba(features)[:, 1]
        
        results = []
        for prob in probabilities:
            results.append({
                'probability': float(prob),
                'fair_odds': float(1/prob) if prob > 0 else float('inf')
            })
        
        return results
    
    def save_model(self):
        """Save model to disk"""
        model_path = f"models/{self.league_code}_model.pkl"
        os.makedirs('models', exist_ok=True)
        joblib.dump(self.model, model_path)
    
    def load_model(self):
        """Load trained model"""
        model_path = f"models/{self.league_code}_model.pkl"
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
            return True
        return False