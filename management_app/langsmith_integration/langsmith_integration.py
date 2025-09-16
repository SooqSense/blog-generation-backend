"""
LangSmith Integration Service for SooqSense Blog Generation.

Provides centralized LangSmith tracing functionality for all blog generation agents
including Blog Writer, LinkedIn Post Generator, Image Generator, and News Analyzer.
"""

import os
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from functools import wraps
from contextlib import contextmanager

from langsmith import Client
from langsmith.run_helpers import traceable
from langchain.callbacks import LangChainTracer
from langchain.callbacks.manager import CallbackManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class LangSmithIntegration:
    """Centralized LangSmith integration service for Blog Generation agents."""
    
    def __init__(self):
        """Initialize LangSmith integration."""
        self._client = None
        self._tracer = None
        self._callback_manager = None
        self._initialized = False
        
        # Configuration from environment
        self.enabled = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
        self.api_key = os.getenv("LANGSMITH_API_KEY")
        self.project_name = os.getenv("LANGSMITH_PROJECT", "sooqsense-blog-generation")
        self.endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
        self.workspace_id = os.getenv("LANGSMITH_WORKSPACE_ID")
        
        print("💰 Initializing LangSmith Blog Generation Integration...")
        print(f"📊 Configuration:")
        print(f"   - Enabled: {self.enabled}")
        print(f"   - Project: {self.project_name}")
        print(f"   - API Key: {'✅' if self.api_key else '❌'}")
        
        # Initialize if configured
        if self.is_langsmith_configured():
            self._initialize_langsmith()
    
    def is_langsmith_configured(self) -> bool:
        """Check if LangSmith is properly configured."""
        return bool(self.enabled and self.api_key and self.project_name)
    
    def _initialize_langsmith(self):
        """Initialize LangSmith client and tracer."""
        try:
            # Set environment variables for LangSmith
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.api_key
            os.environ["LANGCHAIN_PROJECT"] = self.project_name
            os.environ["LANGCHAIN_ENDPOINT"] = self.endpoint
            
            if self.workspace_id:
                os.environ["LANGCHAIN_WORKSPACE_ID"] = self.workspace_id
            
            # Initialize LangSmith client
            self._client = Client(
                api_url=self.endpoint,
                api_key=self.api_key
            )
            
            # Initialize tracer
            self._tracer = LangChainTracer(
                project_name=self.project_name,
                client=self._client
            )
            
            # Initialize callback manager
            self._callback_manager = CallbackManager([self._tracer])
            
            self._initialized = True
            print(f"✅ LangSmith integration initialized for project: {self.project_name}")
            
        except Exception as e:
            print(f"❌ Failed to initialize LangSmith: {str(e)}")
            logger.error(f"LangSmith initialization error: {str(e)}")
            self._initialized = False
    
    @property
    def is_enabled(self) -> bool:
        """Check if LangSmith tracing is enabled and initialized."""
        return self._initialized and self.is_langsmith_configured()
    
    @property
    def callback_manager(self) -> Optional[CallbackManager]:
        """Get the callback manager for LangChain operations."""
        return self._callback_manager if self.is_enabled else None
    
    @property
    def client(self) -> Optional[Client]:
        """Get the LangSmith client."""
        return self._client if self.is_enabled else None
    
    def create_run_metadata(self, agent_name: str, operation: str, **kwargs) -> Dict[str, Any]:
        """Create standardized metadata for LangSmith runs."""
        metadata = {
            "agent_name": agent_name,
            "operation": operation,
            "timestamp": datetime.now().isoformat(),
            "app_name": "SooqSense Blog Generator",
            "app_version": "1.0.0",
            "project": self.project_name
        }
        
        # Add any additional metadata
        metadata.update(kwargs)
        
        return metadata

    def trace_agent_operation(
        self,
        agent_name: str,
        operation: str,
        inputs: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ):
        """
        Decorator factory for tracing agent operations.
        
        Args:
            agent_name: Name of the agent (e.g., "BlogWriter", "LinkedInGenerator")
            operation: Operation being performed (e.g., "generate_blog", "create_post")
            inputs: Input data for the operation
            metadata: Additional metadata for the trace
        """
        def decorator(func: Callable):
            if not self.is_enabled:
                # Return original function if tracing is disabled
                return func
            
            @wraps(func)
            @traceable(
                run_type="chain",
                name=f"{agent_name}_{operation}",
                metadata=self.create_run_metadata(
                    agent_name=agent_name,
                    operation=operation,
                    **(metadata or {})
                )
            )
            async def async_wrapper(*args, **kwargs):
                try:
                    # Log operation start
                    logger.debug(f"🔍 LangSmith tracing {agent_name}.{operation}")
                    
                    # Execute the function
                    result = await func(*args, **kwargs)
                    
                    # Log successful completion
                    logger.debug(f"✅ LangSmith trace completed for {agent_name}.{operation}")
                    
                    return result
                    
                except Exception as e:
                    # Log error
                    logger.error(f"❌ LangSmith trace error in {agent_name}.{operation}: {str(e)}")
                    raise
            
            @wraps(func)
            @traceable(
                run_type="chain",
                name=f"{agent_name}_{operation}",
                metadata=self.create_run_metadata(
                    agent_name=agent_name,
                    operation=operation,
                    **(metadata or {})
                )
            )
            def sync_wrapper(*args, **kwargs):
                try:
                    # Log operation start
                    logger.debug(f"🔍 LangSmith tracing {agent_name}.{operation}")
                    
                    # Execute the function
                    result = func(*args, **kwargs)
                    
                    # Log successful completion
                    logger.debug(f"✅ LangSmith trace completed for {agent_name}.{operation}")
                    
                    return result
                    
                except Exception as e:
                    # Log error
                    logger.error(f"❌ LangSmith trace error in {agent_name}.{operation}: {str(e)}")
                    raise
            
            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    @contextmanager
    def trace_context(self, run_name: str, inputs: Dict[str, Any] = None, metadata: Dict[str, Any] = None):
        """
        Context manager for manual tracing of code blocks.
        
        Usage:
            with langsmith.trace_context("blog_processing", inputs={"topic": topic}):
                # Your code here
                result = process_blog_content(topic)
        """
        if not self.is_enabled:
            yield None
            return
        
        try:
            # Create run context
            run_metadata = self.create_run_metadata("Manual", run_name, **(metadata or {}))
            
            logger.debug(f"🔍 LangSmith manual trace started: {run_name}")
            
            # Use traceable context
            with traceable(
                run_type="chain",
                name=run_name,
                inputs=inputs or {},
                metadata=run_metadata
            ):
                yield self
            
            logger.debug(f"✅ LangSmith manual trace completed: {run_name}")
            
        except Exception as e:
            logger.error(f"❌ LangSmith manual trace error in {run_name}: {str(e)}")
            raise
    
    def log_agent_metrics(
        self,
        agent_name: str,
        operation: str,
        metrics: Dict[str, Any],
        session_id: Optional[str] = None
    ):
        """Log custom metrics for agent operations."""
        if not self.is_enabled:
            return
        
        try:
            # Create metrics payload
            metrics_data = {
                "agent_name": agent_name,
                "operation": operation,
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "metrics": metrics
            }
            
            # Log metrics (LangSmith will capture this through tracing)
            logger.info(f"📊 Agent Metrics [{agent_name}.{operation}]: {metrics}")
            
        except Exception as e:
            logger.error(f"❌ Failed to log agent metrics: {str(e)}")
    
    def create_agent_session(self, agent_name: str, session_metadata: Dict[str, Any] = None) -> Optional[str]:
        """Create a new session for agent operations."""
        if not self.is_enabled:
            return None
        
        try:
            session_id = f"{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Log session creation
            logger.info(f"🆔 Created LangSmith session: {session_id} for {agent_name}")
            
            return session_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create agent session: {str(e)}")
            return None
    
    def get_trace_url(self, run_id: str) -> Optional[str]:
        """Get the LangSmith trace URL for a specific run."""
        if not self.is_enabled:
            return None
        
        try:
            base_url = self.endpoint.replace("/api", "")
            workspace_part = f"/o/{self.workspace_id}" if self.workspace_id else ""
            return f"{base_url}{workspace_part}/projects/p/{self.project_name}/r/{run_id}"
        except Exception as e:
            logger.error(f"❌ Failed to generate trace URL: {str(e)}")
            return None
    
    def log_cost_info(self, operation: str, model: str, tokens_used: int = None, cost_estimate: float = None, additional_data: Dict[str, Any] = None):
        """Log cost information for operations - integrates with traceable decorators."""
        try:
            cost_data = {
                "operation": operation,
                "model": model,
                "tokens_used": tokens_used,
                "cost_estimate": cost_estimate,
                "timestamp": datetime.now().isoformat()
            }
            
            if additional_data:
                cost_data.update(additional_data)
            
            # Log to console for immediate feedback
            if cost_estimate and tokens_used:
                print(f"💰 Cost: {operation} | Model: {model} | Tokens: {tokens_used} | ${cost_estimate:.6f}")
            elif cost_estimate:
                print(f"💰 Cost: {operation} | Model: {model} | ${cost_estimate:.6f}")
            else:
                print(f"💰 Cost logging: {operation} | Model: {model}")
            
            # Log to structured logging for LangSmith integration
            logger.info(f"LangSmith Cost Tracking: {cost_data}")
            
        except Exception as e:
            print(f"⚠️  Cost logging error: {str(e)}")
            logger.error(f"Error logging cost info: {str(e)}")


