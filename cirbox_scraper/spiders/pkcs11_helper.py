import subprocess
from urllib.parse import urlencode


def request_by_pkcs11(url, dni, method, body, authorization, simplec='', decode=True, nif=None):
    # command = f'/opt/logalty/simple {dni} {method} "{url}" "{body}" "{authorization}" 2>&1'
    # command = f'/opt/logalty/simple {dni} {method} "{url}" "{body}" "{authorization}"'

    if body:
        body = urlencode(body)
    else:
        body = 'None'

    if authorization is not None:
        command = f'/opt/logalty/simple{simplec} {dni} {method} "{url}" "{body}" "{authorization}" {nif}'
    else:
        command = f'/opt/logalty/simple{simplec} {dni} {method} "{url}" "{body}" "" {nif}'

    print(command)
    proceso = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    salida, error = proceso.communicate()
    if proceso.returncode == 0:
        if decode:
            salida = salida.decode()
        # f = open('/app/fichero.txt', 'w')
        # f.write(salida)
        # f.close()
        return salida
    else:
        print(error)
        raise Exception(error)
