from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldError
from django.shortcuts import render, redirect

from sortIT.models import ImageSet


@login_required
def choose_img_set(request, project_id):
    try:
        imagesets = ImageSet.objects.filter(project=project_id)  # pyright: ignore[reportAttributeAccessIssue]

        print(imagesets)
        label_dict = {}

        for imset in imagesets:
            label_dict.setdefault(imset.labels, set()).add(imset)

        context = {"object_list": imagesets, "label_dict": label_dict}
        return render(request, "sortIT/imageset_list.html", context)

    except FieldError as e:
        print(f"Error fetching ImageSets: {e}")
        return redirect("/admin/sortIT/imageset/add/")
