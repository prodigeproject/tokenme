Implemented `top_routes` in `work.py`.

It now extracts non-empty `route=` values, counts them, and returns `(route, count)` pairs sorted by descending count and then route name. Focused fixture and malformed-input checks passed.
