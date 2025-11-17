from django.urls import path

from sortIT.views import finish, images, imageset_list, label, project_list, sort


app_name = "sortIT"
urlpatterns = [
    path("", project_list.choose_proj, name="choose_proj"),
    path(
        "project/<int:project_id>/download_csv",
        project_list.download_csv,
        name="down_proj_csv",
    ),
    path(
        "project/<int:project_id>", imageset_list.choose_img_set, name="choose_img_set"
    ),
    path(
        "imagesets/<int:imageset_id>/download_csv",
        imageset_list.download_csv,
        name="down_imset_csv",
    ),
    path("upload_imgs/<int:imageset_id>", images.image_upload, name="img_upload"),
    path("show_img/<int:image_id>", images.show_image, name="show_img"),
    path("show_montage/<int:project_id>", images.show_montage, name="show_montage"),
    path("label/<int:imageset_id>", label.label, name="label"),
    path("label_post", label.label_post, name="label_post"),
    path("sort/<int:imageset_id>", sort.sort, name="sort"),
    path("sort_post", sort.sort_post, name="sort_post"),
    path("finish", finish.finish, name="finish"),
]