# Global LangSmith integration instance
print("🌟 Creating LangSmith Blog Generation Integration...")
langsmith_integration = LangSmithIntegration()


# Convenience decorators for different agent types
def trace_blog_writer(operation: str, metadata: Dict[str, Any] = None):
    """Decorator for Blog Writer operations."""
    return langsmith_integration.trace_agent_operation("BlogWriter", operation, metadata=metadata)


def trace_linkedin_generator(operation: str, metadata: Dict[str, Any] = None):
    """Decorator for LinkedIn Post Generator operations."""
    return langsmith_integration.trace_agent_operation("LinkedInGenerator", operation, metadata=metadata)


def trace_image_generator(operation: str, metadata: Dict[str, Any] = None):
    """Decorator for Image Generator operations."""
    return langsmith_integration.trace_agent_operation("ImageGenerator", operation, metadata=metadata)


def trace_news_analyzer(operation: str, metadata: Dict[str, Any] = None):
    """Decorator for News Analyzer operations."""
    return langsmith_integration.trace_agent_operation("NewsAnalyzer", operation, metadata=metadata)


# Convenience functions for backward compatibility
def trace_context(run_name: str, inputs: Dict[str, Any] = None, metadata: Dict[str, Any] = None):
    """Context manager for manual tracing"""
    return langsmith_integration.trace_context(run_name, inputs, metadata)


def log_cost(operation: str, model: str, tokens_used: int = None, cost_estimate: float = None, additional_data: Dict[str, Any] = None):
    """Log cost information"""
    return langsmith_integration.log_cost_info(operation, model, tokens_used, cost_estimate, additional_data)


# Legacy support - will be deprecated
def trace_llm_call(func_name: str = None):
    """Deprecated: Use trace_blog_writer, trace_linkedin_generator, etc. instead"""
    print("⚠️  trace_llm_call is deprecated. Use specific agent decorators instead.")
    return lambda func: func  # No-op for backward compatibility


# Export convenience functions
__all__ = [
    "LangSmithIntegration",
    "langsmith_integration",
    "trace_blog_writer",
    "trace_linkedin_generator", 
    "trace_image_generator",
    "trace_news_analyzer",
    "trace_context",
    "log_cost",
    "trace_llm_call"  # Deprecated
]