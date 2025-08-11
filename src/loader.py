"""
Template Loader for the Multi-Model Prompt Engine.

Responsible for loading JSON templates from file system, caching templates in memory,
and providing template access methods with hot-reload functionality.
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from functools import lru_cache
import hashlib
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from .models import Template, ModelConfig, TenantConfig
from .utils import validate_template_file, get_file_hash, create_backup


class TemplateLoader:
    """Template loader with caching and hot-reload capabilities."""
    
    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = Path(templates_dir)
        self.logger = logging.getLogger(__name__)
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Initialize caches
        self._global_templates: Dict[str, Template] = {}
        self._model_configs: Dict[str, ModelConfig] = {}
        self._tenant_configs: Dict[str, TenantConfig] = {}
        self._tenant_overrides: Dict[str, Dict] = {}
        self._template_cache = {}
        self._cache_hash = None
        
        # Load all templates
        self._load_all()
    
    def _load_all(self):
        """Load all templates and configurations."""
        try:
            self.logger.info("Loading all templates and configurations...")
            self._load_global_templates()
            self._load_model_configs()
            self._load_tenant_configs()
            self._update_cache_hash()
            self.logger.info("Template loading completed successfully")
        except Exception as e:
            self.logger.error(f"Failed to load templates: {e}")
            raise RuntimeError(f"Failed to load templates: {e}")
    
    def _load_global_templates(self):
        """Load global templates from JSON files."""
        global_dir = self.templates_dir / "global"
        
        if not global_dir.exists():
            raise FileNotFoundError(f"Global templates directory not found: {global_dir}")
        
        self.logger.info(f"Loading global templates from {global_dir}")
        
        for json_file in global_dir.glob("*.json"):
            try:
                if not validate_template_file(json_file):
                    self.logger.warning(f"Skipping invalid template file: {json_file}")
                    continue
                
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    template = Template(**data)
                    self._global_templates[template.id] = template
                    self.logger.debug(f"Loaded global template: {template.id}")
                    
            except Exception as e:
                self.logger.error(f"Failed to load template {json_file}: {e}")
                raise RuntimeError(f"Failed to load template {json_file}: {e}")
    
    def _load_model_configs(self):
        """Load model configurations."""
        models_dir = self.templates_dir / "models"
        
        if not models_dir.exists():
            raise FileNotFoundError(f"Models directory not found: {models_dir}")
        
        self.logger.info(f"Loading model configurations from {models_dir}")
        
        for model_dir in models_dir.iterdir():
            if model_dir.is_dir():
                config_file = model_dir / "config.json"
                if config_file.exists() and validate_template_file(config_file):
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            config = ModelConfig(**data)
                            self._model_configs[config.model_id] = config
                            self.logger.debug(f"Loaded model config: {config.model_id}")
                    except Exception as e:
                        self.logger.error(f"Failed to load model config {config_file}: {e}")
                        raise RuntimeError(f"Failed to load model config {config_file}: {e}")
    
    def _load_tenant_configs(self):
        """Load tenant configurations and overrides."""
        tenants_dir = self.templates_dir / "tenants"
        
        if not tenants_dir.exists():
            self.logger.info("No tenants directory found, skipping tenant configurations")
            return
        
        self.logger.info(f"Loading tenant configurations from {tenants_dir}")
        
        for tenant_dir in tenants_dir.iterdir():
            if tenant_dir.is_dir():
                # Load tenant config
                config_file = tenant_dir / "config.json"
                if config_file.exists() and validate_template_file(config_file):
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            config = TenantConfig(**data)
                            self._tenant_configs[config.tenant_id] = config
                            self.logger.debug(f"Loaded tenant config: {config.tenant_id}")
                    except Exception as e:
                        self.logger.warning(f"Failed to load tenant config {config_file}: {e}")
                
                # Load tenant overrides
                overrides_file = tenant_dir / "overrides.json"
                if overrides_file.exists() and validate_template_file(overrides_file):
                    try:
                        with open(overrides_file, 'r', encoding='utf-8') as f:
                            overrides = json.load(f)
                            self._tenant_overrides[tenant_dir.name] = overrides
                            self.logger.debug(f"Loaded tenant overrides: {tenant_dir.name}")
                    except Exception as e:
                        self.logger.warning(f"Failed to load tenant overrides {overrides_file}: {e}")
    
    def _update_cache_hash(self):
        """Update cache hash for invalidation."""
        hasher = hashlib.md5()
        
        # Hash all template files
        for template_file in self.templates_dir.rglob("*.json"):
            if template_file.is_file():
                hasher.update(str(template_file.stat().st_mtime).encode())
        
        for template_file in self.templates_dir.rglob("*.j2"):
            if template_file.is_file():
                hasher.update(str(template_file.stat().st_mtime).encode())
        
        self._cache_hash = hasher.hexdigest()
    
    def get_global_templates(self) -> Dict[str, Template]:
        """Get all global templates."""
        return self._global_templates.copy()
    
    def get_model_config(self, model_id: str) -> Optional[ModelConfig]:
        """Get model configuration by ID."""
        return self._model_configs.get(model_id)
    
    def get_tenant_config(self, tenant_id: str) -> Optional[TenantConfig]:
        """Get tenant configuration by ID."""
        return self._tenant_configs.get(tenant_id)
    
    def get_tenant_overrides(self, tenant_id: str) -> Dict:
        """Get tenant template overrides."""
        return self._tenant_overrides.get(tenant_id, {})
    
    @lru_cache(maxsize=128)
    def get_jinja_template_cached(self, model_family: str, template_name: str):
        """Get Jinja2 template with LRU cache."""
        return self.get_jinja_template(model_family, template_name)
    
    def get_jinja_template(self, model_family: str, template_name: str):
        """Get Jinja2 template for model family."""
        template_path = f"models/{model_family}/{template_name}.j2"
        try:
            template = self.jinja_env.get_template(template_path)
            self.logger.debug(f"Loaded Jinja template: {template_path}")
            return template
        except TemplateNotFound:
            self.logger.warning(f"Jinja template not found: {template_path}")
            raise FileNotFoundError(f"Jinja template not found: {template_path}")
        except Exception as e:
            self.logger.error(f"Failed to load Jinja template {template_path}: {e}")
            raise
    
    def get_supported_models(self) -> Dict[str, str]:
        """Get list of supported models."""
        return {
            model_id: config.display_name 
            for model_id, config in self._model_configs.items()
        }
    
    def reload_if_changed(self) -> bool:
        """Reload templates only if files have changed."""
        current_hash = self._get_cache_hash()
        
        if current_hash != self._cache_hash:
            self.logger.info("Template files changed, reloading...")
            self.reload()
            return True
        
        return False
    
    def _get_cache_hash(self) -> str:
        """Generate hash of all template files for cache invalidation."""
        hasher = hashlib.md5()
        
        for template_file in self.templates_dir.rglob("*.json"):
            if template_file.is_file():
                hasher.update(str(template_file.stat().st_mtime).encode())
        
        for template_file in self.templates_dir.rglob("*.j2"):
            if template_file.is_file():
                hasher.update(str(template_file.stat().st_mtime).encode())
        
        return hasher.hexdigest()
    
    def reload(self):
        """Reload all templates and configurations."""
        self.logger.info("Reloading all templates and configurations...")
        
        # Clear all caches
        self._global_templates.clear()
        self._model_configs.clear()
        self._tenant_configs.clear()
        self._tenant_overrides.clear()
        self._template_cache.clear()
        
        # Clear Jinja2 cache
        self.jinja_env.cache.clear()
        
        # Reload everything
        self._load_all()
        
        self.logger.info("Template reload completed successfully")
    
    def backup_templates(self, backup_dir: str = "backups") -> Optional[Path]:
        """Create backup of all templates."""
        try:
            backup_path = Path(backup_dir)
            if not backup_path.exists():
                backup_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"templates_backup_{timestamp}"
            final_backup_path = backup_path / backup_name
            
            import shutil
            shutil.copytree(self.templates_dir, final_backup_path)
            
            self.logger.info(f"Templates backed up to {final_backup_path}")
            return final_backup_path
            
        except Exception as e:
            self.logger.error(f"Failed to create template backup: {e}")
            return None
    
    def get_template_stats(self) -> Dict:
        """Get statistics about loaded templates."""
        return {
            "global_templates": len(self._global_templates),
            "model_configs": len(self._model_configs),
            "tenant_configs": len(self._tenant_configs),
            "tenant_overrides": len(self._tenant_overrides),
            "cache_hash": self._cache_hash
        }
