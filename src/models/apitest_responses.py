from typing import Any

from pydantic import BaseModel, Field, model_validator


class FailedValidationVM(BaseModel):
    key: str
    type: str
    expectedValue: Any
    actualValue: Any
    message: str | None = None

    @model_validator(mode="after")
    def set_default_message(self) -> FailedValidationVM:
        if self.message is None:
            self.message = (
                f"Validation failed for '{self.key}'. "
                f"Expected: '{self.expectedValue}', but was: '{self.actualValue}'."
            )
        return self


class ApiTestResponseVM(BaseModel):
    requestId: str
    isValidationSuccess: bool | None = None
    failedValidations: list[FailedValidationVM] = Field(default_factory=list)
    originalResponse: dict[str, Any]
    storedVariables: dict[str, Any] = Field(default_factory=dict)
    status: int
    originalRequest: dict[str, Any]

    def add_failure_for_status_code(self, expected: int, actual: int) -> None:
        failure = FailedValidationVM(
            key="Status Code",
            type="equals",
            expectedValue=f"{expected}",
            actualValue=f"{actual}",
            message=f"Expected status code: {expected}, but received: {actual}",
        )
        self.failedValidations.append(failure)
