* [x] add user settings DB @done(11/14/25 21:17)
* [x] write README @done(11/18/25 00:51)
* [x] add guide about deploying production server @done(20260604 23:41)
* [x] documentation @done(20260604 23:41)
- [x] make port configurable in docker @done(20260814 10:56)
* [ ] update labeling page (multi-label sorting)
* [ ] imageset with multiple classes, but make it possible to select one label, then binary filter it
* [ ] all negative (filtered out) tiles will be sent to "labeling" for class labeling
* [ ] handle annotation conflicts (overwriting image labels)
* [ ] when deleting images on the admin page, also delete the file in media/
- [ ] finished set > thanks page redirects back to imagesets for project after timeout ( 3 seconds) + button to return to imageset page
- [ ] download page improvements (filter by project/imageset/annotator)
- [x] document that uploads are deduped by content hash and renamed per imageset (README assumptions) @done(20260908)
- [x] does a label get overwritten if included in two imagesets?
  - no: separate annotations are kept per (user, image, imageset), so one image can carry a different verdict in each set


## Manual feature verification checklist

Run each check twice — once on the local install, once on Docker — and tick the matching box.

### Local install (one-time setup)

```bash
uv sync                    # or: pip install -r requirements.txt
cp .env.example .env       # edit .env and set SECRET_KEY to a random value
mkdir -p media

source .venv/bin/activate
python manage.py migrate   # migrations ship with the repo; data/ is created automatically
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

> `SECRET_KEY` is mandatory — the app refuses to start without it.

### Docker install (one-time setup)

```bash
cp .env.example .env       # edit .env and set SECRET_KEY
# optional: set DJANGO_SUPERUSER_* for auto-created admin (see .env.example)
docker compose up -d --build
docker compose ps          # expect Status: healthy
```

> `entrypoint.sh` auto-runs makemigrations, migrate and collectstatic, then starts gunicorn. No manual DB steps.

### Feature checks

- [x] Local
  - [x] `http://localhost:8000/account/login/` loads with styling (no broken static files) @done(20260814 14:31)
  - [x] Visiting `/sortIT/` while logged out redirects to the login page @done(20260814 14:31)
  - [x] Sign up a new user → lands on the sign-up done page @done(20260814 14:31)
  - [x] New user can log in with the credentials just created @done(20260814 14:32)
  - [x] `/account/my_page/<id>/` shows the profile; edit + save works @done(20260814 16:56)
  - [x] Password change works @done(20260814 16:56)
  - [x] Logout returns to the login page @done(20260814 14:32)
  - [x] Admin: create a Project, add users, create a Label and an ImageSet, attach the label @done(20260814 17:56)
  - [x] Admin: project list shows labels; imageset list shows image count @done(20260814 17:56)
  - [x] As staff: upload a single image to an ImageSet → it appears in the set @done(20260814 17:56)
  - [x] Upload multiple images at once (multi-select) @done(20260814 17:56)
  - [x] Re-upload the same filename to another ImageSet → associated, NOT duplicated in DB or media @done(20260814 17:57)
  - [x] Uploading regenerates the montage (check `media/montage_<project_id>.jpg` timestamp) @done(20260814 18:17)
  - [x] Montage page shows the grid, thumbnails centered in their cells, no excess bottom whitespace @done(20260814 18:18)
  - [x] Sorting mode (ImageSet with 1 label): shows up to `nimgs` images, Keep/Discard works, progress advances @done(20260814 18:20)
  - [x] Sorting page: changing nimgs/imsize persists for the user (check next page + admin UserPreferences) @done(20260814 18:21)
  - [x] When all images are sorted → finish/thank-you page @done(20260814 18:19)
  - [x] Labeling mode (ImageSet with 2+ labels): pick a label per image, progress advances @done(20260814 18:28)
  - [x] ImageSet with 1 label, or 2 labels incl. one named "other" → redirects to sorting mode instead @done(20260814 22:42) 
  - [x] When all images are labeled → finish page @done(20260814 22:42)
  - [x] CSV export, project level (`/sortIT/project/<id>/download_csv`): header `Image_ID,imageset,filename,<user...>`, one row per (image, image set) @done(20260814 22:43)
  - [x] CSV export, imageset level (`/sortIT/imagesets/<id>/download_csv`) @done(20260814 22:44) 
  - [x] Admin: select 2+ projects → action "Export as CSV" → ZIP; each inner CSV has exactly ONE header row @done(20260814 22:45) 
  - [x] CLI export: `python manage.py export_csv --project <name>` (docker: `docker compose exec web python ...`) → `Image_ID,imageset,filename,<user...>` @done(20260814 22:45) 
  - [x] A label containing a comma survives CSV export un-corrupted (e.g. name a label `a, b`) @done(20260820 10:23) 
  - [x] Annotations from two users on the same image both appear as separate columns @done(20260826 20:45) 
  - [x] `show_img` serves the actual image file @done(20260814 22:48) 
  - [x] confirm separate annotations per imageset @done(20260908)


