from django.urls import path
from .views import JobStatsView, JobStatusView, JobSubmitView

urlpatterns = [
    path('jobs/', JobSubmitView.as_view(), name='job-submit'),
    path('jobs/<int:job_id>/', JobStatusView.as_view(), name='job-status'),
    path('stats/', JobStatsView.as_view(), name='job-stats'),

]