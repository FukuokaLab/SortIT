from django.contrib.auth.models import User
from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=100)
    desc = models.TextField("Description", blank=True)
    users = models.ManyToManyField(User, related_name="projects")

    def __str__(self):
        return self.name

    @property
    def has_images(self):
        return Image.objects.filter(imageset__project=self).exists()


class Label(models.Model):
    name = models.CharField(max_length=100)
    desc = models.TextField("Description", blank=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="labels"
    )

    def __str__(self):
        return self.name


class ImageSet(models.Model):
    name = models.CharField(max_length=100)
    desc = models.TextField("Description", blank=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="imagesets"
    )
    labels = models.ManyToManyField(Label, related_name="imagesets")

    def __str__(self):
        return self.name


class Image(models.Model):
    imageset = models.ManyToManyField(ImageSet, related_name="images")
    filepath = models.CharField(max_length=512, editable=False)
    name = models.CharField(max_length=100)
    sha256 = models.CharField(max_length=64, editable=False, blank=True, default="")

    def __str__(self):
        return self.filepath


class Annotation(models.Model):
    image = models.ForeignKey(
        Image, on_delete=models.CASCADE, related_name="annotations"
    )
    label = models.ForeignKey(Label, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    imageset = models.ForeignKey(ImageSet, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "image", "label"],
                name="unique_user_image_label",
            ),
            models.UniqueConstraint(
                fields=["user", "image"],
                condition=models.Q(label__isnull=True),
                name="unique_user_image_null_label",
            ),
        ]


class UserPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="prefs")
    sort_nimgs = models.PositiveIntegerField(default=16)
    sort_imsize = models.PositiveIntegerField(default=200)
    label_imsize = models.PositiveIntegerField(default=200)
    dark_mode = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}"
