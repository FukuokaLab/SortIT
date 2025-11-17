import random
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render

from sortIT.models import Annotation, Image, ImageSet, UserPreferences


@login_required
def sort(request, imageset_id):
    # get specified image set
    imageset = ImageSet.objects.get(id=imageset_id)

    # Get images and labels linked to the ImageSet
    images = imageset.images.all()
    labels = imageset.labels.all()

    # Check the number of labels linked to the ImageSet
    if not (
        labels.count() == 1
        or (labels.count() == 2 and labels.filter(name="other").exists())
    ):
        # And Redirect to usual labeling mode View if there are > 2 labels
        return redirect("sortIT:label", imageset_id=imageset_id)

    # count total number of images
    total_images = images.count()

    # Get the label linked to the ImageSet that is not "other"
    label = labels.exclude(name="other").first()

    # Choose un-sorted images
    unsorted_images = images.exclude(
        annotations__user=request.user, sortedsets=imageset_id
    )
    if unsorted_images:
        # number of images to show
        prefs = UserPreferences.objects.get(user=request.user)
        n_images = prefs.nimgs
        imsize = prefs.imsize

        if request.method == "POST":
            n_images = int(request.POST.get("nimgs", n_images))
            imsize = int(request.POST.get("imsize", imsize))

            prefs.nimgs = n_images
            prefs.imsize = imsize
            prefs.save()

        # Randomly select n_images
        images = random.sample(
            list(unsorted_images), min(n_images, unsorted_images.count())
        )
    else:
        # If all images are sorted, redirect to finish
        return redirect("sortIT:finish")

    # Calculate progress
    n_labeled = total_images - unsorted_images.count()
    progress = round(n_labeled / total_images * 100)

    # Show sorting form
    context = {
        "images": images,
        "label": label,
        "imageset": imageset,
        "progress": progress,
        "nimgs": n_images,
        "imsize": imsize,
        "n_total": total_images,
        "n_labeled": n_labeled,
    }
    return render(request, "sortIT/sort.html", context)


@login_required
def sort_post(request):
    if request.method == "POST":
        imageset_id = request.POST["imageset"]
        selected_images = request.POST["selected_images"].split(",")

        imageset = ImageSet.objects.get(id=imageset_id)
        labels = imageset.labels.all()

        # Get 'non-other' label which linked to the image-set
        label = labels.exclude(name="other").first()

        # Get all image id displayed
        displayed_images = request.POST["displayed_images"].split(",")

        # set selected images label to None
        for image_id in displayed_images:
            image = Image.objects.get(id=image_id)
            image.sortedsets.add(imageset)
            if (
                image_id not in selected_images
                and image.annotations.filter(user=request.user) is None
            ):
                Annotation.objects.update_or_create(
                    image=image, label=label, user=request.user
                )
            else:
                Annotation.objects.update_or_create(
                    image=image, label=None, user=request.user
                )

        # Redirect to the next page
        return redirect("sortIT:sort", imageset_id=imageset_id)
    else:
        return HttpResponseBadRequest()
