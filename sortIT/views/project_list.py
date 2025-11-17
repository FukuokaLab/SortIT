import datetime
from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldError
from django.http import HttpResponseBadRequest, StreamingHttpResponse
from django.shortcuts import redirect, render

from sortIT.admin import generate_csv_stream
from sortIT.models import Project


@login_required
def choose_proj(request):
    projs = Project.objects.all()
    if projs:
        context = {"object_list": projs}
        return render(request, "sortIT/project_list.html", context)

    else:
        return redirect("/admin/sortIT/project/add/")


@login_required
def download_csv(request, project_id):
    if request.method == "GET":
        current_datetime = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        project = Project.objects.get(id=project_id)
        csv_generator = generate_csv_stream(project=project)
        response = StreamingHttpResponse(csv_generator, content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{project.name}_{current_datetime}.csv"'
        )
    else:
        response = HttpResponseBadRequest()
    return response
