import random

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from sortIT.models import Annotation, Image, ImageSet, Label


@login_required
def label(request, imageset_id):
    # get specified image set
    imageset = get_object_or_404(ImageSet, id=imageset_id)

    images = imageset.images.all()
    labels = imageset.labels.all()

    # Check the number of labels linked to the ImageSet
    if labels.count() == 1 or (
        labels.count() == 2 and labels.filter(name="other").exists()
    ):
        # And Redirect to sortOne View if there is ONLY ONE label other than "other" label
        return redirect("sortIT:sort", imageset_id=imageset_id)

    # Choose un-labeled images randomly
    unlabeled_images = images.exclude(annotations__user=request.user)
    if unlabeled_images:
        image = random.choice(unlabeled_images)
    else:
        return redirect("sortIT:finish")

    # Calculate progress
    total_images = images.count()
    labeled_images = total_images - unlabeled_images.count()
    progress = round(labeled_images / total_images * 100) if total_images > 0 else 0

    # Show labeling form
    context = {
        "image": image,
        "labels": labels,
        "imageset": imageset,
        "progress": progress,
        "n_total": total_images,
        "n_labeled": labeled_images,
    }
    return render(request, "sortIT/label.html", context)


@login_required
def label_post(request):
    # Get the image and label selected by the user
    image_id = request.POST.get("image")
    label_id = request.POST.get("label")
    imageset_id = request.POST.get("imageset")
    if image_id and label_id and imageset_id:
        image = get_object_or_404(Image, id=image_id)
        label = get_object_or_404(Label, id=label_id)
        imageset = get_object_or_404(ImageSet, id=imageset_id)

        Annotation.objects.get_or_create(
            image=image,
            label=label,
            user=request.user,
            defaults={"imageset": imageset},
        )

        return redirect("sortIT:label", imageset_id=imageset.id)
    else:
        return HttpResponse(b"Please select an image and a label.")
