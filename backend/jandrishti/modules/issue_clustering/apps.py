from django.apps import AppConfig


class IssueClusteringConfig(AppConfig):
    name = "jandrishti.modules.issue_clustering"
    label = "issue_clustering"

    def ready(self) -> None:
        from . import handlers  # noqa: F401
