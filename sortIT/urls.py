from django.urls import path

from . import views


app_name = "sortIT"
urlpatterns = [
    path("", views.choose_proj, name="choose_proj"),
    path("project/<int:project_id>/", views.choose_img_set, name="choose_img_set"),
    path("upload_imgs/<int:imageset_id>/", views.image_upload, name="img_upload"),
    path("show_img/<int:image_id>", views.show_image, name="show_img"),
    path("labeling/<int:imageset_id>", views.labeling, name="labeling"),
    path("label_post/", views.label_post, name="label_post"),
    path("sortone/<int:imageset_id>", views.sortone, name="sortone"),
    path("sort_post", views.sort_post, name="sort_post"),
    path("finish/", views.finish, name="finish"),
    path("download", views.download, name="download"),
]
