from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldError
from django.shortcuts import redirect, render

from sortIT.models import ImageSet


@login_required
def choose_img_set(request, project_id):
    imagesets = ImageSet.objects.filter(project=project_id)

    if imagesets:
        label_dict = {}

        for imset in imagesets:
            label_dict.setdefault(imset.labels, set()).add(imset)

        context = {"object_list": imagesets, "label_dict": label_dict}
        return render(request, "sortIT/imageset_list.html", context)

    else:
        return redirect("/admin/sortIT/imageset/add/")
