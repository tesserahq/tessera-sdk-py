from starlette.requests import Request


def request_context(request: Request) -> dict:
    """Build a loggable context dict identifying the request and, when
    already known at this point in the pipeline, the user attempting it."""
    context = {"path": request.url.path, "method": request.method}

    user = getattr(request.state, "user", None)
    if user is not None:
        external_id = getattr(user, "external_id", None)
        if external_id is not None:
            context["user_external_id"] = external_id
        user_id = getattr(user, "id", None)
        if user_id is not None:
            context["user_id"] = str(user_id)

    return context
