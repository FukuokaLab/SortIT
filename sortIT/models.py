import datetime

from django.contrib.auth.models import User
from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=100, default=None)
    desc = models.TextField("Description", default=None, blank=True)
    users = models.ManyToManyField(User, related_name="projects")

    def __str__(self):
        return self.name


class Label(models.Model):
    name = models.CharField(max_length=100)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="labels"
    )

    def __str__(self):
        return self.name


class ImageSet(models.Model):
    name = models.CharField(max_length=100)
    desc = models.TextField("Description", default=None, blank=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="imagesets"
    )
    labels = models.ManyToManyField(Label, related_name="imagesets")
    tatime = models.DurationField(
        default=datetime.timedelta(),
        editable=False,
        help_text="Turnaround time, or time spent labeling this set",
    )

    def __str__(self):
        return self.name


class Image(models.Model):
    imageset = models.ManyToManyField(ImageSet, related_name="images")
    sortedsets = models.ManyToManyField(ImageSet, null=True)
    filepath = models.FilePathField(editable=False)
    name = models.CharField(max_length=100)

    def __str__(self):
        return str(self.filepath)


class Annotation(models.Model):
    image = models.ForeignKey(
        Image, on_delete=models.CASCADE, related_name="annotations"
    )
    label = models.ForeignKey(Label, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class UserPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="prefs")
    nimgs = models.PositiveIntegerField(default=16)
    imsize = models.PositiveIntegerField(default=200)

    def __str__(self):
        return f"{self.user.username}"
