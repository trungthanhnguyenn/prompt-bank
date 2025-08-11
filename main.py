"""
FastAPI application for the Multi-Model Prompt Engine.

Provides HTTP interface for prompt generation services with comprehensive
error handling, logging, and monitoring capabilities.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.engine import PromptEngine
from src.models import (
    PromptRequest, PromptResponse, PromptType,
    HealthResponse, ModelsResponse, ReloadResponse
)
from src.utils import setup_logging, get_env_var, format_timestamp

# Setup logging
logger = setup_logging(get_env_var("LOG_LEVEL", "INFO"))

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Global engine instance
engine: PromptEngine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global engine
    
    # Startup
    logger.info("Starting Multi-Model Prompt Engine...")
    
    try:
        # Initialize prompt engine
        templates_dir = get_env_var("TEMPLATES_DIR", "templates")
        engine = PromptEngine(templates_dir)
        
        # Warm up templates
        await asyncio.create_task(warm_up_templates())
        
        logger.info("Prompt Engine started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start Prompt Engine: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Prompt Engine...")


async def warm_up_templates():
    """Pre-load templates for faster response times."""
    try:
        models = engine.get_supported_models()
        logger.info(f"Warmed up {len(models)} models")
    except Exception as e:
        logger.error(f"Template warm-up failed: {e}")


# Initialize FastAPI app
app = FastAPI(
    title="Multi-Model Prompt Engine",
    description="Pure Python prompt generation engine supporting DeepSeek-R1, Gemma, and Llama3",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
allowed_origins = get_env_var("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for monitoring."""
    start_time = datetime.utcnow()
    
    response = await call_next(request)
    
    process_time = (datetime.utcnow() - start_time).total_seconds()
    
    logger.info(
        "Request processed",
        extra={
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "process_time": process_time
        }
    )
    
    return response


# Optional API key protection (enabled when API_KEY is set)
def verify_api_key(request: Request):
    api_key_required = get_env_var("API_KEY", None)
    if not api_key_required:
        return  # No API key configured -> open

    provided = request.headers.get("x-api-key")
    if not provided or provided != api_key_required:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing API key")


@app.post("/generate", response_model=PromptResponse)
@limiter.limit("10/minute")
async def generate_prompt(request: Request, prompt_request: PromptRequest, _: None = Depends(verify_api_key)):
    """Generate formatted prompt for specified model."""
    
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        # Run template generation in thread pool for CPU-bound work
        loop = asyncio.get_event_loop()
        
        response = await loop.run_in_executor(
            None, 
            engine.generate_prompt,
            prompt_request
        )
        
        return response
        
    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        logger.error(f"Template not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Prompt generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/models", response_model=ModelsResponse)
async def get_supported_models(_: None = Depends(verify_api_key)):
    """Get list of supported models."""
    
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        models = engine.get_supported_models()
        return ModelsResponse(models=models)
    except Exception as e:
        logger.error(f"Failed to get models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reload", response_model=ReloadResponse)
async def reload_templates(_: None = Depends(verify_api_key)):
    """Reload templates (development only)."""
    
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        # Run reload in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, engine.reload_templates)
        
        return ReloadResponse(
            status="reloaded",
            timestamp=format_timestamp(),
            message="All templates reloaded successfully"
        )
    except Exception as e:
        logger.error(f"Template reload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reload failed: {str(e)}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check endpoint."""
    
    if engine is None:
        return HealthResponse(
            status="unhealthy",
            version="1.0.0",
            models_loaded=0,
            templates_loaded=0,
            error="Engine not initialized"
        )
    
    # Basic stats
    stats = engine.get_engine_stats()

    # Filesystem and memory checks (enhanced health)
    checks_error = None
    try:
        from pathlib import Path
        import psutil

        templates_dir = Path(get_env_var("TEMPLATES_DIR", "templates"))
        fs_ok = templates_dir.exists() and templates_dir.is_dir()

        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        # Add simple threshold from SRS: < 256MB considered healthy
        mem_status = "healthy" if memory_mb < 256 else "warning"

        logger.info(
            "Health details",
            extra={"filesystem_ok": fs_ok, "memory_mb": round(memory_mb, 2), "memory_status": mem_status},
        )
    except Exception as e:
        checks_error = str(e)

    return HealthResponse(
        status=stats.get("status", "healthy") if not checks_error else "unhealthy",
        version=stats.get("version", "1.0.0"),
        models_loaded=stats.get("models_supported", 0),
        templates_loaded=stats.get("templates_loaded", 0),
        timestamp=stats.get("timestamp"),
        error=checks_error,
    )


@app.get("/stats")
async def get_engine_stats(_: None = Depends(verify_api_key)):
    """Get detailed engine statistics."""
    
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        stats = engine.get_engine_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate")
async def validate_template_composition(prompt_request: PromptRequest, _: None = Depends(verify_api_key)):
    """Validate template composition for a request."""
    
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        validation_result = engine.validate_template_composition(prompt_request)
        return validation_result
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/hierarchy")
async def get_template_hierarchy(prompt_request: PromptRequest, _: None = Depends(verify_api_key)):
    """Get template hierarchy information for debugging."""
    
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        hierarchy = engine.get_template_hierarchy(prompt_request)
        return hierarchy
    except Exception as e:
        logger.error(f"Failed to get hierarchy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/backup")
async def backup_templates(_: None = Depends(verify_api_key)):
    """Create backup of all templates."""
    
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        backup_path = engine.backup_templates()
        if backup_path:
            return {
                "status": "success",
                "backup_path": str(backup_path),
                "timestamp": format_timestamp()
            }
        else:
            raise HTTPException(status_code=500, detail="Backup failed")
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test")
async def test_prompt_generation(
    model_id: str,
    user_input: str,
    prompt_type: str = "chat",
    tenant_id: str = None
):
    """Test prompt generation with given parameters."""
    
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        # Convert prompt_type string to enum
        try:
            prompt_type_enum = PromptType(prompt_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid prompt type: {prompt_type}")
        
        result = engine.test_prompt_generation(
            model_id=model_id,
            user_input=user_input,
            prompt_type=prompt_type_enum,
            tenant_id=tenant_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    host = get_env_var("APP_HOST", "0.0.0.0")
    port = int(get_env_var("APP_PORT", "8000"))
    reload = get_env_var("APP_RELOAD", "false").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=get_env_var("LOG_LEVEL", "info").lower()
    )
