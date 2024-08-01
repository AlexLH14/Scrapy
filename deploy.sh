#!/bin/bash

echo "Descargando proyecto"
echo "Construyendo build para lanzar migraciones"
docker-compose build crawler-pinpass
docker-compose run --rm --entrypoint="python3 manage.py migrate" crawler-pinpass
echo "Iniciando aplicación con nueva versión de código"
docker-compose up -d --force-recreate