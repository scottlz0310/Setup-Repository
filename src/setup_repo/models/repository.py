"""Repository model for GitHub repositories."""

from datetime import datetime

from pydantic import BaseModel


class Repository(BaseModel):
    """GitHub repository information."""

    name: str
    full_name: str
    clone_url: str
    ssh_url: str
    default_branch: str = "main"
    private: bool = False
    archived: bool = False
    fork: bool = False
    pushed_at: datetime | None = None

    def get_clone_url(self, use_https: bool = False) -> str:
        """Get the clone URL based on preference.

        Args:
            use_https: If True, return HTTPS URL, otherwise SSH URL

        Returns:
            Clone URL string
        """
        return self.clone_url if use_https else self.ssh_url
