Implemented `top_routes` in `work.py`. It counts non-empty `route=` fields and returns `(route, count)` pairs sorted by descending count, then route name.

Focused fixture, tie-order, malformed-field, and empty-input verification passed.