import datetime
import hashlib
import io
import logging
import math
import random
import re
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

import PIL.Image
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import (
    FileResponse,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from sortIT.forms import ImageForm
from sortIT.models import Annotation, Image, ImageSet, Label, Project, UserPreferences
from sortIT.utils import _csv_field, _memberships, annotation_map, generate_csv_stream

logger = logging.getLogger(__name__)


def make_montage(project):
    imagesets = project.imagesets.all()
    images = []
    for i_s in imagesets:
        images.extend(list(i_s.images.all()))
    if not images:
        return  # nothing to plot — don't crash on an empty project
    k = min(len(images), 20)
    images = random.sample(images, k=k)
    images = [PIL.Image.open(image.filepath) for image in images]

    thumb_size = (128, 128)
    cols = math.ceil(math.sqrt(len(images)))
    rows = (len(images) + cols - 1) // cols
    canvas_w = cols * thumb_size[0]
    canvas_h = rows * thumb_size[1]
    canvas = PIL.Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))

    for i, img in enumerate(images):
        img.thumbnail(thumb_size)
        x = (i % cols) * thumb_size[0] + (thumb_size[0] - img.width) // 2
        y = (i // cols) * thumb_size[1] + (thumb_size[1] - img.height) // 2
        canvas.paste(img, (x, y))

    canvas.save(
        f"{settings.MEDIA_ROOT}/montage_{project.id}.jpg",
        "JPEG",
        quality=85,
    )


@login_required
def show_image(request, image_id):
    if request.method == "GET":
        image = Image.objects.get(id=image_id)
        # serve the obfuscated file, but hand the browser the original name
        # (inline keeps <img> tags working; Save-as uses the real filename)
        return FileResponse(open(image.filepath, "rb"), filename=image.name)
    return HttpResponseBadRequest()


@login_required
def show_montage(request, project_id):
    if request.method == "GET":
        try:
            response = FileResponse(
                open(f"{settings.MEDIA_ROOT}/montage_{project_id}.jpg", "rb"),
            )
        except FileNotFoundError:
            logger.warning(
                "No montage for project %s", Project.objects.get(id=project_id)
            )
            response = HttpResponse()
    else:
        response = HttpResponseBadRequest()
    return response


def write_file(img_dst, jpeg_img):
    with open(img_dst, "wb+") as dst:
        dst.writelines(jpeg_img.chunks())


def process_image(img, imageset_id, digest):
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
                    quality = 100 if img_io.tell() < 15 * 1024 else 75

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

                    # store under an obfuscated name so the original filename
                    # is never exposed (CSV/downloads serve the original name)
                    fname = f"{uuid.uuid4().hex}.jpg"

                    img_dst = Path(settings.MEDIA_ROOT).joinpath(fname)

                    write_file(img_dst, jpeg_img)

                finally:
                    output_io.close()

    # Synchronize database operations
    image = Image.objects.create(filepath=img_dst, name=imgname, sha256=digest)
    image.imageset.set([imageset_id])
    image.save()


@staff_member_required
def image_upload(request, imageset_id):
    imageset = ImageSet.objects.get(id=imageset_id)
    Path(settings.MEDIA_ROOT).mkdir(exist_ok=True)
    if request.method == "POST":
        form = ImageForm(request.POST, request.FILES)
        if form.is_valid():
            project = imageset.project

            images = request.FILES.getlist("image")
            images.extend(request.FILES.getlist("image-dir"))

            for img in images:
                digest = hashlib.sha256(img.read()).hexdigest()
                img.seek(0)
                existing = Image.objects.filter(
                    imageset__project=project,
                    sha256=digest,
                ).first()
                if existing:
                    # Duplicate content: just associate the new imageset with this image
                    existing.imageset.add(imageset)
                else:
                    # New image: process and store it
                    process_image(img, imageset_id, digest)

            make_montage(project)
            return redirect("sortIT:choose_img_set", project_id=project.id)
    else:
        context = {
            "imageset": imageset,
            "form": ImageForm(),
        }
    return render(request, "sortIT/upload.html", context)


@login_required
def finish(request):
    return render(request, "sortIT/thankyou.html")


@login_required
def label(request, imageset_id):
    # get specified image set
    imageset = get_object_or_404(ImageSet, id=imageset_id)

    images = imageset.images.all()
    labels = imageset.labels.all()

    # Redirect to sortOne mode if there is exactly one non-"other" label
    if labels.exclude(name="other").count() == 1:
        return redirect("sortIT:sort", imageset_id=imageset_id)

    prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
    imsize = prefs.label_imsize

    # Settings POST: update prefs and keep showing the current image
    if request.method == "POST":
        imsize = int(request.POST.get("imsize", prefs.label_imsize))
        prefs.label_imsize = imsize
        prefs.save()
        image = get_object_or_404(Image, id=request.POST.get("image"))
    else:
        # Choose un-labeled images randomly, unless returning via the Back button
        image = None
        back_image_id = request.GET.get("image")
        if back_image_id:
            image = get_object_or_404(Image, id=back_image_id, imageset=imageset)
        else:
            unlabeled_images = images.exclude(
                annotations__user=request.user, annotations__imageset=imageset
            )
            if unlabeled_images:
                image = random.choice(unlabeled_images)
            else:
                return redirect("sortIT:finish")

    # Calculate progress
    unlabeled_count = images.exclude(
        annotations__user=request.user, annotations__imageset=imageset
    ).count()
    total_images = images.count()
    labeled_images = total_images - unlabeled_count
    progress = round(labeled_images / total_images * 100) if total_images > 0 else 0

    # Show labeling form
    context = {
        "image": image,
        "labels": labels,
        "imageset": imageset,
        "progress": progress,
        "n_total": total_images,
        "n_labeled": labeled_images,
        "imsize": imsize,
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
            imageset=imageset,
        )

        return redirect("sortIT:label", imageset_id=imageset.id)
    else:
        return HttpResponse(b"Please select an image and a label.")


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

    # Redirect to labeling mode unless there is exactly one non-"other" label
    if labels.exclude(name="other").count() != 1:
        return redirect("sortIT:label", imageset_id=imageset_id)

    # count total number of images
    total_images = images.count()

    # Get the label linked to the ImageSet (should only be one)
    label = labels.first()

    # Choose un-sorted images
    unsorted_count = images.exclude(
        annotations__user=request.user, annotations__imageset=imageset
    ).count()
    if unsorted_count:
        # number of images to show
        prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
        n_images = prefs.sort_nimgs
        imsize = prefs.sort_imsize

        if request.method == "POST":
            n_images = int(request.POST.get("nimgs", prefs.sort_nimgs))
            imsize = int(request.POST.get("imsize", prefs.sort_imsize))

            prefs.sort_nimgs = n_images
            prefs.sort_imsize = imsize
            prefs.save()

        # Pick the exact set when returning via the Back button
        back_ids = request.GET.get("images")
        if back_ids:
            id_list = [int(i) for i in back_ids.split(",") if i.isdigit()]
            images = list(images.filter(id__in=id_list))
        else:
            # Randomly select n_images at the DB level
            n_to_show = min(n_images, unsorted_count)
            images = list(
                images.exclude(
                    annotations__user=request.user, annotations__imageset=imageset
                ).order_by("?")[:n_to_show]
            )
    else:
        # If all images are sorted, redirect to finish
        return redirect("sortIT:finish")

    # Calculate progress
    n_labeled = total_images - unsorted_count
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

        # One shared timestamp marks this whole batch as a single undo unit
        batch_ts = timezone.now()

        for image_id in displayed_images:
            image = Image.objects.get(id=image_id)
            Annotation.objects.get_or_create(
                image=image,
                user=request.user,
                imageset=imageset,
                label=None if image_id in selected_images else label,
                defaults={"timestamp": batch_ts},
            )

        # Redirect to the next page
        return redirect("sortIT:sort", imageset_id=imageset_id)
    return HttpResponseBadRequest()


@login_required
def undo(request, imageset_id):
    """Delete the user's most recent annotation batch for this imageset and
    return to it so they can redo the labeling.

    A batch is the set of annotations sharing the most recent timestamp
    (a sort page creates one timestamp per entire page, a label page one
    per image), so Back chains back through the whole session.
    """
    mode = request.POST.get("mode", "label")
    newest = (
        Annotation.objects.filter(user=request.user, imageset_id=imageset_id)
        .order_by("-timestamp")
        .first()
    )
    if newest:
        batch = Annotation.objects.filter(
            user=request.user, imageset_id=imageset_id, timestamp=newest.timestamp
        )
        ids = [str(i) for i in batch.values_list("image_id", flat=True)]
        batch.delete()
        if mode == "sort":
            return redirect(
                f"{reverse('sortIT:sort', args=[imageset_id])}?images={','.join(ids)}"
            )
        return redirect(
            f"{reverse('sortIT:label', args=[imageset_id])}?image={ids[0]}"
        )
    return redirect("sortIT:label", imageset_id=imageset_id)


@login_required
def choose_proj(request):
    projs = Project.objects.all()
    if projs:
        context = {"object_list": projs}
        return render(request, "sortIT/project_list.html", context)

    else:
        return redirect("/admin/sortIT/project/add/")


@login_required
def download_project_csv(request, project_id):
    if request.method == "GET":
        current_datetime = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        project = Project.objects.get(id=project_id)
        csv_generator = generate_csv_stream(project)
        response = StreamingHttpResponse(csv_generator, content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{project.name}_{current_datetime}.csv"'
        )
    else:
        response = HttpResponseBadRequest()
    return response


@login_required
def choose_img_set(request, project_id):
    imagesets = ImageSet.objects.filter(project=project_id)

    if imagesets:
        context = {"object_list": imagesets}
        return render(request, "sortIT/imageset_list.html", context)

    return redirect("/admin/sortIT/imageset/add/")


@login_required
def download_imageset_csv(request, imageset_id):
    if request.method == "GET":
        current_datetime = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        imageset = ImageSet.objects.get(id=imageset_id)
        csv_generator = generate_csv_stream(imageset)
        response = StreamingHttpResponse(csv_generator, content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{imageset.name}_{imageset.project.name}_{current_datetime}.csv"'
        )
    else:
        response = HttpResponseBadRequest()
    return response


@login_required
def toggle_darkmode(request):
    """Flip the user's dark mode preference (POST only)."""
    if request.method == "POST":
        prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
        prefs.dark_mode = not prefs.dark_mode
        prefs.save()
    return redirect(request.POST.get("next") or "sortIT:choose_proj")


def _safe(name) -> str:
    """Sanitize a name for use as a zip entry / attachment filename."""
    return re.sub(r'[\\/:*?"<>|]', "_", str(name))


@staff_member_required
def download(request):
    """Searchable download page: filter a table of
    (project, image set, annotator) combos with data, tick rows, download."""
    if request.method == "POST":
        return _download_action(request)

    combos = (
        Annotation.objects.select_related("imageset__project", "user")
        .values(
            "imageset__project_id",
            "imageset__project__name",
            "imageset_id",
            "imageset__name",
            "user_id",
            "user__username",
        )
        .distinct()
        .order_by("imageset__project__name", "imageset__name", "user__username")
    )

    projects = {}
    imagesets = {}
    users = {}
    rows = []
    for c in combos:
        pid, sid, uid = c["imageset__project_id"], c["imageset_id"], c["user_id"]
        projects[pid] = c["imageset__project__name"]
        imagesets[sid] = c["imageset__name"]
        users[uid] = c["user__username"]
        rows.append(
            {
                "project_id": pid,
                "project_name": c["imageset__project__name"],
                "imageset_id": sid,
                "imageset_name": c["imageset__name"],
                "user_id": uid,
                "username": c["user__username"],
            }
        )

    return render(
        request,
        "sortIT/download.html",
        {
            "rows": rows,
            "projects": [
                {"id": k, "name": v}
                for k, v in sorted(projects.items(), key=lambda x: x[1])
            ],
            "imagesets": [
                {"id": k, "name": v}
                for k, v in sorted(imagesets.items(), key=lambda x: x[1])
            ],
            "users": [
                {"id": k, "name": v}
                for k, v in sorted(users.items(), key=lambda x: x[1])
            ],
        },
    )


def _parse_selection(raw_rows) -> dict:
    """Turn checked `project:imageset:user` values into
    {project_id: {imageset_id: {user_id}}} for combos that really have data."""
    selection = {}
    for raw in raw_rows:
        try:
            pid, sid, uid = (int(x) for x in raw.split(":"))
        except ValueError:
            continue
        if Annotation.objects.filter(
            imageset_id=sid, imageset__project_id=pid, user_id=uid
        ).exists():
            selection.setdefault(pid, {}).setdefault(sid, set()).add(uid)
    return selection


def _selection_csv(project, sets, users) -> str:
    """Combined CSV for one project: rows per (image, image set) membership,
    one column per selected annotator."""
    users = sorted(users, key=lambda u: u.username)
    ann_map = annotation_map(project, users)
    set_ids = {s.id for s in sets}
    images = (
        Image.objects.filter(
            imageset__project=project, imageset__in=sets, annotations__user__in=users
        )
        .distinct()
        .prefetch_related("imageset")
    )
    # only memberships that were actually annotated by a selected user
    pairs = [
        (image, imageset)
        for image, imageset in _memberships(images)
        if (image.id, imageset.id) in ann_map and imageset.id in set_ids
    ]

    sep = ","
    header = ["Image_ID", "imageset", "filename"] + [u.username for u in users]
    lines = [sep.join(_csv_field(f, sep) for f in header)]
    for image, imageset in pairs:
        cells = ann_map.get((image.id, imageset.id), {})
        row = [str(image.id), imageset.name, image.name]
        row += [cells.get(u.id, "") for u in users]
        lines.append(sep.join(_csv_field(f, sep) for f in row))
    return "\n".join(lines) + "\n"


def _download_csv_response(selection: dict) -> HttpResponse:
    """One CSV per project; a single project is returned as a plain CSV,
    multiple projects as a zip of `project.csv` files."""
    now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    objects = {}
    for pid, sets_users in selection.items():
        project = Project.objects.get(id=pid)
        sets = ImageSet.objects.filter(id__in=sets_users)
        users = User.objects.filter(id__in={u for us in sets_users.values() for u in us})
        objects[project] = (sets, users)

    if len(objects) == 1:
        project, (sets, users) = next(iter(objects.items()))
        text = _selection_csv(project, sets, users)
        response = HttpResponse(text, content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{_safe(project.name)}_{now}.csv"'
        )
        return response

    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w", zipfile.ZIP_DEFLATED) as zf:
        for project, (sets, users) in objects.items():
            zf.writestr(f"{_safe(project.name)}_{now}.csv", _selection_csv(project, sets, users))
    response = HttpResponse(zip_io.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="csvexport_{now}.zip"'
    return response


def _download_images_zip(selection: dict) -> HttpResponse:
    """Zip of image files for the selection, organized as
    `project / image set / original filename`."""
    now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w", zipfile.ZIP_DEFLATED) as zf:
        for pid, sets_users in selection.items():
            project_name = _safe(Project.objects.get(id=pid).name)
            user_ids = {u for us in sets_users.values() for u in us}
            for sid, uids in sets_users.items():
                set_name = _safe(ImageSet.objects.get(id=sid).name)
                images = (
                    Image.objects.filter(imageset=sid, annotations__user__in=uids)
                    .distinct()
                    .order_by("id")
                )
                for image in images:
                    src = Path(image.filepath)
                    if src.exists():
                        zf.writestr(
                            f"{project_name}/{set_name}/{_safe(image.name)}",
                            src.read_bytes(),
                        )
    response = HttpResponse(zip_io.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="images_{now}.zip"'
    return response


def _download_action(request) -> HttpResponse:
    action = request.POST.get("action")
    if action in ("download_all_images", "download_all_csvs"):
        return _download_all(action)

    selection = _parse_selection(request.POST.getlist("row"))
    if not selection:
        return HttpResponseBadRequest("Select at least one row.")

    if action == "download_images":
        return _download_images_zip(selection)
    if action == "download_csv":
        return _download_csv_response(selection)
    return HttpResponseBadRequest(f"Unknown action: {action}")


def _download_all(action) -> HttpResponse:
    """Whole-app archive: one CSV per project, or images in
    `project / image set / original filename` folders."""
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w", zipfile.ZIP_DEFLATED) as zf:
        for project in Project.objects.order_by("name"):
            safe = _safe(project.name)
            if action == "download_all_csvs":
                zf.writestr(f"{safe}.csv", "".join(generate_csv_stream(project)))
            else:  # download_all_images
                images = (
                    Image.objects.filter(imageset__project=project)
                    .distinct()
                    .prefetch_related("imageset")
                )
                for image, is_ in _memberships(images):
                    src = Path(image.filepath)
                    if src.exists():
                        arcname = f"{safe}/{_safe(is_.name)}/{_safe(image.name)}"
                        zf.writestr(arcname, src.read_bytes())
    response = HttpResponse(zip_io.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="sortit_all_{stamp}.zip"'
    return response
