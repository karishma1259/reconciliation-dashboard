from django.http import JsonResponse
from django.views import View

from reconciler.models import Location
from reconciler.services.comparator import reconcile_from_db

# Computed once per process. Fine at 120 rows / no auth / take-home scope --
# called out explicitly in DECISIONS.md as something a real deployment
# would need to change (cache invalidation on re-import, etc).
_CACHE = {"data": None}


def _get_discrepancies():
    if _CACHE["data"] is None:
        _CACHE["data"] = reconcile_from_db()
    return _CACHE["data"]


class OrgListView(View):
    """So the frontend's tenant selector doesn't have to hardcode org ids."""
    def get(self, request):
        orgs = sorted(set(Location.objects.values_list("org_id", flat=True)))
        return JsonResponse({"orgs": orgs})


class DiscrepancyListView(View):
    """
    Tenant boundary is enforced here, not trusted from the client beyond
    'which org do you want' -- there's no cross-org query path at all,
    since we filter in Python against org_id before anything is
    serialized. There is no query parameter that returns all orgs at once.
    """
    def get(self, request):
        org_id = request.GET.get("org_id")
        reason = request.GET.get("reason")
        sort = request.GET.get("sort")  # "value_asc" | "value_desc"

        if not org_id:
            return JsonResponse({"error": "org_id query parameter is required"}, status=400)

        rows = [d for d in _get_discrepancies() if d.org_id == org_id]

        if reason and reason != "ALL":
            rows = [d for d in rows if d.reason == reason]

        def sort_key(d):
            # Falls back to value_b when value_a is missing (e.g. orphans have no A value)
            raw = d.value_a if d.value_a not in (None, "") else d.value_b
            try:
                return float("".join(c for c in (raw or "0") if c.isdigit() or c in ".-"))
            except ValueError:
                return 0.0

        if sort == "value_asc":
            rows.sort(key=sort_key)
        elif sort == "value_desc":
            rows.sort(key=sort_key, reverse=True)

        return JsonResponse({"results": [d.as_dict() for d in rows]})
