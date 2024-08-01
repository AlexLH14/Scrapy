#include <stdio.h>
#include <stdlib.h>
#include <curl/curl.h>
#include <stdio.h>
#include <string.h>

static CURLcode sslctx_function(CURL *curl, void *sslctx, void *parm)
{
	fprintf(stderr, "Signing");
	return CURLE_OK;
}

// Función para agregar un encabezado a la lista de encabezados
struct curl_slist* addHeader(struct curl_slist *headers, const char *name, const char *value) {
    char header[1024]; // Ajusta el tamaño según tus necesidades
    snprintf(header, sizeof(header), "%s: %s", name, value);
    return curl_slist_append(headers, header);
}

int main(int argc, char *argv[])
{
  CURL *curl;
  CURLcode res;
  FILE *headerfile;

  const char *pCertName;
  const char *pKeyName;
  const char *pKeyType;
  const char *pCertType;
  const char *pEngine;
  const char *pPassphrase;

#define USE_ENGINE 1

#ifdef USE_ENGINE
  pKeyName  = "pkcs11:id=Private%20Key;type=private";
  pCertName = "pkcs11:id=Certificate;type=cert";
  pPassphrase = NULL;
  pKeyType  = "ENG";
  pCertType  = "ENG";
  //pEngine   = "chil";            /* for nChiper HSM... */
  pEngine   = "pkcs11";
#else
  pKeyName  = "certs/key.pem";
  pCertName = "certs/cert.pem";
  pPassphrase = NULL;
  pKeyType  = "PEM";
  pCertType  = "PEM";
  pEngine   = NULL;
#endif

  curl_global_init(CURL_GLOBAL_DEFAULT);

  int i;
  /*for (i = 0; i < argc; i++)
  {
	  printf("Arg %d: %s\n\n\n\n\n\n", i, argv[i]);
  }*/
  setenv("DOCUMENT", argv[1], 1);

  if(argv[6] != NULL && argv[6][0] != '\0') {
    setenv("CIF", argv[6], 1);
  }
  
  // "SOUP" o "CURL"
  setenv("HTTP_CLIENT", "SOUP", 1);

  // Entorno Desarrollo Logalty
  //setenv("DOMAIN", "https://desarrollo.logalty.com/idhub", 1);

  // Entorno Demo Logalty
  //setenv("DOMAIN", "https://demo.logalty.com/idhub", 1);

  // Entorno Produccion Logalty
  setenv("DOMAIN", "https://services.logalty.com/idhub", 1);
  setenv("OAUTH2_SERVER", "https://api.logalty.com", 1);
  //setenv("CLIENT_ID", "AK46RDTjj", 1);
  setenv("CLIENT_ID", "4iqlbokgh0jj42b73t967fadaq", 1);
  setenv("SECRET", "dq0phccom4b966u1mrvossm2drke6p43fs4nrgt62q206p6jchn", 1);

  char *method = argv[2];
  char *url = argv[3];
  char *login_data = argv[4];

  curl = curl_easy_init();
  if(curl) {
    curl_easy_setopt(curl, CURLOPT_URL, url);

    // Crear y configurar los encabezados personalizados
    struct curl_slist *headers = NULL;
    headers = addHeader(headers, "Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9");
    headers = addHeader(headers, "Connection", "keep-alive");
    headers = addHeader(headers, "Content-Type", "application/x-www-form-urlencoded");
    headers = addHeader(headers, "User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.55");
    headers = addHeader(headers, "Sec-Fetch-Dest", "empty");
    headers = addHeader(headers, "Sec-Fetch-Mode", "cors");
    headers = addHeader(headers, "Sec-Fetch-Site", "same-origin");
    headers = addHeader(headers, "X-Requested-With", "XMLHttpRequest");

    if (argv[5] != NULL) {
        headers = addHeader(headers, "Zk-sid", argv[5]);
    }

    char filepath_dni[256];
    sprintf(filepath_dni, "/app/cirbe_%s.txt", argv[1]);
    FILE *fp = fopen(filepath_dni, "ab+");

    curl_easy_setopt(curl, CURLOPT_COOKIEJAR, filepath_dni);  // Guardar cookies al finalizar si es necesario
    curl_easy_setopt(curl, CURLOPT_COOKIEFILE, filepath_dni); // Habilita las cookies en memoria

    // Habilitar el seguimiento de redirecciones
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);

    if(strcmp(method, "GET") == 0) {
        //GET
        curl_easy_setopt(curl, CURLOPT_HEADERDATA, headerfile);
    } else if(strcmp(method, "POST") == 0) {
        //POST
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, login_data);
        curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, (long)strlen(login_data));
    }

    if(pEngine) {
      struct curl_slist *engines = NULL;
      curl_easy_getinfo(curl, CURLINFO_SSL_ENGINES, &engines);
      for(;engines;engines=engines->next) {
              fprintf(stderr, "engine cargado: %s\n", engines->data);
      }
	    curl_slist_free_all(engines);

      /* use crypto engine */
      int res = curl_easy_setopt(curl, CURLOPT_SSLENGINE, pEngine);
      if(res != CURLE_OK) {
        /* load the crypto engine */
	      const char *str=curl_easy_strerror(res);
        fprintf(stderr, "cannot set crypto engine %d - %s\n", res, str);
        return -1;
      }

      if(curl_easy_setopt(curl, CURLOPT_SSLENGINE_DEFAULT, 1L) != CURLE_OK) {
        /* set the crypto engine as default */
        /* only needed for the first time you load
           a engine in a curl object... */
        fprintf(stderr, "cannot set crypto engine as default\n");
        return -1;
      }
    }

    /* cert is stored PEM coded in file... */
    /* since PEM is default, we needn't set it for PEM */
    curl_easy_setopt(curl, CURLOPT_SSLCERTTYPE, pCertType);

    /* set the cert for client authentication */
    curl_easy_setopt(curl, CURLOPT_SSLCERT, pCertName);

    /* sorry, for engine we must set the passphrase
       (if the key has one...) */
    if(pPassphrase)
      curl_easy_setopt(curl, CURLOPT_KEYPASSWD, pPassphrase);

    /* if we use a key stored in a crypto engine,
       we must set the key type to "ENG" */
    curl_easy_setopt(curl, CURLOPT_SSLKEYTYPE, pKeyType);

    /* set the private key (file or ID in engine) */
    curl_easy_setopt(curl, CURLOPT_SSLKEY, pKeyName);

    /* disconnect if we cannot validate server's cert */
    //curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 1L);

    curl_easy_setopt(curl, CURLOPT_SSL_CTX_FUNCTION, *sslctx_function);

    /* Perform the request, res will get the return code */
    res = curl_easy_perform(curl);
    /* Check for errors */
    if(res != CURLE_OK)
      fprintf(stderr, "curl_easy_perform() failed: %s\n",
              curl_easy_strerror(res));

    /* always cleanup */
    curl_easy_cleanup(curl);
    fclose(fp);
  } else {
    fprintf(stderr, "cURL no inicializado");
  }

  curl_global_cleanup();
  
  return 0;
}
