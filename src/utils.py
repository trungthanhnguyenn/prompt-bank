"""
Utility functions for the Multi-Model Prompt Engine.
"""

import logging
import sys
import os
from datetime import datetime
from typing import Optional
from pathlib import Path


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Setup structured logging for the application."""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / 'app.log', mode='a', encoding='utf-8')
        ]
    )
    
    return logging.getLogger(__name__)


def get_env_var(key: str, default: Optional[str] = None) -> str:
    """Get environment variable with default value."""
    return os.getenv(key, default)


def validate_template_file(file_path: Path) -> bool:
    """Validate that a template file exists and is readable."""
    try:
        if not file_path.exists():
            return False
        if not file_path.is_file():
            return False
        # Try to read the file to ensure it's accessible
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read(1)  # Read one character to test access
        return True
    except (IOError, OSError):
        return False


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations."""
    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    return filename


def format_timestamp(timestamp: Optional[datetime] = None) -> str:
    """Format timestamp for logging and responses."""
    if timestamp is None:
        timestamp = datetime.utcnow()
    return timestamp.isoformat()


def estimate_tokens(text: str, model_family: str) -> int:
    """Estimate token count based on model family and text content."""
    
    # Model-specific token estimations (characters per token)
    estimations = {
        "deepseek-r1": 3.5,  # Mixed Chinese/English
        "gemma": 4.0,        # Primarily English
        "llama3": 3.8        # Primarily English
    }
    
    chars_per_token = estimations.get(model_family, 4.0)
    return max(1, int(len(text) / chars_per_token))


def merge_content_by_category(content_parts: list, category: str) -> str:
    """Merge content parts based on category-specific rules."""
    
    if not content_parts:
        return ""
    
    # Filter out empty content
    valid_parts = [part.strip() for part in content_parts if part.strip()]
    
    if not valid_parts:
        return ""
    
    if category in ["system", "persona"]:
        # Join with periods for system/persona
        return ". ".join(part.rstrip('.') for part in valid_parts) + "."
    
    elif category in ["safety", "constraint"]:
        # Use bullet points for safety/constraints
        return "\n".join(valid_parts)
    
    else:
        # Default: join with double newlines
        return "\n\n".join(valid_parts)


def replace_variables(content: str, variables: list, context: dict) -> str:
    """Replace template variables with context values."""
    
    # Prepare context with system variables
    full_context = context.copy()
    full_context["current_date"] = datetime.now().strftime("%Y年%m月%d日")
    
    # Replace variables using simple substitution
    for var in variables:
        if var in full_context:
            placeholder = "{{ " + var + " }}"
            content = content.replace(placeholder, str(full_context[var]))
    
    return content


def validate_model_id(model_id: str) -> bool:
    """Validate model ID format."""
    import re
    pattern = r'^[a-z0-9\-]+$'
    return bool(re.match(pattern, model_id))


def validate_tenant_id(tenant_id: str) -> bool:
    """Validate tenant ID format."""
    import re
    pattern = r'^[a-z0-9_\-]+$'
    return bool(re.match(pattern, tenant_id))


def get_file_hash(file_path: Path) -> str:
    """Get MD5 hash of file for cache invalidation."""
    import hashlib
    
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except (IOError, OSError):
        return ""


def create_backup(file_path: Path, backup_dir: Path) -> Optional[Path]:
    """Create backup of a file."""
    try:
        if not backup_dir.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = backup_dir / backup_name
        
        import shutil
        shutil.copy2(file_path, backup_path)
        return backup_path
    except (IOError, OSError) as e:
        logging.error(f"Failed to create backup of {file_path}: {e}")
        return None


def restore_backup(backup_path: Path, target_path: Path) -> bool:
    """Restore file from backup."""
    try:
        import shutil
        shutil.copy2(backup_path, target_path)
        return True
    except (IOError, OSError) as e:
        logging.error(f"Failed to restore backup {backup_path}: {e}")
        return False
