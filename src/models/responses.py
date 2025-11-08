"""
Pydantic response models for API endpoints.

All API responses are validated and documented through these models.
"""

from pydantic import BaseModel, Field


class PostcodeResponse(BaseModel):
    """
    Response model for postcode lookup.

    Example:
        {
            "postcode": "3511AB",
            "lat": 52.096065,
            "lon": 5.115926,
            "woonplaats": "Utrecht"
        }
    """
    postcode: str = Field(
        ...,
        description="Dutch postcode (6 characters: 4 digits + 2 letters)",
        examples=["3511AB", "1012AB", "9901EG"]
    )
    lat: float = Field(
        ...,
        description="Latitude in WGS84 coordinate system",
        ge=-90.0,
        le=90.0
    )
    lon: float = Field(
        ...,
        description="Longitude in WGS84 coordinate system",
        ge=-180.0,
        le=180.0
    )
    woonplaats: str = Field(
        ...,
        description="City or town name (Dutch: woonplaats)",
        examples=["Utrecht", "Amsterdam", "Rotterdam"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "postcode": "3511AB",
                    "lat": 52.096065,
                    "lon": 5.115926,
                    "woonplaats": "Utrecht"
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """
    Response model for health check endpoints.

    Example:
        {
            "status": "healthy",
            "database": "connected"
        }
    """
    status: str = Field(
        ...,
        description="Health status",
        examples=["healthy", "unhealthy"]
    )
    database: str = Field(
        ...,
        description="Database connection status",
        examples=["connected", "disconnected"]
    )


class ErrorResponse(BaseModel):
    """
    Standard error response format.

    Example:
        {
            "detail": "Postcode 1000AA not found in database"
        }
    """
    detail: str = Field(
        ...,
        description="Error message describing what went wrong"
    )
