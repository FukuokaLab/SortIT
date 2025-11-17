import datetime
import os
from io import BytesIO
from pathlib import Path
import random

import PIL.Image
import matplotlib.pyplot as plt
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import (
    FileResponse,
    HttpResponse,
    HttpResponseBadRequest,
)
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from sortIT.forms import ImageForm
from sortIT.models import Image, ImageSet, Project


@login_required
def show_image(request, image_id):
    if request.method == "GET":
        image = Image.objects.get(id=image_id)
        response = FileResponse(open(image.filepath, "rb"))
    else:
        response = HttpResponseBadRequest()

    return response


def make_montage(project):
    imagesets = project.imagesets.all()
    images = []
    for i_s in imagesets:
        images.extend(list(i_s.images.all()))
    k = min(len(images), 20)
    images = random.sample(images, k=k)
    images = [PIL.Image.open(image.filepath) for image in images]
    _, axs = plt.subplots(nrows=4, ncols=5, sharex=True, sharey=True, figsize=(2, 1.6))
    for i, ax in enumerate(axs.flat):
        ax.axis("off")
        if i < k:
            ax.imshow(images[i])

    plt.savefig(
        f"{settings.MEDIA_ROOT}/montage_{project.id}.jpg", bbox_inches="tight", dpi=100
    )


def show_montage(request, project_id):
    if request.method == "GET":
        try:
            response = FileResponse(
                open(f"{settings.MEDIA_ROOT}/montage_{project_id}.jpg", "rb")
            )
        except FileNotFoundError:
            print(f"No montage for project {Project.objects.get(id=project_id)}")
            response = HttpResponse()
    else:
        response = HttpResponseBadRequest()
    return response


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
            max_size = (256, 256)
            if width > max_size[0] or height > max_size[1]:
                pil_img.thumbnail(max_size)

            with BytesIO() as output_io:
                try:
                    # if the image size is > 15KB save image with quality 75 to save the storage
                    if img_io.tell() < 15 * 1024:
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
    image = Image.objects.create(filepath=img_dst, name=imgname)
    image.imageset.set([imageset_id])
    image.save()


@staff_member_required
def image_upload(request, imageset_id):
    imageset = ImageSet.objects.get(id=imageset_id)
    project = imageset.project
    form = ImageForm()
    Path(settings.MEDIA_ROOT).mkdir(exist_ok=True)
    if request.method == "POST":
        form = ImageForm(request.POST, request.FILES)
        if form.is_valid():
            images = request.FILES.getlist("image")
            images.extend(request.FILES.getlist("image-dir"))
            for img in images:
                # Check for an existing image with the same original filename in this project
                original_name = Path(img._get_name())
                existing = Image.objects.filter(
                    imageset__project=project, name=original_name
                ).first()
                if existing:
                    # Duplicate: just associate the new imageset with this image
                    existing.imageset.add(imageset)
                else:
                    # New image: process and store it
                    process_image(img, imageset_id)

            make_montage(project)
            return redirect("sortIT:choose_img_set", project_id=project.id)
        else:
            return HttpResponseBadRequest()
    else:
        context = {
            "imageset": imageset,
            "form": form,
        }
        return TemplateResponse(request, "sortIT/upload.html", context)
