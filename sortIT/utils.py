from collections.abc import Generator

from .models import Annotation, Image, ImageSet, Project


def generate_csv_stream(obj: Project | ImageSet, sep: str = ",") -> Generator[str]:
    """Generate a CSV formatted stream of image annotations.

    This generator yields lines of a CSV file that contains each image name
    followed by the annotation labels for every user that has access to the
    project (or image set). The first yielded line is the header row
    containing the column names.

    The CSV format is:

        Image,<user1>,<user2>,<user3>...

    For each image the annotations are collected from the
    `Annotation` model. If a user has an annotation with a label (i.e. not `None`)
    for that image the label's name is written in the cell; otherwise the
    cell is left empty.

    Parameters
    ----------
    obj : Project | ImageSet
        The project or image set to export.  If a :class:`Project` is
        provided all images belonging to the project are exported.  If an
        :class:`ImageSet` is provided only the images in that set are
        exported.
    sep : str, optional
        The separator character to use between fields (defaults to ',').

    Yields
    ------
    str
        One line of the CSV file, terminated with a newline character.

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
            .order_by("id")
        )
    else:  # isinstance(obj, ImageSet):
        imageset = obj
        project = imageset.project
        users = list(imageset.project.users.all())
        images = (
            Image.objects.filter(
                imageset=imageset,
                annotations__isnull=False,
            )
            .distinct()
            .order_by("id")
        )

    header_row = ["Image"] + [user.username for user in users]
    yield sep.join(header_row) + "\n"

    for image in images:
        anns = Annotation.objects.filter(
            image=image,
            user__in=users,
            imageset__project=project,
        ).select_related("label", "user")

        ann_map = {}
        for ann in anns:
            ann_map.setdefault(ann.image_id, {}).setdefault(ann.user_id, []).append(
                ann.label.name if ann.label else ""
            )

        row = ann_map.get(image.id, {})
        row = [image.name] + ["|".join(row.get(u.id, [])) for u in users]

        yield sep.join(row) + "\n"
