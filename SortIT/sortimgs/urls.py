from django.urls import path

from . import views


app_name = 'sortimgs'
urlpatterns = [
    path("upload_imgs/<int:image_set_id>/", views.image_upload, name='img_upload'),

    path("", views.choose_img_set, name='choose_img_set'),
    path("labeling/", views.choose_img_set, name='choose_img_set'),

    path("show_img/<int:image_id>", views.show_image, name='show_img'),
    path("labeling/<int:image_set_id>", views.labeling, name='labeling'),
    path("label_post/", views.label_post, name='label_post'),

    path('sortone/<int:image_set_id>', views.sortone, name='sortone'),
    path('sort_post', views.sort_post, name='sort_post'),

    path("finish/", views.finish, name='finish'),
    path('download', views.download, name='download'),

]
