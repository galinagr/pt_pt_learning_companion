"""In-memory cache for identical /api/generate requests.

The key is a hash of the task, prompt, and inputs. The stored value is the
response. User text is not logged. The cache lives in the process and is
dropped on restart.
"""

from collections import OrderedDict
from hashlib import sha256
import json
from threading import Lock

from pt_pt_learning_companion.schemas import GenerateRequest, GenerateResponse


class ResponseCache:
    def __init__(self, capacity: int = 256) -> None:
        self._capacity = capacity
        self._items: OrderedDict[str, GenerateResponse] = OrderedDict()
        self._lock = Lock()

    def key(self, body: GenerateRequest, system: str) -> str:
        payload = json.dumps(
            {
                "task": body.task,
                "text": body.text.strip(),
                "quality": body.quality,
                "budget_mode": body.budget_mode,
                "require_managed": body.require_managed,
                "system": system,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return sha256(payload.encode("utf-8")).hexdigest()

    def get(self, key: str) -> GenerateResponse | None:
        with self._lock:
            found = self._items.get(key)
            if found is None:
                return None
            self._items.move_to_end(key)
            return found.model_copy(update={"cached": True})

    def put(self, key: str, response: GenerateResponse) -> None:
        stored = response.model_copy(update={"cached": False})
        with self._lock:
            self._items[key] = stored
            self._items.move_to_end(key)
            while len(self._items) > self._capacity:
                self._items.popitem(last=False)
