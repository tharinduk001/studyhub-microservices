def current_user(request):
    """Return {'user_id': int, 'username': str} from the shared session, or None."""
    user_id = request.session.get("user_id")
    username = request.session.get("username")
    if user_id is None or username is None:
        return None
    return {"user_id": user_id, "username": username}
