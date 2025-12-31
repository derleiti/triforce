"""
Circuit Breaker, Cycle Detector & Rate Limiter v2.60

Provides resilience patterns for the TriForce LLM Mesh:
- Circuit Breaker: Prevents cascading failures with automatic fallback
- Cycle Detector: Prevents infinite LLM call loops
- Rate Limiter: Prevents API overload
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional
import logging

logger = logging.getLogger("ailinux.triforce.circuit_breaker")


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


# Fallback mapping: if LLM X fails, try LLM Y
FALLBACK_MAPPING: Dict[str, str] = {
    "gemini": "kimi",
    "kimi": "gemini",
    "deepseek": "qwen",
    "qwen": "deepseek",
    "mistral": "cogito",
    "cogito": "mistral",
    "nova": "gemini",
    "glm": "minimax",
    "minimax": "glm",
    "claude": "deepseek",
}


@dataclass
class CircuitBreaker:
    """Circuit breaker for a single LLM endpoint"""
    llm_id: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None

    # Configuration
    failure_threshold: int = 5          # Failures before opening
    recovery_timeout: int = 60          # Seconds before trying again
    half_open_max_calls: int = 3        # Successful calls to close

    def is_available(self) -> bool:
        """Check if this circuit allows requests"""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self.last_failure:
                # Use timezone-aware datetime for consistency
                now = datetime.now(timezone.utc) if self.last_failure.tzinfo else datetime.utcnow()
                elapsed = (now - self.last_failure).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(f"Circuit {self.llm_id}: OPEN -> HALF_OPEN (recovery attempt)")
                    return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return self.success_count < self.half_open_max_calls

        return False

    def record_success(self):
        """Record a successful call"""
        self.success_count += 1
        self.last_success = datetime.utcnow()

        if self.state == CircuitState.HALF_OPEN:
            if self.success_count >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit {self.llm_id}: HALF_OPEN -> CLOSED (recovered)")

        elif self.state == CircuitState.CLOSED:
            # Gradual reset of failure count on success
            if self.failure_count > 0:
                self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record a failed call"""
        self.last_failure = datetime.utcnow()
        self.failure_count += 1

        if self.state == CircuitState.HALF_OPEN:
            # Immediate open on failure during half-open
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit {self.llm_id}: HALF_OPEN -> OPEN (failure during recovery)")

        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit {self.llm_id}: CLOSED -> OPEN (threshold reached)")

    def get_fallback(self) -> Optional[str]:
        """Get fallback LLM for this one"""
        return FALLBACK_MAPPING.get(self.llm_id)

    def get_status(self) -> Dict:
        """Get circuit status as dict"""
        return {
            "llm_id": self.llm_id,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "fallback": self.get_fallback(),
        }


class CircuitBreakerRegistry:
    """Registry of all circuit breakers"""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(self, llm_id: str) -> CircuitBreaker:
        """Get or create a circuit breaker for an LLM"""
        key = llm_id.lower()
        if key not in self._breakers:
            self._breakers[key] = CircuitBreaker(llm_id=key)
        return self._breakers[key]

    def is_available(self, llm_id: str) -> bool:
        """Check if an LLM is available"""
        return self.get_breaker(llm_id).is_available()

    def record_success(self, llm_id: str):
        """Record a successful call to an LLM"""
        self.get_breaker(llm_id).record_success()

    def record_failure(self, llm_id: str):
        """Record a failed call to an LLM"""
        self.get_breaker(llm_id).record_failure()

    def get_fallback(self, llm_id: str) -> Optional[str]:
        """Get available fallback for an LLM"""
        fallback = self.get_breaker(llm_id).get_fallback()
        if fallback and self.is_available(fallback):
            return fallback
        return None

    def get_all_status(self) -> List[Dict]:
        """Get status of all circuit breakers"""
        return [breaker.get_status() for breaker in self._breakers.values()]

    def reset(self, llm_id: str):
        """Reset a circuit breaker to closed state"""
        if llm_id.lower() in self._breakers:
            breaker = self._breakers[llm_id.lower()]
            breaker.state = CircuitState.CLOSED
            breaker.failure_count = 0
            breaker.success_count = 0
            logger.info(f"Circuit {llm_id}: manually reset to CLOSED")

    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            breaker.state = CircuitState.CLOSED
            breaker.failure_count = 0
            breaker.success_count = 0
        logger.info("All circuits reset to CLOSED")


