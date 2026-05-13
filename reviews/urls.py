from django.urls import path
from .views import (
    AssignReviewerView,
    ReviewQueueView,
    ReviewWorkspaceView,
    CommentView,
    CommentResolveView,
    ReviewDecisionView,
    SLAStatusView,
)

urlpatterns = [
    path(
        "applications/<uuid:application_id>/assign-reviewer/",
        AssignReviewerView.as_view(),
        name="assign-reviewer",
    ),
    path(
        "reviews/my-queue/",
        ReviewQueueView.as_view(),
        name="review-queue",
    ),
    path(
        "reviews/workspace/<uuid:application_id>/",
        ReviewWorkspaceView.as_view(),
        name="review-workspace",
    ),
    path(
        "applications/<uuid:application_id>/comments/",
        CommentView.as_view(),
        name="comments",
    ),
    path(
        "applications/<uuid:application_id>/comments/<uuid:comment_id>/resolve/",
        CommentResolveView.as_view(),
        name="comment-resolve",
    ),
    path(
        "applications/<uuid:application_id>/review-decision/",
        ReviewDecisionView.as_view(),
        name="review-decision",
    ),
    path(
        "reviews/sla-status/",
        SLAStatusView.as_view(),
        name="sla-status",
    ),
]
