from django.urls import path

from sortIT.views import (
    choose_img_set,
    choose_proj,
    download_imageset_csv,
    download_project_csv,
    finish,
    image_upload,
    label,
    label_post,
    show_image,
    show_montage,
    sort,
    sort_post,
    toggle_darkmode,
)

app_name = "sortIT"
urlpatterns = [
    path("", choose_proj, name="choose_proj"),
    path(
        "project/<int:project_id>/download_csv",
        download_project_csv,
        name="down_proj_csv",
    ),
    path(
        "project/<int:project_id>",
        choose_img_set,
        name="choose_img_set",
    ),
    path(
        "imagesets/<int:imageset_id>/download_csv",
        download_imageset_csv,
        name="down_imset_csv",
    ),
    path("upload/<int:imageset_id>", image_upload, name="upload"),
    path("show_img/<int:image_id>", show_image, name="show_img"),
    path("show_montage/<int:project_id>", show_montage, name="show_montage"),
    path("label/<int:imageset_id>", label, name="label"),
    path("label_post", label_post, name="label_post"),
    path("sort/<int:imageset_id>", sort, name="sort"),
    path("sort_post", sort_post, name="sort_post"),
    path("toggle_darkmode", toggle_darkmode, name="toggle_darkmode"),
    path("finish", finish, name="finish"),
]
