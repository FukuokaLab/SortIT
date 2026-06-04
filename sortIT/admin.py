import csv
import datetime
import io
import zipfile

from django.contrib import admin
from django.db.models import Count
from django.http import HttpResponse, StreamingHttpResponse
from django.utils.html import format_html_join

from .models import Annotation, Image, ImageSet, Label, Project
from .utils import generate_csv_stream


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "get_labels"]
    actions = ["export_as_csv"]

    @admin.display(description="Labels")
    def get_labels(self, obj):
        return format_html_join(
            " - ",
            "{}<sub>{}</sub>",
            ((lab, lab.id) for lab in obj.labels.all()),
        )

    def export_as_csv(self, request, queryset):
        """
        Export CSV for each selected project.
        If only one project is selected, return a single CSV file.
        For multiple projects, package CSVs into a ZIP archive.
        """
        current_datetime = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        if len(queryset) == 1:
            project = queryset[0]
            csv_generator = generate_csv_stream(project)
            response = StreamingHttpResponse(csv_generator, content_type="text/csv")
            response["Content-Disposition"] = (
                f'attachment; filename="{project}_{current_datetime}.csv"'
            )
        else:
            zip_io = io.BytesIO()
            with zipfile.ZipFile(zip_io, "w", zipfile.ZIP_DEFLATED) as zf:
                for project in queryset:
                    csv_io = io.StringIO()
                    writer = csv.writer(csv_io, delimiter=",")
                    # write header
                    header_row = ["Image"] + [u.username for u in project.users.all()]
                    writer.writerow(header_row)
                    for row in generate_csv_stream(project):
                        writer.writerow(row.split(","))
                    # add to zip
                    zf.writestr(f"{project}_{current_datetime}.csv", csv_io.getvalue())
            zip_io.seek(0)
            response = HttpResponse(zip_io, content_type="application/zip")
            zip_name = f"{request.user.username}_{current_datetime}.zip"
            response["Content-Disposition"] = f'attachment; filename="{zip_name}"'
        return response

    export_as_csv.short_description = "Export as CSV"


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ["name", "project"]
    list_filter = ["project"]


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    list_filter = ["imageset", "imageset__project"]
    search_fields = ["=id", "name"]


@admin.register(ImageSet)
class ImageSetAdmin(admin.ModelAdmin):
    list_filter = ["project"]
    list_display = ["name", "project", "image_count"]
    actions = ["export_as_csv"]

    def image_count(self, obj):
        return obj.images.count()

    image_count.short_description = "Images Count"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(Count("images"))
        return queryset

    def export_as_csv(self, request, queryset):
        """
        Export all labeling data for each user by csv
        """
        current_datetime = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        imageset = queryset[0]
        csv_generator = generate_csv_stream(imageset)
        response = StreamingHttpResponse(csv_generator, content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{imageset}_{current_datetime}.csv"'
        )
        return response

    export_as_csv.short_description = "Export as CSV"


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ["image_id", "label", "user"]
    search_fields = ["=image__id"]
