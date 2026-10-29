import os
import re
import threading
import logging
from typing import List, Dict, Optional, Any, Callable
from apify_client import ApifyClient
from apify_client._errors import ApifyApiError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("apify_manager")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


class KeyInfo:
    def __init__(self, key_name: str, token: str):
        self.key_name: str = key_name
        self.token: str = token.strip().strip('"').strip("'")
        self.status: str = "UNKNOWN"  # HEALTHY, EXHAUSTED, INVALID, UNKNOWN
        self.monthly_limit_usd: float = 0.0
        self.monthly_usage_usd: float = 0.0
        self.headroom_usd: float = 0.0
        self.username: str = ""
        self._client: Optional[ApifyClient] = None

    def get_client(self) -> ApifyClient:
        if self._client is None:
            self._client = ApifyClient(self.token)
        return self._client

    def check_balance(self, min_headroom: float = 0.15) -> Dict[str, Any]:
        """
        Calls Apify /v2/users/me to inspect monthly usage and calculate remaining headroom.
        Remaining Headroom = monthlyUsageLimitUsd - monthlyUsageUsd
        """
        client = self.get_client()
        try:
            user_info = client.user().get()
            if not user_info or not isinstance(user_info, dict):
                self.status = "INVALID"
                return {
                    "healthy": False,
                    "key_name": self.key_name,
                    "status": self.status,
                    "reason": "Could not retrieve user info from Apify",
                }

            self.username = user_info.get("username", "") or ""
            usage = float(user_info.get("monthlyUsageUsd", 0.0) or 0.0)

            plan = user_info.get("plan") or {}
            limits = user_info.get("limits") or {}

            limit_raw = (
                plan.get("monthlyUsageLimitUsd")
                or limits.get("monthlyUsageLimitUsd")
                or user_info.get("monthlyUsageLimitUsd")
                or 5.0  # default free tier allowance is $5.00
            )
            limit = float(limit_raw)

            headroom = max(0.0, limit - usage)
            self.monthly_limit_usd = limit
            self.monthly_usage_usd = usage
            self.headroom_usd = headroom

            if headroom >= min_headroom:
                self.status = "HEALTHY"
                return {
                    "healthy": True,
                    "key_name": self.key_name,
                    "username": self.username,
                    "status": self.status,
                    "headroom": round(headroom, 4),
                    "usage": round(usage, 4),
                    "limit": round(limit, 4),
                }
            else:
                self.status = "EXHAUSTED"
                return {
                    "healthy": False,
                    "key_name": self.key_name,
                    "username": self.username,
                    "status": self.status,
                    "headroom": round(headroom, 4),
                    "usage": round(usage, 4),
                    "limit": round(limit, 4),
                    "reason": f"Insufficient credit headroom (${round(headroom, 2)} < ${min_headroom})",
                }

        except ApifyApiError as e:
            if getattr(e, "status_code", None) in (401, 403):
                self.status = "INVALID"
            elif getattr(e, "status_code", None) == 402:
                self.status = "EXHAUSTED"
            else:
                self.status = "ERROR"
            return {
                "healthy": False,
                "key_name": self.key_name,
                "status": self.status,
                "error": str(e),
                "status_code": getattr(e, "status_code", None),
            }
        except Exception as e:
            self.status = "ERROR"
            return {
                "healthy": False,
                "key_name": self.key_name,
                "status": self.status,
                "error": str(e),
            }


