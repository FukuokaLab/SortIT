# SortIT
Easy image labeling tool by multiple user.

## Backgound
SortIT is a web application that allows multiple users to label the same image set. Dr. Wataru Uegami, a pathologist, developed this application to facilitate research using machine learning models, with the main target being the classification of pathological image patches. Pathological images are known to have low inter-observer agreement in diagnosis. This application can be used to analyze the variation in judgment or to obtain data that can serve as a gold standard.


## How to build?
1. Install docker
2. Place `.env` files as follow
3. Place `/container/nginx/conf.d/default.conf`
4. `docker compose -f docker-compose.prod.yml build` (build)
5. `docker compose -f docker-compose.prod.yml up -d` (run server as daemon) 
6. `docker compose exec app python manage.py createsuperuser --noinput` (DJANGO_SUPERUSER_xxxx are used for set up)

## Env files
example of .env
```
SQL_ENGINE=django.db.backends.postgresql
POSTGRES_NAME=postgres
POSTGRES_DB=sortimg
POSTGRES_USER=postgres
#POSTGRES_PASSWORD=pass_for_db
POSTGRES_PASSWORD=pass_for_db
SQL_HOST=db
SQL_PORT=5432
SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1
DEBUG=True
SERVER_NAME=my_host_name.com

DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@gmail.com
DJANGO_SUPERUSER_PASSWORD=admin_pass
```


example of .env.prod
```
SQL_ENGINE=django.db.backends.postgresql
POSTGRES_NAME=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=pass_for_db
POSTGRES_DB=sortimg-prod
SQL_HOST=db
SQL_PORT=5432
SECRET_KEY=xxxxxxxxxxxxx_set_your_key_xxxxxxxxxxxxxxxxxx
DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1]
DEBUG=False

SERVER_NAME=my_host_name.com

DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@gmail.com
DJANGO_SUPERUSER_PASSWORD=admin_pass
```

## Example of default conf
``` 
upstream django {
    server app:8000;
}

server {
    listen 80;
    server_name 0.0.0.0;

    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_redirect off;
    }
    
    location /static/ {
		alias /static/;
	}

    location /media/ {
		alias /media/;
	}
}
```

## LICENCE
MIT
