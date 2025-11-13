from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldError
from django.shortcuts import render

from sortIT.models import Project


@login_required
def choose_proj(request):
    try:
        projs = Project.objects.all()  # pyright: ignore[reportAttributeAccessIssue]
        context = {"object_list": projs}
        return render(request, "sortIT/project_list.html", context)

    except FieldError:
        return
