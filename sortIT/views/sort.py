import random

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render

from sortIT.models import Annotation, Image, ImageSet, UserPreferences


@login_required
def sort(request: HttpRequest, imageset_id: int) -> HttpResponse:
    """Render the sorting page for a specific image set.

    This view selects a random subset of images that have not yet been
    annotated by the current user, updates user preferences based on
    POST data, and renders `sortIT/sort.html` with context information
    such as progress, image size and the selected images.

    Args:
        request: The HTTP request object. Must contain an authenticated
            user (enforced by `@login_required`).
        imageset_id: Primary key of the :class:`~sortIT.models.ImageSet`
            that the user wants to sort.

    Returns:
        HttpResponse: Rendered sorting page or a redirect to the labeling
        mode or finish view if conditions are not met.

    """
    # get specified image set
    imageset = ImageSet.objects.get(id=imageset_id)

    # Get images and labels linked to the ImageSet
    images = imageset.images.all()
    labels = imageset.labels.all()

    # Check the number of labels linked to the ImageSet
    if labels.count() != 1:
        # And Redirect to usual labeling mode View if there are > 1 labels
        return redirect("sortIT:label", imageset_id=imageset_id)

    # count total number of images
    total_images = images.count()

    # Get the label linked to the ImageSet (should only be one)
    label = labels.first()

    # Choose un-sorted images
    unsorted_images = images.exclude(annotations__user=request.user)
    if unsorted_images:
        # number of images to show
        prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
        n_images = prefs.nimgs
        imsize = prefs.imsize

        if request.method == "POST":
            n_images = int(request.POST.get("nimgs", prefs.nimgs))
            imsize = int(request.POST.get("imsize", prefs.imsize))

            prefs.nimgs = n_images
            prefs.imsize = imsize
            prefs.save()

        # Randomly select n_images
        images = random.sample(
            list(unsorted_images),
            min(n_images, unsorted_images.count()),
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
    """Handle the form submission from the sorting page.

    Creates :class:`~sortIT.models.Annotation` objects for the images
    shown on the page depending on whether the user selected them to
    keep or remove. Selected images are given `None` as the label
    (indicating the user chose to discard them), while unselected
    images receive the current label of the :class:`~sortIT.models.ImageSet`.

    The view then redirects back to the next page of images to be sorted.

    Args:
        request: The HTTP request object containing POST data.

    Returns:
        HttpResponse: Redirects to the next sorting page or
        `HttpResponseBadRequest` for non-POST requests.

    """
    if request.method == "POST":
        imageset_id = request.POST["imageset"]
        selected_images = request.POST["selected_images"].split(",")

        imageset = ImageSet.objects.get(id=imageset_id)
        label = imageset.labels.first()

        # Get all image id displayed
        displayed_images = request.POST["displayed_images"].split(",")

        for image_id in displayed_images:
            image = Image.objects.get(id=image_id)
            Annotation.objects.get_or_create(
                image=image,
                user=request.user,
                label=None if image_id in selected_images else label,
                defaults={"imageset": imageset},
            )

        # Redirect to the next page
        return redirect("sortIT:sort", imageset_id=imageset_id)
    return HttpResponseBadRequest()
