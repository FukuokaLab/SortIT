import datetime
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, StreamingHttpResponse
from django.shortcuts import redirect, render

from sortIT.admin import generate_csv_stream
from sortIT.models import ImageSet


@login_required
def choose_img_set(request, project_id):
    imagesets = ImageSet.objects.filter(project=project_id)

    if imagesets:
        context = {"object_list": imagesets}
        return render(request, "sortIT/imageset_list.html", context)

    else:
        return redirect("/admin/sortIT/imageset/add/")


@login_required
def download_csv(request, imageset_id):
    if request.method == "GET":
        current_datetime = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        imageset = ImageSet.objects.get(id=imageset_id)
        csv_generator = generate_csv_stream(image_set=imageset)
        response = StreamingHttpResponse(csv_generator, content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{imageset.name}_{imageset.project.name}_{current_datetime}.csv"'
        )
    else:
        response = HttpResponseBadRequest()
    return response
