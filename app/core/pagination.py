from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    skip: int = Field(0, ge=0, description="Offset index")
    limit: int = Field(100, ge=1, le=100, description="Page size limit")


class PaginationMetadata(BaseModel):
    page: int = Field(..., description="Current page number (1-based)")
    page_size: int = Field(..., description="Number of items per page")
    total: int = Field(..., description="Total number of items matching filters")
    total_pages: int = Field(..., description="Total number of pages")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T] = Field(..., description="List of paginated items")
    pagination: PaginationMetadata = Field(..., description="Pagination metadata details")

