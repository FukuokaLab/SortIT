#!/usr/bin/env python
"""
Export annotations as csv
usage:
$ python manage.py export_csv --output annotations.csv --project ColonPolyp
"""

import csv

from django.contrib.auth.models import User
from django.core.management import CommandError
from django.core.management.base import BaseCommand

from sortIT.models import Annotation, Image, Project

__date__ = "2026-01-21"
__email__ = " ethan <at> nagasaki-u.ac.jp "


def batched_queryset(qs, batch_size=500):
    start = 0
    while True:
        batch = list(qs[start : start + batch_size])
        if not batch:
            break
        yield batch
        start += batch_size


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

        users = list(User.objects.order_by("id"))

        base_images = (
            Image.objects.filter(
                imageset__project=project,
                annotations__isnull=False,
            )
            .distinct()
            .order_by("id")
        )

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Image_ID", "filepath"] + [u.username for u in users])

            for image_batch in batched_queryset(base_images, batch_size=500):
                image_ids = [img.id for img in image_batch]

                annotations = Annotation.objects.filter(
                    image_id__in=image_ids,
                    imageset__project=project,
                ).select_related("user", "label")

                ann_map = {}
                for ann in annotations:
                    ann_map.setdefault(ann.image_id, {}).setdefault(
                        ann.user_id, []
                    ).append(ann.label.name if ann.label else "")

                for image in image_batch:
                    row = ann_map.get(image.id, {})
                    writer.writerow(
                        [str(image.id), image.filepath] + ["|".join(row.get(u.id, [])) for u in users]
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {base_images.count()} images from project '{project.name}' "
                f"to {output_path}"
            )
        )
