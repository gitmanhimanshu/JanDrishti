from django.urls import path

from .views import CampaignDetailView, CampaignListView, ContributeView

app_name = "funding"

urlpatterns = [
    path("campaigns/", CampaignListView.as_view(), name="campaigns"),
    path("campaigns/<uuid:campaign_id>/", CampaignDetailView.as_view(), name="campaign-detail"),
    path("campaigns/<uuid:campaign_id>/contribute/", ContributeView.as_view(), name="contribute"),
]
