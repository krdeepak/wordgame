from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from channels.auth import AuthMiddlewareStack

application = ProtocolTypeRouter({
    # Empty for now (http->django views is added by default)

    "websocket": AuthMiddlewareStack(
        URLRouter([
            # URLRouter just takes standard Django path() or url() entries.
        ])
    ),

})
