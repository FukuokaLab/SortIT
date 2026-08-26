from sortIT.models import UserPreferences


def dark_mode(request):
    """Expose the user's dark mode preference to every template."""
    dark = False
    if request.user.is_authenticated:
        prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
        dark = prefs.dark_mode
    return {"dark_mode": dark}