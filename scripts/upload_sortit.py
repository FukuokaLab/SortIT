# upload_script.py
import os
from pathlib import Path

import tqdm
import sys


# 1. Point to your Django project root (where manage.py lives)
PROJECT_ROOT = os.getenv("PWD")
sys.path.append(PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

import django

django.setup()

from sortIT.models import Image, ImageSet, Project
from sortIT.views import make_montage

for FOLDER in Path("/home/aliya/projects/colonpolyp/data/patches").iterdir():
    label = FOLDER.name
    imageset_id = ImageSet.objects.get(name=label).pk

    for filepath in tqdm.tqdm(FOLDER.iterdir(), desc=label):
        if not os.path.isfile(filepath):
            continue

        image = Image.objects.create(filepath=filepath, name=filepath.name)
        image.imageset.set([imageset_id])
        image.save()

project = Project.objects.get(name="ColonPolyp")
make_montage(project)
