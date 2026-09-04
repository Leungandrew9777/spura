# spura-engine/app/db/init_db.py
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.db.models import Base
import os

def init_database():
    """Initialize database with schema"""
    
    # Create engine
    engine = create_engine(settings.DATABASE_URL)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Seed leagues data
    seed_leagues(engine)
    
    print("Database initialized successfully!")

def seed_leagues(engine):
    """Seed initial league data"""
    
    leagues = [
        {"code": "EPL", "name": "Premier League", "country": "England"},
        {"code": "SP1", "name": "La Liga", "country": "Spain"},
        {"code": "I1", "name": "Serie A", "country": "Italy"},
        {"code": "D1", "name": "Bundesliga", "country": "Germany"},
        {"code": "F1", "name": "Ligue 1", "country": "France"},
        {"code": "CL", "name": "Champions League", "country": "Europe"},
        {"code": "EL", "name": "Europa League", "country": "Europe"}
    ]
    
    with engine.connect() as conn:
        for league in leagues:
            conn.execute(
                text("""
                    INSERT INTO competitions (code, name, country, is_european)
                    VALUES (:code, :name, :country, :is_european)
                    ON CONFLICT (code) DO NOTHING
                """),
                {
                    "code": league["code"],
                    "name": league["name"],
                    "country": league["country"],
                    "is_european": league["country"] == "Europe"
                }
            )
        conn.commit()

if __name__ == "__main__":
    init_database()