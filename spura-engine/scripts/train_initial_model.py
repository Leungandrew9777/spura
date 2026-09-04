# spura-engine/scripts/train_initial_model.py
"""
Train the initial ML model for a specific league.
Start with the Premier League as it has the most data.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import get_db_session
from app.ml.spura_model import SpuraPredictionModel
from app.ml.feature_engineering import FeatureEngineer
from loguru import logger
import pandas as pd

def train_model_for_league(league_code: str = "EPL"):
    """Train model for a specific league"""
    
    logger.info(f"🚀 Training model for {league_code}")
    
    # Get database session
    db = next(get_db_session())
    
    # Initialize feature engineer
    fe = FeatureEngineer(db, league_code)
    
    # Prepare training data
    logger.info("Preparing training data...")
    training_data = fe.prepare_training_data()
    
    logger.info(f"Training data shape: {training_data.shape}")
    logger.info(f"Features: {list(training_data.columns)}")
    
    # Initialize model
    model = SpuraPredictionModel(league_code)
    
    # Train model
    logger.info("Training model...")
    metrics = model.train(training_data)
    
    logger.success(f"✅ Model trained successfully!")
    logger.info(f"📊 Metrics: {metrics}")
    
    # Save model
    model.save_model()
    logger.info(f"💾 Model saved to models/{league_code}_model.pkl")
    
    db.close()
    
    return metrics

if __name__ == "__main__":
    # Train for Premier League first (most data available)
    metrics = train_model_for_league("EPL")
    print("\n" + "="*50)
    print("TRAINING COMPLETE")
    print("="*50)
    print(f"Brier Score: {metrics['brier_score']:.4f}")
    print(f"Log Loss: {metrics['log_loss']:.4f}")
    print(f"Training Samples: {metrics['training_samples']}")
    print(f"Test Samples: {metrics['test_samples']}")