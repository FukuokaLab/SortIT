"""
Export annotations as csv
usage:
$ python manage.py export_csv --output annotations.csv --project ColonPolyp
"""

import csv

from django.core.management import CommandError
from django.core.management.base import BaseCommand

from sortIT.models import Image, Project
from sortIT.utils import _memberships, annotation_map

__date__ = "2026-01-21"
__email__ = " ethan <at> nagasaki-u.ac.jp "


class Command(BaseCommand):
    help = "Export labeled images to CSV with one column per user"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="annotations.csv",
            help="Output CSV file",
        )
        parser.add_argument(
            "--project",
            type=str,
            required=True,
            help="Project ID or project name",
        )

    def handle(self, *args, **options):
        output_path = options["output"]
        project_arg = options["project"]

        # Resolve project (ID or name)
        try:
            if project_arg.isdigit():
                project = Project.objects.get(id=int(project_arg))
            else:
                project = Project.objects.get(name=project_arg)
        except Project.DoesNotExist:
            raise CommandError(f"Project not found: {project_arg}")

        users = list(project.users.all())

        images = (
            Image.objects.filter(
                imageset__project=project,
                annotations__isnull=False,
            )
            .distinct()
            .order_by("id")
            .prefetch_related("imageset")
        )

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["Image_ID", "imageset", "filename"] + [u.username for u in users]
            )

            ann_map = annotation_map(project, users)

            for image, imageset in _memberships(images):
                cells = ann_map.get((image.id, imageset.id), {})
                writer.writerow(
                    [str(image.id), imageset.name, image.name]
                    + [cells.get(u.id, "") for u in users]
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Exported annotations from project '{project.name}' to {output_path}"
            )
        )
