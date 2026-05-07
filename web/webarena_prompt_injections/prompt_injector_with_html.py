"""
Enhanced prompt injector that supports HTML injection for AdInject attacks.
Based on the original prompt_injector.py but adds HTML injection capability.
"""

import json
import os
from typing import Dict, Any, List
from . import constants as c
from .attack_backends.base import AttackBackend


class EnhancedPromptInjector:
    """Enhanced prompt injector with HTML injection support."""
    
    def __init__(self, attack_backend: AttackBackend):
        self.attack_backend = attack_backend
        
    def inject_prompt(
        self,
        prompt: str,
        attack: Dict[str, Any],
        environment: str,
        injection_format: str = "raw",
    ) -> str:
        """
        Inject a prompt with the specified attack.
        
        Args:
            prompt: The original prompt
            attack: Attack configuration
            environment: Target environment (gitlab/reddit)
            injection_format: Format of injection (raw/markdown/html)
            
        Returns:
            The injected prompt
        """
        # Check if this is an AdInject attack with HTML
        if "injection_html" in attack:
            return self._inject_html_attack(prompt, attack, environment)
        
        # Original WASP injection logic
        if injection_format == "raw":
            return self._raw_inject(prompt, attack, environment)
        elif injection_format == "markdown":
            return self._markdown_inject(prompt, attack, environment)
        else:
            raise ValueError(f"Unknown injection format: {injection_format}")
    
    def _inject_html_attack(self, prompt: str, attack: Dict[str, Any], environment: str) -> str:
        """
        Inject HTML-based attack (AdInject style).
        
        This creates a two-part injection:
        1. HTML content that will be injected into the page
        2. A prompt that tells the agent to continue with the task
        """
        # Get the HTML content
        html_content = attack["injection_html"]
        
        # Substitute parameters in HTML
        for key, value in attack.get("parameters", {}).items():
            html_content = html_content.replace(f"{{{key}}}", str(value))
        
        # Store HTML for backend to inject
        self.attack_backend.set_html_content(html_content)
        
        # Return the original prompt (the HTML will be injected separately)
        return prompt
    
    def _raw_inject(self, prompt: str, attack: Dict[str, Any], environment: str) -> str:
        """Original raw injection logic from WASP."""
        injection = attack["instruction"]
        
        # Substitute parameters
        for key, value in attack.get("parameters", {}).items():
            injection = injection.replace(f"{{{key}}}", str(value))
        
        # Add the injection to the prompt
        if environment == "reddit":
            # For Reddit, inject as a post/comment
            return f"{prompt}\n\n{injection}"
        else:
            # For other environments, inject directly
            return injection
    
    def _markdown_inject(self, prompt: str, attack: Dict[str, Any], environment: str) -> str:
        """Markdown format injection."""
        injection = attack["instruction"]
        
        # Substitute parameters
        for key, value in attack.get("parameters", {}).items():
            injection = injection.replace(f"{{{key}}}", str(value))
        
        # Format as markdown
        formatted_injection = f"\n\n```\n{injection}\n```\n"
        
        return f"{prompt}{formatted_injection}"


def create_enhanced_prompt_injector(attack_backend: AttackBackend) -> EnhancedPromptInjector:
    """Create an enhanced prompt injector instance."""
    return EnhancedPromptInjector(attack_backend)
