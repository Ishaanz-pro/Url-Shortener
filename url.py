from sqlalchemy import (
    Column, String, DateTime, Integer, 
    ForeignKey, Boolean, Text, BigInteger, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
from app.database import Base

class URL(Base):
    __tablename__ = "urls"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    original_url = Column(Text, nullable=False)
    short_code = Column(String(20), unique=True, nullable=False, index=True)
    custom_alias = Column(String(100), unique=True, nullable=True, index=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Analytics
    click_count = Column(BigInteger, default=0, index=True)
    last_clicked_at = Column(DateTime, nullable=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="urls")
    analytics = relationship("Analytics", back_populates="url", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_user_short_code", "user_id", "short_code"),
        Index("idx_short_code_active", "short_code", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<URL {self.short_code}>"
    
    def is_expired(self) -> bool:
        """Check if URL has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class Analytics(Base):
    __tablename__ = "analytics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    url_id = Column(String, ForeignKey("urls.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Geo data
    country = Column(String(2), nullable=True, index=True)
    city = Column(String(100), nullable=True)
    
    # Device info
    user_agent = Column(Text, nullable=True)
    device_type = Column(String(20), nullable=True, index=True)  # mobile, desktop, tablet
    browser = Column(String(100), nullable=True, index=True)
    os = Column(String(100), nullable=True, index=True)
    
    # Request info
    ip_address = Column(String(45), nullable=True, index=True)
    referrer = Column(Text, nullable=True)
    
    # Timestamps
    clicked_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    url = relationship("URL", back_populates="analytics")
    
    __table_args__ = (
        Index("idx_url_clicked_at", "url_id", "clicked_at"),
        Index("idx_country_device", "country", "device_type"),
    )
    
    def __repr__(self) -> str:
        return f"<Analytics {self.url_id} - {self.clicked_at}>"
