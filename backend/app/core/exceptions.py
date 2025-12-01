from fastapi import HTTPException, status


class HabexaException(HTTPException):
    pass


class NotFoundError(HabexaException):
    def __init__(self, resource: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found"
        )


class UnauthorizedError(HabexaException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message
        )


class ValidationError(HabexaException):
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

