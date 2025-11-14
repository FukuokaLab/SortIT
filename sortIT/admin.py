import datetime
from pathlib import Path

from django.contrib import admin, messages
from django.db.models import Count
from django.http import StreamingHttpResponse
from django.utils.html import format_html, format_html_join
from django.utils.translation import ngettext

from .models import Annotation, Image, ImageSet, Label, User, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "get_labels"]

    @admin.display(description="Labels")
    def get_labels(self, obj):
        return format_html_join(
            " - ",
            "{}<sub>{}</sub>",
            ((lab, lab.id) for lab in obj.labels.all()),
        )


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ["name", "project"]
    list_filter = ["project"]


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ["filepath"]
    list_filter = ["imageset"]

    # actions = ["remove_label"]
    #
    # @admin.action(description="Remove labels for selected images")
    # def remove_annoatations(self, request, queryset):
    #     updated = queryset.update(label=None)
    #     self.message_user(
    #         request,
    #         ngettext(
    #             "%d label was changed to 'None'.",
    #             "%d labels were changed to 'None'.",
    #             updated,
    #         )
    #         % updated,
    #         messages.SUCCESS,
    #     )


def generate_csv_stream(separator=",", image_set=None):
    """
    Generator function to stream CSV data
    """
    header_row = ["Image Name"] + [user.username for user in User.objects.all()]
    yield (separator.join(header_row) + "\n")

    # write data row
    images = Image.objects.filter(imageset=image_set)
    for image in images:
        ext = Path(image.filepath).name.split(".")[-2]
        row = [Path(image.filepath).stem.split("___")[0] + "." + ext]
        annotations = Annotation.objects.filter(image=image)

        annotation_dict = {
            annotation.user.username: annotation.label.name
            for annotation in annotations
            if annotation.label is not None
        }

        # Write the label name of the Annotation for each user (leave blank if not present)
        for user in User.objects.all():
            user_label = annotation_dict.get(user.username, "")
            row.append(user_label)

        yield (separator.join(row) + "\n")


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
        Export all rabeling data for each user by csv (semi-colon)
        """
        csv_generator = generate_csv_stream(separator=",", image_set=queryset[0])
        response = StreamingHttpResponse(csv_generator, content_type="text/csv")
        current_datetime = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        response["Content-Disposition"] = (
            f'attachment; filename="image_set{queryset[0]}_{current_datetime}.csv"'
        )
        return response

    export_as_csv.short_description = "Export as CSV"


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ["image__id", "label", "user"]
