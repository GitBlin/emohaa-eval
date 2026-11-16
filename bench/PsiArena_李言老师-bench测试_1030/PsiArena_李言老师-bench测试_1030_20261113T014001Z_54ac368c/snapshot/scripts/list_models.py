#!/usr/bin/env python
"""List configured model endpoints; GET /models only, no generation calls."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from psiarena.config import get_settings, _client_for


def main():
    s = get_settings()
    seen = set()
    for role in ('client', 'judge'):
        rc = s.roles[role]
        endpoint = (rc.base_url, rc.api_key)
        if endpoint in seen:
            continue
        seen.add(endpoint)
        print(f'Endpoint: {rc.base_url}')
        try:
            models = _client_for(rc.base_url, rc.api_key, s.timeout).models.list()
            for model in models:
                print(model.id)
        except Exception as exc:
            # Some gateway errors echo headers; keep errors free of credentials.
            raise SystemExit(f'Model list failed: {type(exc).__name__}') from None

if __name__ == '__main__':
    main()
