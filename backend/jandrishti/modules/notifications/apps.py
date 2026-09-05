from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = "jandrishti.modules.notifications"
    label = "notifications"

    def ready(self) -> None:
        # Importing the handlers module is what registers the subscriptions on
        # the event bus. Doing it in `ready` keeps subscription wiring out of
        # every other module.
        from .application import handlers  # noqa: F401
