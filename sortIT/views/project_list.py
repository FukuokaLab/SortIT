from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldError
from django.shortcuts import redirect, render

from sortIT.models import Project


@login_required
def choose_proj(request):
    projs = Project.objects.all()
    if projs:
        context = {"object_list": projs}
        return render(request, "sortIT/project_list.html", context)

    else:
        return redirect("/admin/sortIT/project/add/")
