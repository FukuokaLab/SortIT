from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
import os
#from admin_thumbnails.thumbnail import AdminThumbnail

class ImageSet(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name

class Image(models.Model):
    image_set = models.ForeignKey(ImageSet, on_delete=models.CASCADE, related_name='images')
    file_path = models.FilePathField()
    #image_tag = AdminThumbnail(image_field='file_path')

    def __str__(self):
        return self.file_path

@receiver(models.signals.post_delete, sender=Image)
def delete_file(sender, instance, **kwargs):

    if os.path.isfile(instance.file_path):
        os.remove(instance.file_path)

class Label(models.Model):
    imageset = models.ForeignKey(ImageSet, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Annotation(models.Model):
    image = models.ForeignKey(Image, on_delete=models.CASCADE, related_name='annotations')
    label = models.ForeignKey(Label, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
