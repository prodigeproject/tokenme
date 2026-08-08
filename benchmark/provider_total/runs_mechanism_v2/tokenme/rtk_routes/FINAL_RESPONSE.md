Implemented `top_routes` in `work.py` using `Counter`. It extracts non-empty `route=` fields and returns `(route, count)` pairs sorted by descending count, then route name.

Focused verification passed for fixture counts, tie ordering, malformed empty routes, and empty input.