@dataclass
class CycleDetector:
    """Detects and prevents LLM call cycles"""
    max_depth: int = 10
    _active_chains: Dict[str, List[str]] = field(default_factory=dict)

    def start_chain(self, trace_id: str, llm_id: str) -> bool:
        """Start or continue a call chain. Returns False if cycle detected."""
        if trace_id not in self._active_chains:
            self._active_chains[trace_id] = []

        chain = self._active_chains[trace_id]

        # Check for cycle (LLM already in chain)
        if llm_id in chain:
            logger.warning(f"Cycle detected in trace {trace_id}: {' -> '.join(chain)} -> {llm_id}")
            return False

        # Check for max depth
        if len(chain) >= self.max_depth:
            logger.warning(f"Max depth {self.max_depth} reached in trace {trace_id}")
            return False

        chain.append(llm_id)
        return True

    def add_to_chain(self, trace_id: str, llm_id: str) -> bool:
        """Alias for start_chain for compatibility"""
        return self.start_chain(trace_id, llm_id)

    def end_chain(self, trace_id: str):
        """End and cleanup a call chain"""
        self._active_chains.pop(trace_id, None)

    def pop_from_chain(self, trace_id: str):
        """Remove last LLM from chain (for unwinding)"""
        if trace_id in self._active_chains and self._active_chains[trace_id]:
            self._active_chains[trace_id].pop()

    def get_chain(self, trace_id: str) -> List[str]:
        """Get the current call chain"""
        return self._active_chains.get(trace_id, [])

    def get_chain_depth(self, trace_id: str) -> int:
        """Get current depth of a chain"""
        return len(self.get_chain(trace_id))

    def is_in_chain(self, trace_id: str, llm_id: str) -> bool:
        """Check if an LLM is already in the chain"""
        return llm_id in self.get_chain(trace_id)

    def get_active_chains(self) -> Dict[str, List[str]]:
        """Get all active chains (for debugging)"""
        return dict(self._active_chains)


@dataclass
class RateLimiter:
    """Rate limiting for LLM calls"""
    default_rpm: int = 60  # Requests per minute

    # Per-LLM rate limits (can be customized)
    llm_limits: Dict[str, int] = field(default_factory=lambda: {
        "gemini": 100,
        "kimi": 30,
        "nova": 120,
        "deepseek": 60,
        "qwen": 60,
        "claude": 50,
        "mistral": 60,
        "cogito": 40,
        "glm": 40,
        "minimax": 40,
    })

    _requests: Dict[str, List[datetime]] = field(default_factory=dict)

    def is_allowed(self, llm_id: str) -> bool:
        """Check if a request is allowed under rate limit"""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=1)
        key = llm_id.lower()

        # Initialize if needed
        if key not in self._requests:
            self._requests[key] = []

        # Clean old requests outside window
        self._requests[key] = [
            t for t in self._requests[key]
            if t > window_start
        ]

        # Get limit for this LLM
        limit = self.llm_limits.get(key, self.default_rpm)

        # Check if under limit
        if len(self._requests[key]) >= limit:
            logger.debug(f"Rate limit reached for {llm_id}: {len(self._requests[key])}/{limit}")
            return False

        # Record this request
        self._requests[key].append(now)
        return True

    def get_wait_time(self, llm_id: str) -> float:
        """Get seconds to wait before next allowed request"""
        key = llm_id.lower()

        if key not in self._requests or not self._requests[key]:
            return 0.0

        # Get oldest request in window
        oldest = min(self._requests[key])
        wait = 60 - (datetime.utcnow() - oldest).total_seconds()
        return max(0.0, wait)

    def get_current_usage(self, llm_id: str) -> Dict:
        """Get current rate limit usage for an LLM"""
        key = llm_id.lower()
        limit = self.llm_limits.get(key, self.default_rpm)

        now = datetime.utcnow()
        window_start = now - timedelta(minutes=1)

        if key in self._requests:
            current = len([t for t in self._requests[key] if t > window_start])
        else:
            current = 0

        return {
            "llm_id": llm_id,
            "current": current,
            "limit": limit,
            "remaining": max(0, limit - current),
            "reset_in": self.get_wait_time(llm_id),
        }

    def set_limit(self, llm_id: str, rpm: int):
        """Set custom rate limit for an LLM"""
        self.llm_limits[llm_id.lower()] = rpm

    def get_all_usage(self) -> List[Dict]:
        """Get usage for all tracked LLMs"""
        return [
            self.get_current_usage(llm_id)
            for llm_id in self.llm_limits.keys()
        ]


# Singleton instances
circuit_registry = CircuitBreakerRegistry()
cycle_detector = CycleDetector()
rate_limiter = RateLimiter()
