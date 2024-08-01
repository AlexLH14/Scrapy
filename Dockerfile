#FROM debian:latest
FROM python:3.8

# Evita que los prompts de apt interfieran con la automatización
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update -y && apt-get install -y \
    gnutls-bin \
    libcurl4-openssl-dev \
    libengine-pkcs11-openssl \
    libglib2.0 \
    curl \
    gcc \
    swig \
    libsoup-3.0 \
    nano \
    opensc

RUN apt-get install -y python3-pip
RUN pip install selenium

# Copiar solo el archivo de requerimientos primero
COPY requirements/requirements.txt /app/requirements/requirements.txt

WORKDIR /app

# Instalar las dependencias solo si requirements.txt ha cambiado
RUN pip install -r requirements/requirements.txt

# Copiar el resto de los archivos de la aplicación
COPY . /app
COPY .env.pinpass /app/cirbox/settings/

RUN mkdir -p /opt/logalty
RUN mkdir -p /app/static/flags/cirbe

COPY logalty-pkcs11.so /opt/logalty/
COPY simple.c /opt/logalty/
COPY simple_renta.c /opt/logalty/
COPY simple_cirbe.c /opt/logalty/
COPY simple_lgt.c /opt/logalty/

RUN echo "module: /opt/logalty/logalty-pkcs11.so" > /usr/share/p11-kit/modules/p11-logalty.module

# Modifica el archivo /etc/ssl/openssl.cnf
RUN sed -i '/\[openssl_init\]/a engines = engine_section\n[engine_section]\npkcs11 = pkcs11_section\n[pkcs11_section]\ndynamic_path = /usr/lib/x86_64-linux-gnu/engines-3/libpkcs11.so' /etc/ssl/openssl.cnf

# Copia la configuración de OpenSC y crea un enlace simbólico si es necesario
RUN mkdir -p /etc/ssl/engines
RUN ln -s /usr/lib/x86_64-linux-gnu/engines-1.1/pkcs11.so /etc/ssl/engines/libpkcs11.so

WORKDIR /opt/logalty

RUN gcc -L/usr/lib/x86_64-linux-gnu simple.c -o simple -lcurl
RUN gcc -L/usr/lib/x86_64-linux-gnu simple_renta.c -o simplerenta -lcurl
RUN gcc -L/usr/lib/x86_64-linux-gnu simple_cirbe.c -o simplecirbe -lcurl
RUN gcc -L/usr/lib/x86_64-linux-gnu simple_lgt.c -o simplelgt -lcurl

WORKDIR /app
