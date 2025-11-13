# Multiple Choice Mode
import random
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from sortIT.models import Annotation, Image, ImageSet, Label


@staff_member_required
def label_multi(request, imageset_id):
    # get specified image set
    imageset = get_object_or_404(ImageSet, id=imageset_id)

    images = imageset.images.all()
    labels = imageset.labels.all()

    # Check the number of labels linked to the ImageSet
    if labels.count() == 1 or (
        labels.count() == 2 and labels.filter(name="other").exists()
    ):
        # And Redirect to sortOne View if there is ONLY ONE label other than "other" label
        return redirect("sortIT:sortone", imageset_id=imageset_id)

    # Choose un-labeled images randomly
    unlabeled_images = images.exclude(annotations__user=request.user)
    if unlabeled_images:
        image = random.choice(unlabeled_images)
    else:
        return redirect("sortIT:finish")

    # Calculate progress
    total_images = images.count()
    labeled_images = total_images - unlabeled_images.count()
    progress = round(labeled_images / total_images * 100)

    # Show labeling form
    context = {
        "image": image,
        "labels": labels,
        "imageset": imageset,
        "progress": progress,
        "n_total": total_images,
        "n_labeled": labeled_images,
    }
    return render(request, "sortIT/labeling.html", context)


@staff_member_required
def label_multi_post(request):
    # Get the image and label selected by the user
    image_id = request.POST.get("image")
    label_id = request.POST.get("label")
    if image_id and label_id:
        image = Image.objects.get(id=image_id)  # pyright: ignore[reportAttributeAccessIssue]
        label = Label.objects.get(id=label_id)  # pyright: ignore[reportAttributeAccessIssue]

        # Create an Annotation object
        annotation = Annotation(image=image, label=label, user=request.user)
        annotation.save()

        # Redirect to the same ImageSet
        return redirect("sortIT:labeling", image.imageset.id)
    else:
        # if the image or label is not specified
        return HttpResponse(b"Please select an image and a label.")
