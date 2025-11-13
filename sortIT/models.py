import os

from django.contrib.auth.models import User
from django.db import models
from django.dispatch import receiver


class Project(models.Model):
    name = models.CharField(max_length=100, default=None)
    desc = models.TextField("Description", default=None, blank=True)

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
        Project, on_delete=models.CASCADE, related_name="imageset"
    )
    labels = models.ManyToManyField(Label, related_name="imageset")
    timespent = models.DurationField()

    def __str__(self):
        return self.name


class Image(models.Model):
    imageset = models.ManyToManyField(ImageSet, related_name="images")
    filepath = models.FilePathField(path="data/patches", recursive=True)

    def __str__(self):
        return str(self.filepath)


class Annotation(models.Model):
    image = models.ForeignKey(
        Image, on_delete=models.CASCADE, related_name="annotation"
    )
    label = models.ForeignKey(Label, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    time = models.DateTimeField(auto_now_add=True)
