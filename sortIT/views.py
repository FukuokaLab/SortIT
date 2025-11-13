import datetime
import os
import random
import zipfile
from io import BytesIO
from pathlib import Path
import logging

import PIL
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import FieldError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.datastructures import MultiValueDictKeyError
from django.views import generic

from .admin import generate_csv_stream
from .forms import ImageForm
from .models import Annotation, Image, ImageSet, Label, Project, User


# Single label (filtering)
@staff_member_required
def sortone(request, imageset_id):
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
        return redirect("sortIT:labeling", imageset_id=imageset_id)

    # count total number of images
    total_images = images.count()

    # Get the label linked to the ImageSet that is not "other"
    label = labels.exclude(name="other").first()

    # Choose un-sorted images
    unsorted_images = images.exclude(annotation__user=request.user)
    if unsorted_images:
        # number of images to show
        n_images = 36
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
        "n_total": total_images,
        "n_labeled": n_labeled,
    }
    return render(request, "sortIT/sortone.html", context)


@staff_member_required
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
            if image_id in selected_images:
                Annotation.objects.create(image=image, label=None, user=request.user)
            else:
                Annotation.objects.create(image=image, label=label, user=request.user)

        # Redirect to the next page
        return redirect("sortIT:sortone", imageset_id=imageset_id)


def finish(request):
    return render(request, "sortIT/thankyou.html")


@login_required
def show_image(request, image_id):
    image = Image.objects.get(id=image_id)
    response = FileResponse(open(image.filepath, "rb"))
    return response


def make_montage(request, project_id):
    project = Project.objects.get(id=project_id)
    imagesets = project.imagesets.all()
    images = list().extend([images.images.all() for images in imagesets])
    print(images)


def write_file(img_dst, jpeg_img):
    with open(img_dst, "wb+") as dst:
        for chunk in jpeg_img.chunks():
            dst.write(chunk)


def process_image(img, imageset_id):
    with BytesIO() as img_io:
        img_io.write(img.read())
        img_io.seek(0)

        with PIL.Image.open(img_io) as pil_img:
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")

            width, height = pil_img.size
            max_size = (700, 700)
            if width > max_size[0] or height > max_size[1]:
                pil_img.thumbnail(max_size)

            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

            with BytesIO() as output_io:
                try:
                    # if the image size is > 20KB save image with quality 75 to save the storage
                    if img_io.tell() < 20 * 1024:
                        quality = 100
                    else:
                        quality = 75

                    pil_img.save(output_io, format="JPEG", quality=quality)
                    output_io.seek(0)

                    jpeg_img = InMemoryUploadedFile(
                        output_io,
                        "ImageField",
                        img.name,
                        "image/jpeg",
                        output_io.tell(),
                        None,
                    )
                    imgname = Path(img._get_name())
                    ext = imgname.name.split(".")[-1]

                    now = datetime.datetime.now()
                    time = now.strftime("%Y%m%d-%H%M%S")

                    fname = f"{imgname.stem}___{imageset_id}___{time}.{ext}.jpg"

                    img_dst = Path(settings.MEDIA_ROOT).joinpath(fname)

                    write_file(img_dst, jpeg_img)

                finally:
                    output_io.close()

    # Synchronize database operations
    image = Image.objects.create(filepath=img_dst)
    image.imageset.set([imageset_id])
    image.save()


@staff_member_required
def image_upload(request, imageset_id):
    # Synchronous processing
    imageset = ImageSet.objects.get(id=imageset_id)
    form = ImageForm()
    if request.method == "POST":
        form = ImageForm(request.POST, request.FILES)
        if form.is_valid():
            images = request.FILES.getlist("image")
            for img in images:
                process_image(img, imageset_id)
            return redirect(
                "sortIT:choose_img_set",
                project_id=Project.objects.get(imageset=imageset).id,
            )
    else:
        context = {
            "imageset": imageset,
            "form": form,
        }
        return TemplateResponse(request, "sortIT/image_upload.html", context)


@staff_member_required
def download(request):
    if request.method == "POST":
        user_id = request.POST["user"]

        try:
            imageset_id = request.POST["imageset"]
            imageset = ImageSet.objects.get(id=imageset_id)

        except MultiValueDictKeyError:
            users = User.objects.all()
            imagesets = ImageSet.objects.all()

            context = {
                "users": users,
                "imagesets": imagesets,
                "message": "Please select an Image Set.",
            }
            return render(request, "sortIT/download.html", context)

        delete = request.POST.get("delete", False)

        if request.POST.get("action") == "download_images":
            user = User.objects.get(id=user_id)

            print(
                f"SELCTED IMAGESET: {imageset.name} ========================================"
            )
            images = imageset.images.all()
            labels = imageset.label_set.all()

            labeled_images = images.filter(annotations__user=user)

            zip_name = f"{imageset.name}_{user.username}.zip"
            zip_path = Path(settings.MEDIA_ROOT).joinpath(zip_name)

            # generate ZIP
            with zipfile.ZipFile(zip_path, "w") as zip_file:
                # For each label, get images linked to the label and add them to the corresponding folder in the ZIP file
                for label in labels:
                    # get images linked to the label
                    images_by_label = labeled_images.filter(annotations__label=label)

                    # Add images to the folder
                    for image in images_by_label:
                        image_filepath = Path(image.filepath)

                        ext = image_filepath.stem.split(".")[-1]
                        stem_image = image_filepath.stem.split("___")[0]
                        newname = f"{stem_image}.{ext}"

                        zip_file.write(
                            image.filepath,
                            Path(f"{imageset.name}_{user.username}")
                            .joinpath(label.name)
                            .joinpath(newname),
                        )

                        # If the checkbox is checked, delete the image from the database and server
                        if delete:
                            image.delete()

                            try:
                                os.remove(image_filepath)
                            except FileNotFoundError:
                                print(f"File Not found: {image_filepath}")

            # Return the ZIP file as a response
            response = FileResponse(open(zip_path, "rb"))
            response["Content-Type"] = "application/zip"
            response["Content-Disposition"] = f'attachment; filename="{zip_name}"'

            os.remove(zip_path)

            return response

        elif request.POST.get("action") == "download_csv":
            csv_generator = generate_csv_stream(separator=";", imageset=imageset)
            response = StreamingHttpResponse(csv_generator, content_type="text/csv")
            current_datetime = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            response["Content-Disposition"] = (
                f'attachment; filename="imageset_{imageset}_{current_datetime}.csv"'
            )
            return response

    else:
        users = User.objects.all()
        imagesets = ImageSet.objects.all()

        context = {
            "users": users,
            "imagesets": imagesets,
        }
        return render(request, "sortIT/download.html", context)
