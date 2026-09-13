from django.urls import path
from reconciler.views import DiscrepancyListView, OrgListView

urlpatterns = [
    path("discrepancies/", DiscrepancyListView.as_view(), name="discrepancies"),
    path("orgs/", OrgListView.as_view(), name="orgs"),
]