- [x] Docker @done(20260908)
  - [x] `http://localhost:8000/account/login/` loads with styling (no broken static files) @done(20260814 14:09)
  - [x] Visiting `/sortIT/` while logged out redirects to the login page @done(20260814 14:10)
  - [x] Sign up a new user → lands on the sign-up done page @done(20260908)
  - [x] New user can log in with the credentials just created @done(20260908)
  - [x] `/account/my_page/<id>/` shows the profile; edit + save works @done(20260908)
  - [x] Password change works and forces re-login @done(20260908)
  - [x] Logout returns to the login page @done(20260908)
  - [x] Admin: create a Project, add users, create a Label and an ImageSet, attach the label @done(20260908)
  - [x] Admin: project list shows labels; imageset list shows image count @done(20260908)
  - [x] As staff: upload a single image to an ImageSet → it appears in the set @done(20260908)
  - [x] Upload multiple images at once (multi-select) @done(20260908)
  - [x] Re-upload the same filename to another ImageSet → associated, NOT duplicated in DB or media @done(20260908)
  - [x] Uploading regenerates the montage (check `media/montage_<project_id>.jpg` timestamp) @done(20260908)
  - [x] Montage page shows the grid, thumbnails centered in their cells, no excess bottom whitespace @done(20260908)
  - [x] Sorting mode (ImageSet with 1 label): shows up to `nimgs` images, Keep/Discard works, progress advances @done(20260908)
  - [x] Sorting page: changing nimgs/imsize persists for the user (check next page + admin UserPreferences) @done(20260908)
  - [x] When all images are sorted → finish/thank-you page @done(20260908)
  - [x] Labeling mode (ImageSet with 2+ labels): pick a label per image, progress advances @done(20260908)
  - [x] ImageSet with 1 label, or 2 labels incl. one named "other" → redirects to sorting mode instead @done(20260908) 
  - [x] When all images are labeled → finish page @done(20260908)
  - [x] CSV export, project level (`/sortIT/project/<id>/download_csv`): header `Image_ID,imageset,filename,<user...>`, one row per (image, image set) @done(20260908)
  - [x] CSV export, imageset level (`/sortIT/imagesets/<id>/download_csv`) @done(20260908) 
  - [x] Admin: select 2+ projects → action "Export as CSV" → ZIP; each inner CSV has exactly ONE header row @done(20260908) 
  - [x] CLI export: `python manage.py export_csv --project <name>` (docker: `docker compose exec web python ...`) → `Image_ID,imageset,filename,<user...>` @done(20260908) 
  - [x] A label containing a comma survives CSV export un-corrupted (e.g. name a label `a, b`) @done(20260908) 
  - [x] Annotations from two users on the same image both appear as separate columns @done(20260908) 
  - [x] `show_img` serves the actual image file @done(20260908) 
