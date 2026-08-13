from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import resolve as url_resolve
from django.urls import reverse

from account.forms import LoginForm, MyPasswordChangeForm, SignupForm, UserUpdateForm
from sortIT.forms import ImageForm
from sortIT.models import Annotation, Image, ImageSet, Label, Project, UserPreferences
from sortIT.utils import annotation_map


class ModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.project = Project.objects.create(
            name="Test Project",
            desc="Test Description",
        )
        self.project.users.add(self.user)
        self.label = Label.objects.create(
            name="Test Label",
            desc="Test Label Description",
            project=self.project,
        )
        self.imageset = ImageSet.objects.create(
            name="Test ImageSet",
            desc="Test ImageSet Description",
            project=self.project,
        )
        self.imageset.labels.add(self.label)

    def test_project_str(self):
        self.assertEqual(str(self.project), "Test Project")

    def test_project_max_name_length(self):
        project = Project(name="a" * 101)
        with self.assertRaises(ValidationError):
            project.full_clean()

    def test_project_desc_blank(self):
        project = Project.objects.create(name="No Desc")
        project.users.add(self.user)
        self.assertEqual(project.desc, "")

    def test_project_users_m2m(self):
        user2 = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )
        self.project.users.add(user2)
        self.assertEqual(self.project.users.count(), 2)

    def test_label_str(self):
        self.assertEqual(str(self.label), "Test Label")

    def test_label_desc_blank(self):
        label = Label.objects.create(name="No Desc", project=self.project)
        self.assertEqual(label.desc, "")

    def test_label_related_name(self):
        self.assertIn(self.label, self.project.labels.all())

    def test_label_cascade_on_project_delete(self):
        label_id = self.label.id
        self.project.delete()
        self.assertFalse(Label.objects.filter(id=label_id).exists())

    def test_imageset_str(self):
        self.assertEqual(str(self.imageset), "Test ImageSet")

    def test_imageset_desc_blank(self):
        imageset = ImageSet.objects.create(name="No Desc", project=self.project)
        self.assertEqual(imageset.desc, "")

    def test_imageset_labels_m2m(self):
        label2 = Label.objects.create(name="Second Label", project=self.project)
        self.imageset.labels.add(label2)
        self.assertEqual(self.imageset.labels.count(), 2)

    def test_imageset_cascade_on_project_delete(self):
        imageset_id = self.imageset.id
        self.project.delete()
        self.assertFalse(ImageSet.objects.filter(id=imageset_id).exists())

    def test_image_creation_and_str(self):
        image = Image.objects.create(
            filepath="/path/to/test/image.png", name="test_image.png"
        )
        image.imageset.add(self.imageset)
        self.assertEqual(image.name, "test_image.png")
        self.assertEqual(str(image), "/path/to/test/image.png")

    def test_image_multiple_imagesets(self):
        imageset2 = ImageSet.objects.create(
            name="Another ImageSet", project=self.project
        )
        image = Image.objects.create(
            filepath="/path/to/test/image2.png", name="image2.png"
        )
        image.imageset.add(self.imageset)
        image.imageset.add(imageset2)
        self.assertEqual(image.imageset.count(), 2)

    def test_image_filepath_max_length(self):
        long_path = "/" + "a" * 511
        image = Image.objects.create(filepath=long_path, name="test.png")
        self.assertEqual(len(image.filepath), 512)

    def test_annotation_creation(self):
        image = Image.objects.create(
            filepath="/path/to/test/image.jpg", name="test_image.jpg"
        )
        image.imageset.add(self.imageset)
        annotation = Annotation.objects.create(
            image=image, label=self.label, user=self.user, imageset=self.imageset
        )
        self.assertEqual(annotation.image, image)
        self.assertEqual(annotation.label, self.label)
        self.assertEqual(annotation.user, self.user)
        self.assertEqual(annotation.imageset, self.imageset)
        self.assertIsNotNone(annotation.timestamp)

    def test_annotation_null_label(self):
        image = Image.objects.create(
            filepath="/path/to/test/image.jpg", name="test_image.jpg"
        )
        image.imageset.add(self.imageset)
        annotation = Annotation.objects.create(
            image=image, label=None, user=self.user, imageset=self.imageset
        )
        self.assertIsNone(annotation.label)

    def test_annotation_cascade_on_image_delete(self):
        image = Image.objects.create(
            filepath="/path/to/test/image.jpg", name="test_image.jpg"
        )
        image.imageset.add(self.imageset)
        annotation = Annotation.objects.create(
            image=image, label=self.label, user=self.user, imageset=self.imageset
        )
        annotation_id = annotation.id
        image.delete()
        self.assertFalse(Annotation.objects.filter(id=annotation_id).exists())

    def test_annotation_cascade_on_user_delete(self):
        user2 = User.objects.create_user(
            username="testuser2", email="test2@example.com", password="testpass123"
        )
        image = Image.objects.create(
            filepath="/path/to/test/image.jpg", name="test_image.jpg"
        )
        image.imageset.add(self.imageset)
        annotation = Annotation.objects.create(
            image=image, label=self.label, user=user2, imageset=self.imageset
        )
        annotation_id = annotation.id
        user2.delete()
        self.assertFalse(Annotation.objects.filter(id=annotation_id).exists())

    def test_user_preferences_defaults(self):
        prefs = UserPreferences.objects.get(user=self.user)
        self.assertEqual(prefs.nimgs, 16)
        self.assertEqual(prefs.imsize, 200)

    def test_user_preferences_str(self):
        prefs = UserPreferences.objects.get(user=self.user)
        self.assertEqual(str(prefs), "testuser")

    def test_user_preferences_cascade_on_user_delete(self):
        prefs_id = UserPreferences.objects.get(user=self.user).id
        self.user.delete()
        self.assertFalse(UserPreferences.objects.filter(id=prefs_id).exists())


class ViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.project = Project.objects.create(name="Test Project", desc="Test Desc")
        self.project.users.add(self.user)
        self.label = Label.objects.create(
            name="Test Label", desc="Test Desc", project=self.project
        )
        self.imageset = ImageSet.objects.create(
            name="Test ImageSet", desc="Test Desc", project=self.project
        )
        self.imageset.labels.add(self.label)
        self.client.login(username="testuser", password="testpass123")

    def test_choose_proj_view(self):
        response = self.client.get(reverse("sortIT:choose_proj"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Project")

    def test_choose_proj_no_projects(self):
        self.project.delete()
        Project.objects.all().delete()
        response = self.client.get(reverse("sortIT:choose_proj"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/sortIT/project/add/")

    def test_choose_proj_unauthenticated(self):
        self.client.logout()
        response = self.client.get(reverse("sortIT:choose_proj"))
        self.assertEqual(response.status_code, 302)

    def test_choose_img_set_view(self):
        response = self.client.get(
            reverse("sortIT:choose_img_set", kwargs={"project_id": self.project.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test ImageSet")

    def test_choose_img_set_no_sets(self):
        self.imageset.delete()
        response = self.client.get(
            reverse("sortIT:choose_img_set", kwargs={"project_id": self.project.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/sortIT/imageset/add/")

    def test_download_proj_csv(self):
        response = self.client.get(
            reverse("sortIT:down_proj_csv", kwargs={"project_id": self.project.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_download_imset_csv(self):
        response = self.client.get(
            reverse("sortIT:down_imset_csv", kwargs={"imageset_id": self.imageset.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_download_csv_post_bad_request(self):
        response = self.client.post(
            reverse("sortIT:down_proj_csv", kwargs={"project_id": self.project.pk})
        )
        self.assertEqual(response.status_code, 400)

    def test_sort_view_redirects_to_label_multi_labels(self):
        label2 = Label.objects.create(name="Label 2", project=self.project)
        self.imageset.labels.add(label2)
        response = self.client.get(
            reverse("sortIT:sort", kwargs={"imageset_id": self.imageset.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("sortIT:label", kwargs={"imageset_id": self.imageset.pk}),
        )

    def test_sort_view_shows_single_label(self):
        image = Image.objects.create(filepath="/tmp/test.png", name="test.png")
        image.imageset.add(self.imageset)
        response = self.client.get(
            reverse("sortIT:sort", kwargs={"imageset_id": self.imageset.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_sort_view_redirects_to_finish_when_all_sorted(self):
        image = Image.objects.create(filepath="/tmp/test.png", name="test.png")
        image.imageset.add(self.imageset)
        Annotation.objects.create(
            image=image, label=self.label, user=self.user, imageset=self.imageset
        )
        response = self.client.get(
            reverse("sortIT:sort", kwargs={"imageset_id": self.imageset.pk})
        )
        self.assertRedirects(response, reverse("sortIT:finish"))

    def test_sort_post_selects_images_null_label(self):
        image = Image.objects.create(filepath="/tmp/test.png", name="test.png")
        image.imageset.add(self.imageset)
        self.client.post(
            reverse("sortIT:sort_post"),
            {
                "imageset": self.imageset.id,
                "selected_images": str(image.id),
                "displayed_images": str(image.id),
            },
        )
        annotation = Annotation.objects.get(image=image, user=self.user)
        self.assertIsNone(annotation.label)

    def test_sort_post_unselected_images_get_label(self):
        image = Image.objects.create(filepath="/tmp/test.png", name="test.png")
        image.imageset.add(self.imageset)
        self.client.post(
            reverse("sortIT:sort_post"),
            {
                "imageset": self.imageset.id,
                "selected_images": "",
                "displayed_images": str(image.id),
            },
        )
        annotation = Annotation.objects.get(image=image, user=self.user)
        self.assertEqual(annotation.label, self.label)

    def test_sort_post_get_bad_request(self):
        response = self.client.get(reverse("sortIT:sort_post"))
        self.assertEqual(response.status_code, 400)

    def test_label_view_redirects_to_sort_single_label(self):
        image = Image.objects.create(filepath="/tmp/test.png", name="test.png")
        image.imageset.add(self.imageset)
        response = self.client.get(
            reverse("sortIT:label", kwargs={"imageset_id": self.imageset.pk})
        )
        self.assertRedirects(
            response,
            reverse("sortIT:sort", kwargs={"imageset_id": self.imageset.pk}),
        )

    def test_label_view_redirects_to_finish_when_done(self):
        label2 = Label.objects.create(name="Label 2", project=self.project)
        label3 = Label.objects.create(name="Label 3", project=self.project)
        self.imageset.labels.add(label2, label3)
        image = Image.objects.create(filepath="/tmp/test.png", name="test.png")
        image.imageset.add(self.imageset)
        Annotation.objects.create(
            image=image, label=label2, user=self.user, imageset=self.imageset
        )
        response = self.client.get(
            reverse("sortIT:label", kwargs={"imageset_id": self.imageset.pk})
        )
        self.assertRedirects(response, reverse("sortIT:finish"))

    def test_label_view_shows_multi_labels(self):
        label2 = Label.objects.create(name="Label 2", project=self.project)
        label3 = Label.objects.create(name="Label 3", project=self.project)
        self.imageset.labels.add(label2, label3)
        image = Image.objects.create(filepath="/tmp/test.png", name="test.png")
        image.imageset.add(self.imageset)
        response = self.client.get(
            reverse("sortIT:label", kwargs={"imageset_id": self.imageset.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Label 2")

    def test_label_post_creates_annotation(self):
        label2 = Label.objects.create(name="Label 2", project=self.project)
        self.imageset.labels.add(label2)
        image = Image.objects.create(filepath="/tmp/test.png", name="test.png")
        image.imageset.add(self.imageset)
        response = self.client.post(
            reverse("sortIT:label_post"),
            {
                "image": image.id,
                "label": label2.id,
                "imageset": self.imageset.id,
            },
        )
        self.assertEqual(response.status_code, 302)
        annotation = Annotation.objects.get(image=image, user=self.user)
        self.assertEqual(annotation.label, label2)

    def test_label_post_missing_params(self):
        response = self.client.post(reverse("sortIT:label_post"), {"image": "999"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please select an image and a label.")

    def test_label_post_nonexistent_image(self):
        response = self.client.post(
            reverse("sortIT:label_post"),
            {
                "image": "99999",
                "label": self.label.id,
                "imageset": self.imageset.id,
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_finish_view(self):
        response = self.client.get(reverse("sortIT:finish"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SortIT")

    def test_finish_view_unauthenticated(self):
        self.client.logout()
        response = self.client.get(reverse("sortIT:finish"))
        self.assertEqual(response.status_code, 302)


class URLTestCase(TestCase):
    def test_url_resolution(self):
        self.assertEqual(url_resolve("/sortIT/").func.__name__, "choose_proj")
        self.assertEqual(
            url_resolve("/sortIT/project/1").func.__name__, "choose_img_set"
        )
        self.assertEqual(url_resolve("/sortIT/upload/1").func.__name__, "image_upload")
        self.assertEqual(url_resolve("/sortIT/finish").func.__name__, "finish")

    def test_reverse_urls(self):
        self.assertEqual(reverse("sortIT:choose_proj"), "/sortIT/")
        self.assertEqual(
            reverse("sortIT:choose_img_set", kwargs={"project_id": 1}),
            "/sortIT/project/1",
        )
        self.assertEqual(
            reverse("sortIT:upload", kwargs={"imageset_id": 1}),
            "/sortIT/upload/1",
        )
        self.assertEqual(reverse("sortIT:finish"), "/sortIT/finish")
        self.assertEqual(reverse("sortIT:sort_post"), "/sortIT/sort_post")
        self.assertEqual(reverse("sortIT:label_post"), "/sortIT/label_post")
        self.assertEqual(
            reverse("sortIT:down_proj_csv", kwargs={"project_id": 1}),
            "/sortIT/project/1/download_csv",
        )
        self.assertEqual(
            reverse("sortIT:down_imset_csv", kwargs={"imageset_id": 1}),
            "/sortIT/imagesets/1/download_csv",
        )


class FormTestCase(TestCase):
    def test_image_form_valid(self):
        form = ImageForm(data={})
        self.assertTrue(form.is_valid())

    def test_image_form_model(self):
        self.assertEqual(ImageForm._meta.model, Image)
        self.assertIn("image", ImageForm._meta.fields)

    def test_signup_form_valid(self):
        form_data = {
            "username": "newuser",
            "email": "new@example.com",
            "first_name": "First",
            "last_name": "Last",
            "password1": "Str0ngP@ssw0rd!",
            "password2": "Str0ngP@ssw0rd!",
        }
        form = SignupForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_signup_form_missing_password(self):
        form_data = {
            "username": "newuser",
            "email": "new@example.com",
            "first_name": "First",
            "last_name": "Last",
            "password1": "",
            "password2": "",
        }
        form = SignupForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("password1", form.errors)

    def test_signup_form_password_mismatch(self):
        form_data = {
            "username": "newuser",
            "email": "new@example.com",
            "first_name": "First",
            "last_name": "Last",
            "password1": "Str0ngP@ssw0rd!",
            "password2": "DifferentP@ss!",
        }
        form = SignupForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_user_update_form_valid(self):
        user = User.objects.create_user(
            username="updatetest", email="up@example.com", password="testpass123"
        )
        form_data = {
            "username": "updatetest",
            "email": "new@example.com",
            "first_name": "First",
            "last_name": "Last",
        }
        form = UserUpdateForm(data=form_data, instance=user)
        self.assertTrue(form.is_valid())

    def test_login_form_renders(self):
        form = LoginForm()
        self.assertIn("form-control", form.as_p())

    def test_password_change_form_renders(self):
        user = User.objects.create_user(
            username="pwtest", email="pw@example.com", password="testpass123"
        )
        form = MyPasswordChangeForm(user=user)
        self.assertIn("form-control", form.as_p())


class SignalTestCase(TestCase):
    def test_user_preferences_auto_created(self):
        user = User.objects.create_user(
            username="newuser", email="new@example.com", password="newpass123"
        )
        self.assertTrue(UserPreferences.objects.filter(user=user).exists())
        prefs = UserPreferences.objects.get(user=user)
        self.assertEqual(prefs.nimgs, 16)
        self.assertEqual(prefs.imsize, 200)


class AdminTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.client = Client()
        self.client.login(username="admin", password="adminpass123")

    def test_project_admin(self):
        Project.objects.create(name="Admin Test Project", desc="Admin Desc")
        response = self.client.get("/admin/sortIT/project/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Test Project")

    def test_export_as_csv_multi_project_zip(self):
        """ZIP export of multiple projects: each CSV has exactly one header row."""
        import io
        import zipfile

        for i in range(2):
            p = Project.objects.create(name=f"Zip Proj {i}", desc="d")
            p.users.add(self.user)
            label = Label.objects.create(name="Keep", project=p)
            imageset = ImageSet.objects.create(name=f"Set {i}", project=p)
            imageset.labels.add(label)
            image = Image.objects.create(filepath=f"/tmp/{i}.jpg", name=f"{i}.jpg")
            image.imageset.add(imageset)
            Annotation.objects.create(
                image=image, label=label, user=self.user, imageset=imageset
            )

        response = self.client.post(
            "/admin/sortIT/project/",
            {"action": "export_as_csv", "_selected_action": [1, 2]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            self.assertEqual(len(zf.namelist()), 2)
            for name in zf.namelist():
                lines = zf.read(name).decode().strip().split("\n")
                self.assertEqual(
                    lines[0],
                    "Image_ID,Image,admin",
                    f"bad header in {name}: {lines[0]}",
                )
                self.assertEqual(
                    lines.count("Image_ID,Image,admin"),
                    1,
                    f"duplicate header in {name}",
                )
                # row matches its own project: "Zip Proj <i>...csv" -> "<i>.jpg"
                i = name.split(" ")[2].split("_")[0]
                self.assertEqual(lines[1].split(",")[1:], [f"{i}.jpg", "Keep"])


class AnnotationMapTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="maptest", email="mt@example.com", password="testpass123"
        )
        self.project = Project.objects.create(name="Map Test")
        self.project.users.add(self.user)
        self.label = Label.objects.create(name="Tumor", project=self.project)
        self.imageset = ImageSet.objects.create(name="Set", project=self.project)
        self.imageset.labels.add(self.label)

    def test_annotation_map_groups_labels_per_user(self):
        img1 = Image.objects.create(filepath="/tmp/1.jpg", name="1.jpg")
        img1.imageset.add(self.imageset)
        img2 = Image.objects.create(filepath="/tmp/2.jpg", name="2.jpg")
        img2.imageset.add(self.imageset)

        Annotation.objects.create(
            image=img1, label=self.label, user=self.user, imageset=self.imageset
        )
        Annotation.objects.create(
            image=img2, label=None, user=self.user, imageset=self.imageset
        )

        ann_map = annotation_map(self.project, [self.user])
        self.assertEqual(ann_map[img1.id][self.user.id], ["Tumor"])
        self.assertEqual(ann_map[img2.id][self.user.id], [""])

    def test_annotation_map_respects_image_ids(self):
        img = Image.objects.create(filepath="/tmp/1.jpg", name="1.jpg")
        img.imageset.add(self.imageset)
        Annotation.objects.create(
            image=img, label=self.label, user=self.user, imageset=self.imageset
        )

        ann_map = annotation_map(self.project, [self.user], image_ids=[img.id])
        self.assertIn(img.id, ann_map)
        # Unknown image id -> no annotations returned
        ann_map_empty = annotation_map(self.project, [self.user], image_ids=[99999])
        self.assertEqual(ann_map_empty, {})


class MontageTestCase(TestCase):
    def test_make_montage_output(self):
        """Generate a montage and copy to /tmp for visual inspection."""
        import shutil
        import tempfile
        from pathlib import Path

        import PIL.Image
        from django.test.utils import override_settings

        from sortIT.views import make_montage

        user = User.objects.create_user(
            username="montest", email="mt@example.com", password="testpass123"
        )
        project = Project.objects.create(name="Montage Test")
        project.users.add(user)
        imageset = ImageSet.objects.create(name="Test Set", project=project)

        media_tmp = tempfile.mkdtemp()

        # Create 15 colored test images
        colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
            (255, 0, 255),
            (0, 255, 255),
            (128, 0, 0),
            (0, 128, 0),
            (0, 0, 128),
            (128, 128, 0),
            (128, 0, 128),
            (0, 128, 128),
            (64, 64, 64),
            (192, 192, 192),
            (255, 128, 0),
        ]
        img_paths = []
        for idx, color in enumerate(colors):
            pil_img = PIL.Image.new("RGB", (64, 64), color)
            path = Path(media_tmp) / f"test_{idx}.jpg"
            pil_img.save(path, "JPEG")
            img_paths.append(path)

        with override_settings(MEDIA_ROOT=media_tmp):
            for path in img_paths:
                img = Image.objects.create(filepath=str(path), name=path.name)
                img.imageset.add(imageset)

            make_montage(project)

            src = Path(media_tmp) / f"montage_{project.id}.jpg"
            dst = Path("/tmp/montage_test_output.jpg")
            shutil.copy(src, dst)
            self.assertTrue(dst.exists(), f"Montage not found at {dst}")
            print(f"\nMontage written to {dst}")
