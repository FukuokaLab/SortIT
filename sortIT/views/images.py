import datetime
import os
import zipfile
from io import BytesIO
from pathlib import Path
import random

import PIL.Image
import matplotlib.pyplot as plt
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.template.response import TemplateResponse
from django.utils.datastructures import MultiValueDictKeyError

from sortIT.admin import generate_csv_stream
from sortIT.forms import ImageForm
from sortIT.models import Image, ImageSet, Project, User


@login_required
def show_image(request, image_id):
    image = Image.objects.get(id=image_id)
    response = FileResponse(open(image.filepath, "rb"))
    return response


def make_montage(project_id):
    project = Project.objects.get(id=project_id)
    imagesets = project.imagesets.all()
    images = []
    for i_s in imagesets:
        images.extend(list(i_s.images.all()))
    images = random.sample(images, k=20)
    images = [PIL.Image.open(image.filepath) for image in images]
    fig, axs = plt.subplots(
        nrows=4, ncols=5, sharex=True, sharey=True, figsize=(2, 1.6)
    )
    for i, ax in enumerate(axs.flat):
        ax.imshow(images[i])
        ax.axis("off")
    plt.savefig(f"media/montage_{project_id}.jpg", bbox_inches="tight", dpi=100)


def show_montage(request, project_id):
    if request.method == "GET":
        try:
            response = FileResponse(open(f"media/montage_{project_id}.jpg", "rb"))
        except FileNotFoundError:
            print(f"No montage for project {Project.objects.get(id=project_id)}")
            response = HttpResponse()
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
    image = Image.objects.create(filepath=img_dst, name=imgname)
    image.imageset.set([imageset_id])
    image.save()


@staff_member_required
def image_upload(request, imageset_id):
    imageset = ImageSet.objects.get(id=imageset_id)
    project_id = Project.objects.get(imagesets=imageset).id
    form = ImageForm()
    if request.method == "POST":
        form = ImageForm(request.POST, request.FILES)
        if form.is_valid():
            images = request.FILES.getlist("image")
            for img in images:
                process_image(img, imageset_id)

            make_montage(project_id)
            return redirect("sortIT:choose_img_set", project_id=project_id)
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