class ApifyManager:
    """
    Central Manager for Apify credentials, pool auto-discovery, balance checking,
    and zero-restart in-flight failover.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.mode: str = os.getenv("APIFY_MODE", "test").strip().lower()
        self.test_keys: List[KeyInfo] = []
        self.premium_key: Optional[KeyInfo] = None
        self.current_test_index: int = 0
        self.discover_keys()

    def discover_keys(self):
        """
        Scans environment variables:
        - APIFY_PREMIUM_KEY (Live Mode)
        - APIFY_KEY_1, APIFY_KEY_2, ..., APIFY_KEY_N (Numbered Test Pool)
        - Fallback: APIFY_KEY, APIFY_TOKEN
        """
        with self._lock:
            # 1. Discover Premium Key
            premium_token = (
                os.getenv("APIFY_PREMIUM_KEY")
                or os.getenv("APIFY_LIVE_KEY")
                or ""
            ).strip()
            if premium_token:
                self.premium_key = KeyInfo("APIFY_PREMIUM_KEY", premium_token)
            else:
                self.premium_key = None

            # 2. Discover Numbered Test Keys
            numbered_keys: List[tuple[int, str, str]] = []
            for env_name, env_val in os.environ.items():
                if not env_val or not env_val.strip():
                    continue
                match = re.match(r"^APIFY_KEY_(\d+)$", env_name.strip(), re.IGNORECASE)
                if match:
                    idx = int(match.group(1))
                    numbered_keys.append((idx, env_name, env_val.strip()))

            numbered_keys.sort(key=lambda x: x[0])

            self.test_keys = [
                KeyInfo(name, val) for _, name, val in numbered_keys
            ]

            # Fallback if no numbered keys found
            if not self.test_keys:
                single_fallback = (
                    os.getenv("APIFY_KEY_1")
                    or os.getenv("APIFY_KEY")
                    or os.getenv("APIFY_TOKEN")
                    or ""
                ).strip()
                if single_fallback:
                    self.test_keys = [KeyInfo("APIFY_KEY_1", single_fallback)]

            self.current_test_index = 0
            logger.info(
                f"[ApifyManager] Discovered {len(self.test_keys)} test key(s), "
                f"Premium key present: {bool(self.premium_key)}, Mode: {self.mode}"
            )

    def set_mode(self, mode: str):
        """Sets operating mode: 'test' or 'live'."""
        with self._lock:
            cleaned = mode.strip().lower()
            if cleaned not in ("test", "live"):
                cleaned = "test"
            self.mode = cleaned
            logger.info(f"[ApifyManager] Operating mode switched to: '{self.mode}'")

    def get_mode(self) -> str:
        return self.mode

    def get_active_key_info(self) -> KeyInfo:
        """Returns the KeyInfo object for the currently active key."""
        with self._lock:
            if self.mode == "live":
                if not self.premium_key or not self.premium_key.token:
                    raise ValueError(
                        "Live Apify Mode requested, but APIFY_PREMIUM_KEY is not configured in .env!"
                    )
                return self.premium_key

            if not self.test_keys:
                raise ValueError(
                    "No test Apify keys found! Please configure APIFY_KEY_1, APIFY_KEY_2, etc., in .env"
                )

            # Return the current key from the pool
            if self.current_test_index >= len(self.test_keys):
                self.current_test_index = 0
            return self.test_keys[self.current_test_index]

    def get_active_token(self) -> str:
        """Returns raw token string of the currently active key."""
        return self.get_active_key_info().token

    def get_client(self) -> ApifyClient:
        """Returns an ApifyClient instance initialized with the active token."""
        return self.get_active_key_info().get_client()

    def rotate_to_next_key(
        self,
        reason: str = "",
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> KeyInfo:
        """
        Switches to the next healthy key in the pool.
        In live mode, rotation is not supported as there is only one premium key.
        """
        with self._lock:
            if self.mode == "live":
                msg = f"⚠️ [ApifyManager] Live Mode Key error ({reason}). Cannot failover (single premium key)."
                if status_cb:
                    status_cb(msg)
                logger.warning(msg)
                return self.premium_key

            prev_key = self.test_keys[self.current_test_index]
            start_index = self.current_test_index
            total = len(self.test_keys)

            # Move forward looking for a non-exhausted key
            for step in range(1, total + 1):
                candidate_index = (start_index + step) % total
                candidate = self.test_keys[candidate_index]
                if candidate.status != "EXHAUSTED" and candidate.status != "INVALID":
                    self.current_test_index = candidate_index
                    msg = (
                        f"⚠️ Account {prev_key.key_name} {reason}! "
                        f"Auto-switching to {candidate.key_name}..."
                    )
                    logger.warning(f"[ApifyManager] {msg}")
                    if status_cb:
                        status_cb(msg)
                    return candidate

            # If all are exhausted or invalid, just advance index and alert
            self.current_test_index = (start_index + 1) % total
            next_key = self.test_keys[self.current_test_index]
            msg = (
                f"🚨 All Apify test accounts in the pool appear exhausted! "
                f"Attempting failover to {next_key.key_name}..."
            )
            logger.error(f"[ApifyManager] {msg}")
            if status_cb:
                status_cb(msg)
            return next_key

    def mark_current_exhausted(
        self,
        reason: str = "quota limit reached",
        status_cb: Optional[Callable[[str], None]] = None,
    ):
        """Marks current key as EXHAUSTED and immediately rotates to the next."""
        current = self.get_active_key_info()
        current.status = "EXHAUSTED"
        logger.warning(f"[ApifyManager] Flagged {current.key_name} as EXHAUSTED: {reason}")
        return self.rotate_to_next_key(reason=reason, status_cb=status_cb)

    def preflight_check(
        self,
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Synchronously checks balances and headroom for keys based on current mode.
        Returns a structured report and sets keys' statuses.
        """
        if status_cb:
            status_cb("🔍 Running Apify pre-flight balance and quota inspection...")

        if self.mode == "live":
            if not self.premium_key:
                return {
                    "success": False,
                    "mode": "live",
                    "error": "APIFY_PREMIUM_KEY is missing from environment variables.",
                    "healthy_count": 0,
                    "details": [],
                }
            res = self.premium_key.check_balance()
            healthy = res.get("healthy", False)
            return {
                "success": healthy,
                "mode": "live",
                "healthy_count": 1 if healthy else 0,
                "total_keys": 1,
                "details": [res],
            }

        # Test Mode: check all keys in the pool
        if not self.test_keys:
            self.discover_keys()

        if not self.test_keys:
            return {
                "success": False,
                "mode": "test",
                "error": "No APIFY_KEY_1...N keys configured in environment variables.",
                "healthy_count": 0,
                "details": [],
            }

        details = []
        healthy_keys = []
        for key_info in self.test_keys:
            res = key_info.check_balance()
            details.append(res)
            if res.get("healthy", False):
                healthy_keys.append(key_info)

        # Place the first healthy key at current_test_index
        if healthy_keys:
            first_healthy = healthy_keys[0]
            with self._lock:
                self.current_test_index = self.test_keys.index(first_healthy)

        healthy_count = len(healthy_keys)
        success = healthy_count > 0

        logger.info(
            f"[ApifyManager] Pre-flight check complete: {healthy_count}/{len(self.test_keys)} "
            f"healthy keys. Mode={self.mode}"
        )

        return {
            "success": success,
            "mode": "test",
            "healthy_count": healthy_count,
            "total_keys": len(self.test_keys),
            "details": details,
        }

    def call_actor_raw(
        self,
        actor_id: str,
        run_input: dict,
        timeout_secs: Optional[int] = None,
        memory_mbytes: Optional[int] = None,
        status_cb: Optional[Callable[[str], None]] = None,
        max_attempts: Optional[int] = None,
    ) -> tuple[dict, list[dict]]:
        """
        Executes an Apify actor call with automatic mid-run failover on 402/429/quota limits.
        Returns (run_dict, dataset_items_list).
        """
        if self.mode == "live":
            total_keys = 1
        else:
            total_keys = max(1, len(self.test_keys))

        attempts_allowed = max_attempts or (total_keys + 1)
        attempt = 0

        while attempt < attempts_allowed:
            attempt += 1
            active_key = self.get_active_key_info()
            client = active_key.get_client()

            call_kwargs: Dict[str, Any] = {"run_input": run_input}
            if timeout_secs:
                call_kwargs["timeout_secs"] = timeout_secs
            if memory_mbytes:
                call_kwargs["memory_mbytes"] = memory_mbytes

            try:
                run = client.actor(actor_id).call(**call_kwargs)
                dataset_id = (
                    run.get("defaultDatasetId")
                    if isinstance(run, dict)
                    else getattr(run, "defaultDatasetId", None)
                )

                items = []
                if dataset_id:
                    items = list(client.dataset(dataset_id).iterate_items())

                return run, items

            except ApifyApiError as e:
                status_code = getattr(e, "status_code", None)
                err_msg = str(e).lower()
                is_quota_error = (
                    status_code in (402, 429)
                    or "monthly usage" in err_msg
                    or "limit reached" in err_msg
                    or "rate limit" in err_msg
                )

                if is_quota_error and self.mode == "test" and len(self.test_keys) > 1:
                    reason = f"exhausted quota (HTTP {status_code})"
                    self.mark_current_exhausted(reason=reason, status_cb=status_cb)
                    # Retry in-flight immediately with next key
                    continue
                else:
                    # In live mode or non-quota error, raise
                    logger.error(f"[ApifyManager] Actor {actor_id} failed on {active_key.key_name}: {e}")
                    raise

            except Exception as e:
                err_str = str(e).lower()
                if ("402" in err_str or "quota" in err_str or "payment" in err_str) and self.mode == "test" and len(self.test_keys) > 1:
                    self.mark_current_exhausted(reason="quota/payment error", status_cb=status_cb)
                    continue
                raise

        raise RuntimeError(
            f"Pipeline Aborted: All available Apify keys ({len(self.test_keys)}) "
            f"failed or were exhausted while calling actor {actor_id}."
        )

    def call_actor(
        self,
        actor_id: str,
        run_input: dict,
        timeout_secs: Optional[int] = None,
        memory_mbytes: Optional[int] = None,
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> list[dict]:
        """
        High-level wrapper that executes an actor and returns dataset items directly.
        """
        _, items = self.call_actor_raw(
            actor_id=actor_id,
            run_input=run_input,
            timeout_secs=timeout_secs,
            memory_mbytes=memory_mbytes,
            status_cb=status_cb,
        )
        return items


# Singleton instance shared across all backend modules
apify_manager = ApifyManager()

