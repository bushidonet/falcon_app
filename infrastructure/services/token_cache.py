import time
import threading
import multiprocessing
import logging



logger = logging.getLogger(__name__)

class TokenCache:
    """
    Cache compartido de tokens Falcon, compatible con macOS/Windows (spawn mode).
    El Manager se crea bajo demanda (lazy init) para evitar RuntimeError.
    """

    _manager = None
    _shared_dict = None
    _init_lock = threading.Lock()

    def __init__(self):
        self._lock = threading.RLock()

        # Lazy init: solo creamos el Manager la primera vez que se instancia
        with TokenCache._init_lock:
            if TokenCache._manager is None:
                logger.info("🌀 Inicializando Manager multiproceso de TokenCache...")
                TokenCache._manager = multiprocessing.Manager()
                TokenCache._shared_dict = TokenCache._manager.dict()

        self._cache = TokenCache._shared_dict

    def get(self, tenant_id: str):
        with self._lock:
            entry = self._cache.get(tenant_id)
            if entry and entry["expires_at"] > time.time():
                return entry["token"]
            if entry:
                self.invalidate(tenant_id)
            return None

    def set(self, tenant_id: str, token: str, expires_at: float):
        with self._lock:
            self._cache[tenant_id] = {"token": token, "expires_at": expires_at}
            ttl = int(expires_at - time.time())
            logger.info(f"[{tenant_id}] 💾 Token almacenado (expira en {ttl}s)")

    def invalidate(self, tenant_id: str):
        with self._lock:
            self._cache.pop(tenant_id, None)
            logger.info(f"[{tenant_id}] ❌ Token eliminado del cache.")


# Lazy singleton global
_token_cache_instance = None

def get_token_cache() -> TokenCache:
    global _token_cache_instance
    if _token_cache_instance is None:
        _token_cache_instance = TokenCache()
    return _token_cache_instance
