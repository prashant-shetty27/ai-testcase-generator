from pydantic import BaseModel, Field
from typing import List, Optional


class TestGenerationRequest(BaseModel):
    requirement: str = Field(..., min_length=5, description="Requirement text must not be empty")
    template: str = "manual"

    platforms: Optional[List[str]] = [
        "web",
        "mobile_web",
        "android_app",
        "ios_app"
    ]

    include_platform_tests: bool = True
    include_boundary_tests: bool = True
    include_parameter_tests: bool = True
    include_e2e_tests: bool = True