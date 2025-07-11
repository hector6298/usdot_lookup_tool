from sqlmodel import SQLModel, Field, Column, JSON
from datetime import datetime
from typing import Optional

class OAuthToken(SQLModel, table=True):
    user_id: str = Field(primary_key=True)  # Your app's user ID
    org_id: str = Field(primary_key=True)  # Your app's organization ID, if applicable
    provider: str = Field(index=True)  # e.g. "salesforce", "auth0"
    access_token: str
    refresh_token: Optional[str] = Field(default=None)
    token_type: Optional[str] = Field(default=None)  
    issued_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    valid_until: Optional[datetime] = Field(default=None)
    token_data: dict = Field(default=None, sa_column=Column(JSON)) 
