"""robots.txt compliance checker.

Per AGENT_RULES.md: Respect robots.txt when enabled.
"""
from typing import Dict, Optional
from urllib.parse import urlparse
import logging

import httpx


logger = logging.getLogger(__name__)


class RobotsChecker:
    """Checks robots.txt compliance for URLs.
    
    Per AGENT_RULES.md: Respect robots.txt when enabled.
    """
    
    def __init__(self):
        """Initialize the robots checker."""
        self._cache: Dict[str, str] = {}
    
    async def is_allowed(self, url: str, user_agent: str = "*") -> bool:
        """Check if a URL is allowed by robots.txt.
        
        Args:
            url: URL to check
            user_agent: User agent to check against
            
        Returns:
            True if allowed, False if disallowed
        """
        try:
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            robots_url = f"{base_url}/robots.txt"
            
            # Get robots.txt content
            robots_content = await self._get_robots_txt(robots_url)
            if not robots_content:
                # No robots.txt, assume allowed
                return True
            
            # Parse and check
            return self._check_allowed(robots_content, parsed.path, user_agent)
            
        except Exception as e:
            logger.warning(f"Error checking robots.txt: {str(e)}")
            # On error, default to allowed
            return True
    
    async def _get_robots_txt(self, robots_url: str) -> Optional[str]:
        """Fetch robots.txt content.
        
        Args:
            robots_url: URL of robots.txt
            
        Returns:
            robots.txt content or None
        """
        # Check cache
        if robots_url in self._cache:
            return self._cache[robots_url]
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(robots_url, timeout=10.0)
                if response.status_code == 200:
                    content = response.text
                    self._cache[robots_url] = content
                    return content
        except Exception as e:
            logger.debug(f"Could not fetch robots.txt: {str(e)}")
        
        return None
    
    def _check_allowed(
        self,
        robots_content: str,
        path: str,
        user_agent: str
    ) -> bool:
        """Check if path is allowed based on robots.txt rules.
        
        Args:
            robots_content: Content of robots.txt
            path: URL path to check
            user_agent: User agent to match
            
        Returns:
            True if allowed, False if disallowed
        """
        lines = robots_content.split("\n")
        current_agent = None
        rules_for_agent = []
        rules_for_all = []
        
        for line in lines:
            line = line.strip().lower()
            
            if line.startswith("user-agent:"):
                agent = line.split(":", 1)[1].strip()
                current_agent = agent
                
            elif line.startswith("disallow:"):
                disallow_path = line.split(":", 1)[1].strip()
                if current_agent == user_agent.lower():
                    rules_for_agent.append(("disallow", disallow_path))
                elif current_agent == "*":
                    rules_for_all.append(("disallow", disallow_path))
                    
            elif line.startswith("allow:"):
                allow_path = line.split(":", 1)[1].strip()
                if current_agent == user_agent.lower():
                    rules_for_agent.append(("allow", allow_path))
                elif current_agent == "*":
                    rules_for_all.append(("allow", allow_path))
        
        # Use agent-specific rules if available, otherwise use wildcard
        rules = rules_for_agent if rules_for_agent else rules_for_all
        
        # Check rules (longer paths take precedence)
        rules.sort(key=lambda x: -len(x[1]))
        
        for rule_type, rule_path in rules:
            if path.startswith(rule_path) or rule_path == "/":
                if rule_type == "disallow" and rule_path:
                    return False
                elif rule_type == "allow":
                    return True
        
        # Default to allowed
        return True
