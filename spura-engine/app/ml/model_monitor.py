# spura-engine/ml/model_monitor.py
import logging
from typing import Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class ModelMonitor:
    def __init__(self, db: Session):
        self.db = db
        self.metrics_buffer = []
    
    def track_prediction(self, prediction: Dict, actual_result: Dict):
        """Track model performance over time"""
        # Calculate rolling metrics
        self.metrics_buffer.append({
            'timestamp': datetime.now(),
            'prediction': prediction['probability'],
            'actual': actual_result['goal_scored'],
            'league': prediction['league']
        })
        
        # Calculate and store metrics every 100 predictions
        if len(self.metrics_buffer) >= 100:
            self._calculate_and_store_metrics()
    
    def _calculate_and_store_metrics(self):
        """Calculate model performance metrics"""
        recent_predictions = self.metrics_buffer[-100:]
        
        # Calculate Brier score
        brier = sum((p['prediction'] - p['actual'])**2 for p in recent_predictions) / len(recent_predictions)
        
        # Calculate log loss
        log_loss = -sum(
            (p['actual'] * np.log(p['prediction']) + 
             (1 - p['actual']) * np.log(1 - p['prediction']))
            for p in recent_predictions
        ) / len(recent_predictions)
        
        # Store in database
        self._store_metrics({
            'brier_score': brier,
            'log_loss': log_loss,
            'sample_size': len(recent_predictions),
            'timestamp': datetime.now()
        })
        
        # Clear buffer
        self.metrics_buffer = []
    
    def get_model_health(self, league: str) -> Dict:
        """Get current model health status"""
        # Get recent metrics from database
        recent_metrics = self.db.query(ModelMetrics).filter(
            ModelMetrics.league == league,
            ModelMetrics.timestamp >= datetime.now() - timedelta(days=7)
        ).all()
        
        if not recent_metrics:
            return {'status': 'unknown', 'message': 'No recent data'}
        
        # Calculate average metrics
        avg_brier = np.mean([m.brier_score for m in recent_metrics])
        avg_log_loss = np.mean([m.log_loss for m in recent_metrics])
        
        # Determine health status
        if avg_brier < 0.15:
            status = 'excellent'
        elif avg_brier < 0.20:
            status = 'good'
        elif avg_brier < 0.25:
            status = 'fair'
        else:
            status = 'poor'
        
        return {
            'status': status,
            'brier_score': avg_brier,
            'log_loss': avg_log_loss,
            'recommendation': self._get_recommendation(status)
        }
    
    def _get_recommendation(self, status: str) -> str:
        recommendations = {
            'excellent': 'Model performing well, continue current approach',
            'good': 'Model performing adequately, monitor for drift',
            'fair': 'Consider retraining model with recent data',
            'poor': 'Immediate retraining required, check data quality'
        }
        return recommendations.get(status, 'Unknown status')