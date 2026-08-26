from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import resolve as url_resolve
from django.urls import reverse

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

    def test_desc_blank_defaults(self):
        project = Project.objects.create(name="No Desc")
        project.users.add(self.user)
        self.assertEqual(project.desc, "")
        label = Label.objects.create(name="No Desc", project=self.project)
        self.assertEqual(label.desc, "")
        imageset = ImageSet.objects.create(name="No Desc", project=self.project)
        self.assertEqual(imageset.desc, "")

    def test_label_str(self):
        self.assertEqual(str(self.label), "Test Label")

    def test_label_related_name(self):
        self.assertIn(self.label, self.project.labels.all())

    def test_imageset_str(self):
        self.assertEqual(str(self.imageset), "Test ImageSet")

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
        # 512 fits; 513 chars must raise on full_clean.
        Image.objects.create(filepath="/" + "a" * 511, name="ok.png")
        too_long = Image(filepath="/" + "a" * 512, name="x.png")
        with self.assertRaises(ValidationError):
            too_long.full_clean()

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

    def test_annotation_unique_constraint_per_label(self):
        from django.db import IntegrityError, transaction

        image = Image.objects.create(
            filepath="/path/to/test/image.jpg", name="test_image.jpg"
        )
        image.imageset.add(self.imageset)
        Annotation.objects.create(
            image=image, label=self.label, user=self.user, imageset=self.imageset
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Annotation.objects.create(
                image=image,
                label=self.label,
                user=self.user,
                imageset=self.imageset,
            )

    def test_annotation_unique_constraint_per_null_label(self):
        from django.db import IntegrityError, transaction

        image = Image.objects.create(
            filepath="/path/to/test/image2.jpg", name="test_image2.jpg"
        )
        image.imageset.add(self.imageset)
        Annotation.objects.create(
            image=image, label=None, user=self.user, imageset=self.imageset
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Annotation.objects.create(
                image=image,
                label=None,
                user=self.user,
                imageset=self.imageset,
            )

    def test_annotation_allows_same_image_different_imagesets(self):
        # The shared-image feature depends on this: same (user, image) can
        # carry a different verdict per imageset, and even a NULL verdict in
        # one set does NOT block a labeled verdict in another.
        other_set = ImageSet.objects.create(name="Other Set", project=self.project)
        self.imageset.labels.add(self.label)  # ensure label attached here too
        image = Image.objects.create(
            filepath="/path/to/test/image3.jpg", name="test_image3.jpg"
        )
        image.imageset.add(self.imageset, other_set)

        Annotation.objects.create(
            image=image, label=None, user=self.user, imageset=self.imageset
        )
        # Same image, different imageset, real label -> must succeed.
        Annotation.objects.create(
            image=image, label=self.label, user=self.user, imageset=other_set
        )
        self.assertEqual(Annotation.objects.filter(image=image).count(), 2)

    def test_user_preferences_str(self):
        prefs = UserPreferences.objects.get(user=self.user)
        self.assertEqual(str(prefs), "testuser")

class ViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        cls.project = Project.objects.create(name="Test Project", desc="Test Desc")
        cls.project.users.add(cls.user)
        cls.label = Label.objects.create(
            name="Test Label", desc="Test Desc", project=cls.project
        )
        cls.imageset = ImageSet.objects.create(
            name="Test ImageSet", desc="Test Desc", project=cls.project
        )
        cls.imageset.labels.add(cls.label)

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_choose_proj_view(self):
        response = self.client.get(reverse("sortIT:choose_proj"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Project")

    def test_choose_proj_no_projects(self):
        self.project.delete()
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

    def test_label_other_plus_one_label_no_redirect_loop(self):
        """One real label + "other" -> sort mode; no label<->sort loop."""
        other = Label.objects.create(name="other", project=self.project)
        self.imageset.labels.add(other)
        image = Image.objects.create(filepath="/tmp/test.png", name="test.png")
        image.imageset.add(self.imageset)

        response = self.client.get(
            reverse("sortIT:label", kwargs={"imageset_id": self.imageset.pk})
        )
        self.assertRedirects(
            response,
            reverse("sortIT:sort", kwargs={"imageset_id": self.imageset.pk}),
        )
        # sort must render (not bounce back to label)
        response = self.client.get(
            reverse("sortIT:sort", kwargs={"imageset_id": self.imageset.pk})
        )
        self.assertEqual(response.status_code, 200)

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

    def test_darkmode_toggle_flips_prefs(self):
        from sortIT.models import UserPreferences

        url = reverse("sortIT:toggle_darkmode")
        prefs = UserPreferences.objects.get(user=self.user)
        self.assertFalse(prefs.dark_mode)

        self.client.post(url, {"next": reverse("sortIT:choose_proj")})
        prefs.refresh_from_db()
        self.assertTrue(prefs.dark_mode)

        self.client.post(url, {"next": reverse("sortIT:choose_proj")})
        prefs.refresh_from_db()
        self.assertFalse(prefs.dark_mode)

    def test_show_image_returns_file(self):
        import tempfile
        from pathlib import Path

        import PIL.Image
        from django.test.utils import override_settings

        media_tmp = tempfile.mkdtemp()
        path = Path(media_tmp) / "shown.png"
        PIL.Image.new("RGB", (8, 8), (10, 20, 30)).save(path, "PNG")
        image = Image.objects.create(filepath=str(path), name=path.name)
        image.imageset.add(self.imageset)

        with override_settings(MEDIA_ROOT=media_tmp):
            response = self.client.get(
                reverse("sortIT:show_img", kwargs={"image_id": image.pk})
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), path.read_bytes())

    def test_show_image_non_get_returns_400(self):
        image = Image.objects.create(filepath="/tmp/sg.png", name="sg.png")
        image.imageset.add(self.imageset)
        response = self.client.post(
            reverse("sortIT:show_img", kwargs={"image_id": image.pk})
        )
        self.assertEqual(response.status_code, 400)

    def test_show_montage_missing_returns_empty_200(self):
        import tempfile
        from django.test.utils import override_settings

        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            response = self.client.get(
                reverse("sortIT:show_montage", kwargs={"project_id": self.project.pk})
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")

    def test_label_view_post_updates_imsize(self):
        from sortIT.models import UserPreferences

        # Need >=2 labels so the view doesn't redirect to sort.
        label2 = Label.objects.create(name="Second", project=self.project)
        self.imageset.labels.add(label2)
        image = Image.objects.create(filepath="/tmp/lab.png", name="lab.png")
        image.imageset.add(self.imageset)
        response = self.client.post(
            reverse("sortIT:label", kwargs={"imageset_id": self.imageset.pk}),
            {"image": image.id, "imsize": 333},
        )
        self.assertEqual(response.status_code, 200)
        prefs = UserPreferences.objects.get(user=self.user)
        self.assertEqual(prefs.label_imsize, 333)

    def test_label_view_404_when_back_image_not_in_set(self):
        # Need >=2 labels so the view doesn't redirect to sort.
        label2 = Label.objects.create(name="Second", project=self.project)
        self.imageset.labels.add(label2)
        other_set = ImageSet.objects.create(name="Other Set", project=self.project)
        foreign_image = Image.objects.create(filepath="/tmp/foreign.png", name="foreign.png")
        foreign_image.imageset.add(other_set)

        response = self.client.get(
            reverse("sortIT:label", kwargs={"imageset_id": self.imageset.pk})
            + f"?image={foreign_image.id}"
        )
        self.assertEqual(response.status_code, 404)

    def test_sort_view_post_updates_nimgs_and_imsize(self):
        from sortIT.models import UserPreferences

        image = Image.objects.create(filepath="/tmp/sort_post.png", name="sp.png")
        image.imageset.add(self.imageset)
        response = self.client.post(
            reverse("sortIT:sort", kwargs={"imageset_id": self.imageset.pk}),
            {"nimgs": 8, "imsize": 444},
        )
        self.assertEqual(response.status_code, 200)
        prefs = UserPreferences.objects.get(user=self.user)
        self.assertEqual(prefs.sort_nimgs, 8)
        self.assertEqual(prefs.sort_imsize, 444)

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


class SignalTestCase(TestCase):
    def test_user_preferences_auto_created(self):
        user = User.objects.create_user(
            username="newuser", email="new@example.com", password="newpass123"
        )
        self.assertTrue(UserPreferences.objects.filter(user=user).exists())
        prefs = UserPreferences.objects.get(user=user)
        self.assertEqual(prefs.sort_nimgs, 16)
        self.assertEqual(prefs.sort_imsize, 200)


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

        projects = []
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
            projects.append(p)

        response = self.client.post(
            "/admin/sortIT/project/",
            {"action": "export_as_csv", "_selected_action": [p.id for p in projects]},
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


class CsvFieldTestCase(TestCase):
    """Unit tests for the CSV quoting helper."""

    def test_plain_value_unquoted(self):
        from sortIT.utils import _csv_field

        self.assertEqual(_csv_field("plain", ","), "plain")

    def test_empty_value_becomes_empty(self):
        from sortIT.utils import _csv_field

        self.assertEqual(_csv_field("   ", ","), "")

    def test_value_with_separator_is_quoted(self):
        from sortIT.utils import _csv_field

        self.assertEqual(_csv_field("a,b", ","), '"a,b"')

    def test_value_with_whitespace_is_quoted(self):
        from sortIT.utils import _csv_field

        self.assertEqual(_csv_field("has space", ","), '"has space"')

    def test_embedded_double_quote_is_doubled(self):
        from sortIT.utils import _csv_field

        # RFC 4180: a literal " inside a quoted field is doubled.
        self.assertEqual(_csv_field('say "hi"', ","), '"say ""hi"""')


class MontageTestCase(TestCase):
    def test_make_montage_writes_correctly_sized_canvas(self):
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
        for idx, color in enumerate(colors):
            pil_img = PIL.Image.new("RGB", (64, 64), color)
            path = Path(media_tmp) / f"test_{idx}.jpg"
            pil_img.save(path, "JPEG")
            img = Image.objects.create(filepath=str(path), name=path.name)
            img.imageset.add(imageset)

        # 15 tiles, thumb=128 -> cols=ceil(sqrt(15))=4, rows=4, canvas 512x512
        expected_size = (512, 512)

        with override_settings(MEDIA_ROOT=media_tmp):
            make_montage(project)
            out_path = Path(media_tmp) / f"montage_{project.id}.jpg"

        self.assertTrue(out_path.exists(), f"Montage not found at {out_path}")
        self.assertGreater(out_path.stat().st_size, 0)
        with PIL.Image.open(out_path) as canvas:
            self.assertEqual(canvas.size, expected_size)


class UploadDedupTestCase(TestCase):
    """Upload dedup keys on content hash, not filename."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.project = Project.objects.create(name="Dedup Project")
        self.set_a = ImageSet.objects.create(name="Set A", project=self.project)
        self.set_b = ImageSet.objects.create(name="Set B", project=self.project)

    def _img_bytes(self, color):
        import io

        import PIL.Image

        buf = io.BytesIO()
        PIL.Image.new("RGB", (32, 32), color).save(buf, "PNG")
        return buf.getvalue()

    def _upload(self, imageset, files):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test.utils import override_settings

        uploads = [
            SimpleUploadedFile(name, data, content_type="image/png")
            for name, data in files
        ]
        with override_settings(MEDIA_ROOT=self.media_tmp):
            return self.client.post(
                reverse("sortIT:upload", args=[imageset.id]),
                {"image": uploads},
            )

    def test_same_content_different_name_is_deduped(self):
        import tempfile

        self.media_tmp = tempfile.mkdtemp()
        self.client.force_login(self.user)

        bytes_a = self._img_bytes((255, 0, 0))
        r1 = self._upload(self.set_a, [("photo.jpg", bytes_a)])
        r2 = self._upload(self.set_b, [("renamed.png", bytes_a)])

        self.assertEqual(r1.status_code, 302)
        self.assertEqual(r2.status_code, 302)
        self.assertEqual(Image.objects.count(), 1)
        self.assertIn(self.set_b, Image.objects.first().imageset.all())

    def test_same_name_different_content_is_not_deduped(self):
        import tempfile

        self.media_tmp = tempfile.mkdtemp()
        self.client.force_login(self.user)

        r1 = self._upload(self.set_a, [("photo.jpg", self._img_bytes((255, 0, 0)))])
        r2 = self._upload(self.set_b, [("photo.jpg", self._img_bytes((0, 0, 255)))])

        self.assertEqual(r1.status_code, 302)
        self.assertEqual(r2.status_code, 302)
        self.assertEqual(Image.objects.count(), 2)



class BackButtonTestCase(TestCase):
    """Back button: undo the last label/sort batch and return to it."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        cls.project = Project.objects.create(name="Test Project", desc="Test Desc")
        cls.project.users.add(cls.user)
        cls.label = Label.objects.create(
            name="Test Label", desc="Test Desc", project=cls.project
        )
        cls.label2 = Label.objects.create(
            name="Test Label 2", desc="Test Desc 2", project=cls.project
        )
        # Two labels so the label page renders instead of redirecting to sort
        cls.imageset = ImageSet.objects.create(
            name="Test ImageSet", desc="Test Desc", project=cls.project
        )
        cls.imageset.labels.add(cls.label, cls.label2)

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_label_undo_returns_to_same_image(self):
        image = Image.objects.create(filepath="/tmp/undo1.png", name="undo1.png")
        self.imageset.images.add(image)

        self.client.post(
            reverse("sortIT:label_post"),
            {"image": image.id, "label": self.label.id, "imageset": self.imageset.id},
        )
        self.assertTrue(Annotation.objects.filter(image=image, user=self.user).exists())

        resp = self.client.post(reverse("sortIT:undo", args=[self.imageset.id]))
        self.assertFalse(Annotation.objects.filter(image=image, user=self.user).exists())
        self.assertEqual(
            resp["Location"],
            f"{reverse('sortIT:label', args=[self.imageset.id])}?image={image.id}",
        )

    def test_sort_undo_returns_to_same_set(self):
        imgs = [
            Image.objects.create(filepath=f"/tmp/undo{i}.png", name=f"undo{i}.png")
            for i in range(3)
        ]
        self.imageset.images.add(*imgs)
        ids = [str(i.id) for i in imgs]

        self.client.post(
            reverse("sortIT:sort_post"),
            {
                "imageset": self.imageset.id,
                "selected_images": ids[0],
                "displayed_images": ",".join(ids),
            },
        )
        self.assertEqual(
            Annotation.objects.filter(user=self.user, imageset=self.imageset).count(),
            3,
        )

        resp = self.client.post(
            reverse("sortIT:undo", args=[self.imageset.id]), {"mode": "sort"}
        )
        self.assertEqual(
            Annotation.objects.filter(user=self.user, imageset=self.imageset).count(),
            0,
        )
        self.assertEqual(
            resp["Location"],
            f"{reverse('sortIT:sort', args=[self.imageset.id])}?images={','.join(ids)}",
        )

    def test_undo_without_history_lands_in_flow(self):
        resp = self.client.post(reverse("sortIT:undo", args=[self.imageset.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], reverse("sortIT:label", args=[self.imageset.id]))

    def test_undo_chains_through_session(self):
        img1 = Image.objects.create(filepath="/tmp/chain1.png", name="chain1.png")
        img2 = Image.objects.create(filepath="/tmp/chain2.png", name="chain2.png")
        self.imageset.images.add(img1, img2)

        for img in (img1, img2):
            self.client.post(
                reverse("sortIT:label_post"),
                {"image": img.id, "label": self.label.id, "imageset": self.imageset.id},
            )

        # First back returns to the second-labeled image
        resp = self.client.post(
            reverse("sortIT:undo", args=[self.imageset.id]), {"mode": "label"}
        )
        self.assertEqual(
            resp["Location"],
            f"{reverse('sortIT:label', args=[self.imageset.id])}?image={img2.id}",
        )
        self.assertFalse(Annotation.objects.filter(image=img2, user=self.user).exists())
        self.assertTrue(Annotation.objects.filter(image=img1, user=self.user).exists())

        # Second back returns to the first-labeled image
        resp = self.client.post(
            reverse("sortIT:undo", args=[self.imageset.id]), {"mode": "label"}
        )
        self.assertEqual(
            resp["Location"],
            f"{reverse('sortIT:label', args=[self.imageset.id])}?image={img1.id}",
        )
        self.assertFalse(Annotation.objects.filter(user=self.user).exists())

class SharedImageTestCase(TestCase):
    """Option 2: an image keeps an independent decision in each imageset."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="share", email="share@example.com", password="testpass123"
        )
        cls.project = Project.objects.create(name="Shared Proj", desc="")
        cls.project.users.add(cls.user)
        cls.cat = Label.objects.create(name="cat", desc="", project=cls.project)
        cls.dog = Label.objects.create(name="dog", desc="", project=cls.project)
        cls.set_a = ImageSet.objects.create(name="Set A", desc="", project=cls.project)
        cls.set_b = ImageSet.objects.create(name="Set B", desc="", project=cls.project)
        cls.set_a.labels.add(cls.cat, cls.dog)
        cls.set_b.labels.add(cls.cat, cls.dog)
        cls.x = Image.objects.create(filepath="/tmp/shared_x.png", name="x.png")
        cls.set_a.images.add(cls.x)
        cls.set_b.images.add(cls.x)

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def label_x(self, label, imageset):
        return self.client.post(
            reverse("sortIT:label_post"),
            {"image": self.x.id, "label": label.id, "imageset": imageset.id},
        )

    def test_label_in_one_set_keeps_image_unlabeled_in_the_other(self):
        self.label_x(self.cat, self.set_a)
        self.assertEqual(
            Annotation.objects.filter(
                image=self.x, user=self.user, imageset=self.set_a
            ).count(),
            1,
        )
        self.assertEqual(
            Annotation.objects.filter(
                image=self.x, user=self.user, imageset=self.set_b
            ).count(),
            0,
        )
        # X is still offered to set B's labeler (not hidden by set A's verdict)
        resp = self.client.get(
            f"{reverse('sortIT:label', args=[self.set_b.id])}?image={self.x.id}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f"show_img/{self.x.id}")

    def test_same_image_gets_own_row_per_imageset(self):
        self.label_x(self.cat, self.set_a)
        self.label_x(self.cat, self.set_b)
        self.assertEqual(Annotation.objects.filter(image=self.x, user=self.user).count(), 2)

    def test_conflicting_labels_coexist_per_set(self):
        self.label_x(self.cat, self.set_a)
        self.label_x(self.dog, self.set_b)
        self.assertEqual(
            Annotation.objects.filter(image=self.x, user=self.user).count(), 2
        )
        names = set(
            Annotation.objects.filter(image=self.x, user=self.user)
            .exclude(label__isnull=True)
            .values_list("label__name", flat=True)
        )
        self.assertEqual(names, {"cat", "dog"})

    def test_imageset_csv_only_contains_its_own_decisions(self):
        self.label_x(self.cat, self.set_a)
        self.label_x(self.dog, self.set_b)

        from sortIT.utils import generate_csv_stream

        csv_a = "".join(generate_csv_stream(self.set_a))
        csv_b = "".join(generate_csv_stream(self.set_b))
        # Set A's row shows only cat; set B's row shows only dog
        self.assertIn("x.png,cat", csv_a)
        self.assertNotIn("dog", csv_a)
        self.assertIn("x.png,dog", csv_b)
        self.assertNotIn("cat", csv_b)
