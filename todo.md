* [x] add user settings DB @done(11/14/25 21:17)
* [x] write README @done(11/18/25 00:51)
* [x] add guide about deploying production server @done(20260604 23:41)
* [x] documentation @done(20260604 23:41)
* [ ] update labeling page (multi-label sorting)
* [ ] imageset with multiple classes, but make it possible to select one label, then binary filter it
* [ ] all negative (filtered out) tiles will be sent to "labeling" for class labeling
* [ ] handle annotation conflicts (overwriting image labels)
* [ ] when deleting images on the admin page, also delete the file in media/
- [ ] make port configurable in docker

## Manual feature verification checklist

Run each check twice — once on the local install, once on Docker — and tick the matching box.

### Local install (one-time setup)

```bash
uv sync                    # or: pip install -r requirements.txt
cp .env.example .env       # edit .env and set SECRET_KEY to a random value
mkdir -p data              # required for the log file (data/sortit.log)
source .venv/bin/activate
python manage.py makemigrations
python manage.py migrate
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

| # | Check | Local | Docker |
|---|-------|:-----:|:------:|
| 1 | `http://localhost:8000/account/login/` loads with styling (no broken static files) | [ ] | [ ] |
| 2 | Visiting `/sortIT/` while logged out redirects to the login page | [ ] | [ ] |
| 3 | Sign up a new user → lands on the sign-up done page | [ ] | [ ] |
| 4 | New user can log in with the credentials just created | [ ] | [ ] |
| 5 | `/account/my_page/<id>/` shows the profile; edit + save works | [ ] | [ ] |
| 6 | Password change works and forces re-login | [ ] | [ ] |
| 7 | Logout returns to the login page | [ ] | [ ] |
| 8 | Admin: create a Project, add users, create a Label and an ImageSet, attach the label | [ ] | [ ] |
| 9 | Admin: project list shows labels; imageset list shows image count | [ ] | [ ] |
| 10 | As staff: upload a single image to an ImageSet → it appears in the set | [ ] | [ ] |
| 11 | Upload multiple images at once (multi-select) | [ ] | [ ] |
| 12 | Re-upload the same filename to another ImageSet → associated, NOT duplicated in DB or media | [ ] | [ ] |
| 13 | Uploading regenerates the montage (check `media/montage_<project_id>.jpg` timestamp) | [ ] | [ ] |
| 14 | Montage page shows the grid, thumbnails centered in their cells, no excess bottom whitespace | [ ] | [ ] |
| 15 | Sorting mode (ImageSet with 1 label): shows up to `nimgs` images, Keep/Discard works, progress advances | [ ] | [ ] |
| 16 | Sorting page: changing nimgs/imsize persists for the user (check next page + admin UserPreferences) | [ ] | [ ] |
| 17 | When all images are sorted → finish/thank-you page | [ ] | [ ] |
| 18 | Labeling mode (ImageSet with 2+ labels): pick a label per image, progress advances | [ ] | [ ] |
| 19 | ImageSet with 1 label, or 2 labels incl. one named "other" → redirects to sorting mode instead | [ ] | [ ] |
| 20 | When all images are labeled → finish page | [ ] | [ ] |
| 21 | CSV export, project level (`/sortIT/project/<id>/download_csv`): header `Image_ID,Image,<user...>`, one row per image | [ ] | [ ] |
| 22 | CSV export, imageset level (`/sortIT/imagesets/<id>/download_csv`) | [ ] | [ ] |
| 23 | Admin: select 2+ projects → action "Export as CSV" → ZIP; each inner CSV has exactly ONE header row | [ ] | [ ] |
| 24 | CLI export: `python manage.py export_csv --project <name>` (docker: `docker compose exec web python ...`) → `Image_ID,filepath,<user...>` | [ ] | [ ] |
| 25 | A label containing a comma survives CSV export un-corrupted (e.g. name a label `a, b`) | [ ] | [ ] |
| 26 | Annotations from two users on the same image both appear as separate columns | [ ] | [ ] |
| 27 | `show_img` serves the actual image file | [ ] | [ ] |
