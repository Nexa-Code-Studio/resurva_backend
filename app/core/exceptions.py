class BaseAppException(Exception):
    """Base exception class for all custom application errors."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class EntityNotFoundException(BaseAppException):
    """Raised when a database record is missing."""
    def __init__(self, entity_name: str, identifier: str):
        super().__init__(f"{entity_name} with identity '{identifier}' not found.", status_code=404)


class BusinessRuleValidationException(BaseAppException):
    """Raised when a business action violates predefined constraint rules."""
    pass
