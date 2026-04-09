"""Intake Agent - Validates user input and determines scrape strategy.

Single Responsibility: Validate and prepare scraping job parameters.
This agent is the entry point of the scraping pipeline, responsible for:
- Validating user-provided URLs and credentials
- Determining the appropriate scraping strategy
- Preparing the job configuration for downstream agents
"""
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from app.agents.base_agent import BaseAgent
from app.core.security_guard import normalize_and_validate_prompt, validate_scrape_url
from app.schemas.scraping_types import ScrapingType


class IntakeAgent(BaseAgent):
    """Validates user input and determines scraping strategy.
    
    Single Responsibility: Input validation and strategy determination.
    
    This agent does NOT perform scraping - it only validates and prepares
    the configuration for the ScraperAgent.
    """
    
    def __init__(self):
        """Initialize the Intake Agent."""
        super().__init__(agent_name="intake_agent")
    
    async def execute(self, input_data: dict) -> dict:
        """Validate user input and determine scrape strategy.
        
        Args:
            input_data: Job configuration containing:
                - url: Target URL to scrape
                - scrape_type: Type of data to extract
                - credentials: Optional login credentials
                - config: Optional job configuration
                
        Returns:
            Structured response with validated configuration and strategy
        """
        # Validate required fields
        validation_error = self.validate_input(input_data, ["url"])
        if validation_error:
            return self.fail_response(error=validation_error)
        
        url = input_data.get("url")
        scrape_type = input_data.get("scrape_type", ScrapingType.GENERAL.value)
        credentials = input_data.get("credentials")
        config = input_data.get("config", {})
        
        # Validate URL format
        url_validation = self._validate_url(url)
        if url_validation:
            return self.fail_response(error=url_validation)
        
        # Validate credentials if provided
        if credentials:
            cred_validation = self._validate_credentials(credentials)
            if cred_validation:
                return self.fail_response(error=cred_validation)
        
        # Determine scraping strategy based on URL and type
        strategy = self._determine_strategy(url, scrape_type, config)
        
        # Build validated job configuration
        runtime_config = dict(config or {})
        if isinstance(runtime_config.get("prompt"), str):
            try:
                runtime_config["prompt"] = normalize_and_validate_prompt(runtime_config.get("prompt"))
            except ValueError as exc:
                return self.fail_response(error=str(exc))
        runtime_config.setdefault("max_pages", 100)
        runtime_config.setdefault("max_depth", 3)
        runtime_config.setdefault("respect_robots_txt", True)
        runtime_config.setdefault("rate_limit_delay", 1.0)
        if "follow_pagination" in runtime_config and "follow_links" not in runtime_config:
            runtime_config["follow_links"] = bool(runtime_config["follow_pagination"])
        elif "follow_links" in runtime_config and "follow_pagination" not in runtime_config:
            runtime_config["follow_pagination"] = bool(runtime_config["follow_links"])
        else:
            runtime_config.setdefault("follow_pagination", True)
            runtime_config.setdefault("follow_links", bool(runtime_config["follow_pagination"]))

        validated_config = {
            "url": url,
            "scrape_type": scrape_type,
            "credentials": credentials,
            "strategy": strategy,
            "config": runtime_config,
        }
        
        return self.success_response(data=validated_config)
    
    def _validate_url(self, url: str) -> Optional[str]:
        """Validate URL format and accessibility.
        
        Args:
            url: URL to validate
            
        Returns:
            Error message if invalid, None otherwise
        """
        return validate_scrape_url(url, field_name="url")
    
    def _validate_credentials(self, credentials: dict) -> Optional[str]:
        """Validate login credentials format.
        
        Per AGENT_RULES.md: Only use provided credentials for login.
        
        Args:
            credentials: Credentials dict with login_url, username, password
            
        Returns:
            Error message if invalid, None otherwise
        """
        if "login_url" in credentials:
            url_error = self._validate_url(credentials["login_url"])
            if url_error:
                return f"Invalid login URL: {url_error}"
        
        # Both username and password must be provided together
        has_username = bool(credentials.get("username"))
        has_password = bool(credentials.get("password"))
        
        if has_username != has_password:
            return "Both username and password must be provided together"
        
        return None
    
    def _determine_strategy(
        self,
        url: str,
        scrape_type: str,
        config: dict
    ) -> Dict[str, Any]:
        """Determine the optimal scraping strategy.
        
        Args:
            url: Target URL
            scrape_type: Type of content to scrape
            config: Job configuration
            
        Returns:
            Strategy configuration for the scraper
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Base strategy
        strategy = {
            "use_javascript": True,  # Default to Playwright for JS rendering
            "wait_for_selector": None,
            "pagination_type": "auto",  # auto-detect pagination
            "extraction_method": "auto",
        }
        
        # Adjust based on scrape type
        if scrape_type == ScrapingType.PDF.value:
            strategy["extraction_method"] = "file_download"
            strategy["file_extensions"] = [".pdf"]
        elif scrape_type == ScrapingType.WORD.value:
            strategy["extraction_method"] = "file_download"
            strategy["file_extensions"] = [".doc", ".docx"]
        elif scrape_type == ScrapingType.EXCEL.value:
            strategy["extraction_method"] = "file_download"
            strategy["file_extensions"] = [".xls", ".xlsx", ".csv"]
        elif scrape_type == ScrapingType.IMAGES.value:
            strategy["extraction_method"] = "media_extraction"
            strategy["media_types"] = ["image"]
        elif scrape_type == ScrapingType.VIDEOS.value:
            strategy["extraction_method"] = "media_extraction"
            strategy["media_types"] = ["video"]
        elif scrape_type == ScrapingType.STRUCTURED.value:
            strategy["extraction_method"] = "structured_data"
            strategy["look_for"] = ["tables", "lists", "json-ld", "microdata"]
        
        return strategy
