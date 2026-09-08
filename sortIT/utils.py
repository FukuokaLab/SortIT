from collections.abc import Generator

from .models import Annotation, Image, ImageSet, Project


def annotation_map(
    project: Project,
    users: list,
    image_ids: list | None = None,
) -> dict:
    """Map (image_id, imageset_id) -> user_id -> label name.

    Annotations are unique per (user, image, image set), so each user has at
    most one value per pair (an empty string when the annotation has no label,
    i.e. the user discarded the image).
    """
    qs = Annotation.objects.filter(user__in=users).select_related("label")
    qs = qs.filter(imageset__project=project)
    if image_ids is not None:
        qs = qs.filter(image_id__in=image_ids)

    ann_map: dict = {}
    for ann in qs:
        ann_map.setdefault((ann.image_id, ann.imageset_id), {})[ann.user_id] = (
            ann.label.name if ann.label else ""
        )
    return ann_map


def _csv_field(value: str, sep: str) -> str:
    """Strip a CSV field; quote it if it contains the separator, whitespace,
    or a quote character (internal quotes are doubled)."""
    value = value.strip()
    if not value:
        return ""
    if sep in value or any(c.isspace() for c in value) or '"' in value:
        return '"' + value.replace('"', '""') + '"'
    return value


def _memberships(images) -> list[tuple[Image, ImageSet]]:
    """All (image, image set) memberships of the given images, sorted."""
    return sorted(
        ((image, imageset) for image in images for imageset in image.imageset.all()),
        key=lambda m: (m[0].id, m[1].id),
    )


def generate_csv_stream(obj: Project | ImageSet, sep: str = ",") -> Generator[str]:
    """Generate a CSV stream of image annotations.

    One row per image (per image set for a project export: an image that
    belongs to two image sets appears once per set, with the set named in
    the ``imageset`` column). Each cell holds that user's single label for
    the row's image set.

    The CSV format is:

        Image_ID,imageset,filename,<user1>,<user2>,<user3>...   # Project
        Image_ID,filename,<user1>,<user2>,<user3>...            # ImageSet

    Parameters
    ----------
    obj : Project | ImageSet
        Export all images of a project (one row per image set membership),
        or just the images of a single image set.
    sep : str, optional
        The separator character to use between fields (defaults to ',').
    """
    # Determine which images to include
    if isinstance(obj, Project):
        project = obj
        users = list(project.users.all())
        images = (
            Image.objects.filter(
                imageset__project=project,
                annotations__isnull=False,
            )
            .distinct()
            .prefetch_related("imageset")
        )
        include_set_col = True
        pairs = _memberships(images)  # one row per (image, image set)
    else:  # isinstance(obj, ImageSet):
        imageset = obj
        project = imageset.project
        users = list(imageset.project.users.all())
        images = (
            Image.objects.filter(
                imageset=imageset,
                annotations__imageset=imageset,
            )
            .distinct()
            .order_by("id")
        )
        include_set_col = False
        pairs = [(image, imageset) for image in images]

    header = ["Image_ID", "filename"]
    if include_set_col:
        header.insert(1, "imageset")
    header += [user.username for user in users]
    yield sep.join(_csv_field(f, sep) for f in header) + "\n"

    # Pre-fetch all annotations for this export in one query
    ann_map = annotation_map(project, users)

    for image, imageset in pairs:
        row = [str(image.id)]
        if include_set_col:
            row.append(imageset.name)
        row.append(image.name)  # original filename, pre-obfuscation
        cells = ann_map.get((image.id, imageset.id), {})
        row += [cells.get(user.id, "") for user in users]

        yield sep.join(_csv_field(f, sep) for f in row) + "\n"