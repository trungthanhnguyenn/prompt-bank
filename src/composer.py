"""
Template Composer for the Multi-Model Prompt Engine.

Responsible for template hierarchy resolution, priority-based composition,
override application, and variable substitution.
"""

import logging
from typing import Dict, List
from datetime import datetime

from .models import Template, PromptRequest
from .loader import TemplateLoader
from .utils import merge_content_by_category, replace_variables


class TemplateComposer:
    """Template composer with hierarchical composition and override support."""
    
    def __init__(self, loader: TemplateLoader):
        self.loader = loader
        self.logger = logging.getLogger(__name__)
    
    def compose_system_prompt(self, request: PromptRequest, model_family: str) -> str:
        """Compose system prompt from applicable templates."""
        
        self.logger.debug(f"Composing system prompt for model {request.model_id}, tenant {request.tenant_id}")
        
        # Get applicable templates
        templates = self._get_applicable_templates(request, model_family)
        
        if not templates:
            self.logger.warning("No applicable templates found")
            return ""
        
        # Apply tenant overrides
        self._apply_tenant_overrides(templates, request.tenant_id)
        
        # Sort by priority (higher first)
        templates.sort(key=lambda t: t.priority, reverse=True)
        
        # Compose content by category
        system_parts = []
        
        # Group templates by category
        categories = ["system", "persona", "safety", "instruction", "constraint"]
        
        for category in categories:
            category_templates = [t for t in templates if t.category == category]
            if category_templates:
                category_content = self._compose_category(
                    category_templates, category, model_family, request.context
                )
                if category_content:
                    system_parts.append(category_content)
        
        final_prompt = "\n\n".join(system_parts).strip()
        
        self.logger.debug(f"Composed system prompt with {len(system_parts)} categories, {len(final_prompt)} characters")
        
        return final_prompt
    
    def _get_applicable_templates(self, request: PromptRequest, model_family: str) -> List[Template]:
        """Get templates applicable to this request."""
        
        templates = []
        global_templates = self.loader.get_global_templates()
        
        for template in global_templates.values():
            # Check if template applies to this prompt type
            if template.applies_to and request.prompt_type.value not in template.applies_to:
                self.logger.debug(f"Template {template.id} does not apply to prompt type {request.prompt_type.value}")
                continue
                
            # Check model compatibility
            if not self._is_model_compatible(template, model_family):
                self.logger.debug(f"Template {template.id} not compatible with model family {model_family}")
                continue
                
            templates.append(template)
        
        self.logger.debug(f"Found {len(templates)} applicable templates")
        return templates
    
    def _is_model_compatible(self, template: Template, model_family: str) -> bool:
        """Check if template is compatible with model family."""
        # If no model overrides specified, template is universal
        if not template.model_overrides:
            return True
            
        # Check if model family has specific override
        return model_family in template.model_overrides
    
    def _apply_tenant_overrides(self, templates: List[Template], tenant_id: str):
        """Apply tenant-specific overrides to templates."""
        if not tenant_id:
            return
            
        overrides = self.loader.get_tenant_overrides(tenant_id)
        
        if not overrides:
            self.logger.debug(f"No overrides found for tenant {tenant_id}")
            return
        
        self.logger.debug(f"Applying {len(overrides)} overrides for tenant {tenant_id}")
        
        for template in templates:
            if template.id in overrides:
                override = overrides[template.id]
                
                # Add additional rules
                if "additional_rules" in override:
                    template.content.rules.extend(override["additional_rules"])
                    self.logger.debug(f"Added {len(override['additional_rules'])} rules to {template.id}")
                
                # Adjust priority
                if "priority_adjustment" in override:
                    template.priority += override["priority_adjustment"]
                    self.logger.debug(f"Adjusted priority of {template.id} by {override['priority_adjustment']}")
    
    def _compose_category(self, templates: List[Template], category: str, 
                         model_family: str, context: Dict) -> str:
        """Compose templates for a specific category."""
        
        content_parts = []
        
        for template in templates:
            content = self._get_template_content(template, model_family, context)
            if content:
                content_parts.append(content)
        
        # Merge content based on category rules
        return merge_content_by_category(content_parts, category)
    
    def _get_template_content(self, template: Template, model_family: str, context: Dict) -> str:
        """Get content for template, applying model overrides and variables."""
        
        # Start with base content
        content = template.content.instruction
        
        # Apply model-specific override if exists
        if model_family in template.model_overrides:
            override = template.model_overrides[model_family]
            if "instruction" in override:
                content = override["instruction"]
                self.logger.debug(f"Applied model override for {template.id}")
        
        # Add rules if any
        if template.content.rules:
            rules_text = "\n".join(f"- {rule}" for rule in template.content.rules)
            content = f"{content}\n\n{rules_text}"
        
        # Replace variables
        content = replace_variables(content, template.variables, context)
        
        return content
    
    def get_template_hierarchy(self, request: PromptRequest, model_family: str) -> Dict:
        """Get template hierarchy information for debugging."""
        
        templates = self._get_applicable_templates(request, model_family)
        
        # Apply tenant overrides
        self._apply_tenant_overrides(templates, request.tenant_id)
        
        # Sort by priority
        templates.sort(key=lambda t: t.priority, reverse=True)
        
        hierarchy = {
            "prompt_type": request.prompt_type.value,
            "model_family": model_family,
            "tenant_id": request.tenant_id,
            "templates": []
        }
        
        for template in templates:
            hierarchy["templates"].append({
                "id": template.id,
                "name": template.name,
                "category": template.category,
                "priority": template.priority,
                "immutable": template.immutable,
                "applies_to": template.applies_to
            })
        
        return hierarchy
    
    def validate_template_composition(self, request: PromptRequest, model_family: str) -> Dict:
        """Validate template composition and return validation results."""
        
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "template_count": 0,
            "categories": set()
        }
        
        try:
            templates = self._get_applicable_templates(request, model_family)
            validation_result["template_count"] = len(templates)
            
            if not templates:
                validation_result["warnings"].append("No applicable templates found")
            
            # Check for required categories
            required_categories = ["system", "safety"]
            found_categories = set()
            
            for template in templates:
                found_categories.add(template.category)
                validation_result["categories"].add(template.category)
                
                # Check for immutable templates
                if template.immutable and template.priority < 900:
                    validation_result["warnings"].append(
                        f"Immutable template {template.id} has low priority {template.priority}"
                    )
            
            # Check for missing required categories
            for category in required_categories:
                if category not in found_categories:
                    validation_result["warnings"].append(f"Missing required category: {category}")
            
            # Check for priority conflicts
            priorities = [t.priority for t in templates]
            if len(priorities) != len(set(priorities)):
                validation_result["warnings"].append("Duplicate priorities found")
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation failed: {str(e)}")
        
        return validation_result
