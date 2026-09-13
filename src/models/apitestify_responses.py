from typing import Any
from pydantic import BaseModel, Field, model_validator

class FailedValidationVM(BaseModel):
    key: str
    type: str
    expectedValue: Any
    actualValue: Any
    message: str | None = None

    @model_validator(mode="after")
    def set_default_message(self) -> "FailedValidationVM":
        if self.message is None:
            self.message = (
                f"Validation failed for '{self.key}'. "
                f"Expected: '{self.expectedValue}', but was: '{self.actualValue}'."
            )
        return self

class ApiTestResponseVM(BaseModel):
    requestId: str
    isValidationSuccess: bool
    failedValidations: list[FailedValidationVM] = Field(default_factory=list)
    originalResponse: dict[str, Any]
    storedVariables: dict[str, Any] = Field(default_factory=dict)
    status: int
    originalRequest: dict[str, Any]
