"""Company Service — handles company input parsing and validation.

This follows the FastAPI Backend Builder pattern:
- Services own business logic
- Endpoints delegate to services
"""

from backend.models.schemas import CompanyInput


# ── Constants ─────────────────────────────────────────────────────────────

MAX_BATCH_SIZE = 10


# ── Exceptions ────────────────────────────────────────────────────────────

class ValidationError(Exception):
    """Raised when company input validation fails."""
    pass


class BatchSizeError(ValidationError):
    """Raised when batch size exceeds limit."""
    pass


# ── Service Class ────────────────────────────────────────────────────────

class CompanyService:
    """Service for company input processing and validation."""
    
    def __init__(self):
        pass
    
    def parse_company_input(self, company: CompanyInput) -> CompanyInput:
        """Parse and normalize company input.
        
        Supports "Company Name,domain.com" format in company_name field.
        """
        if company.domain:
            return company
        
        # If company_name contains comma, split to extract domain
        if "," in company.company_name:
            parts = company.company_name.split(",", 1)
            return CompanyInput(
                company_name=parts[0].strip(),
                domain=parts[1].strip() if len(parts) > 1 else None
            )
        
        return company
    
    def validate_batch(self, companies: list[CompanyInput]) -> None:
        """Validate batch input.
        
        Raises:
            BatchSizeError: If batch exceeds maximum size
        """
        if len(companies) > MAX_BATCH_SIZE:
            raise BatchSizeError(
                f"Maximum {MAX_BATCH_SIZE} companies per batch, got {len(companies)}"
            )
    
    def normalize_batch(
        self, companies: list[CompanyInput]
    ) -> list[CompanyInput]:
        """Normalize a batch of company inputs."""
        return [self.parse_company_input(c) for c in companies]
