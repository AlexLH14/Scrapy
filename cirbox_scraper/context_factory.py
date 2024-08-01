from OpenSSL import crypto, SSL, SSL
from cirbox_scraper.spiders.vida_laboral_osw import SpiderVidaLaboral
from scrapy.core.downloader.contextfactory import ScrapyClientContextFactory
from twisted.web.iweb import IPolicyForHTTPS
from zope.interface.declarations import implementer
from twisted.internet.ssl import PrivateCertificate, KeyPair
from twisted.internet.ssl import optionsForClientTLS, platformTrust
from twisted.internet.ssl import CertificateOptions
from cryptography.hazmat.primitives.serialization import load_pem_private_key

"""
    ESTA CLASE NO SE UTILIZA EN NINGÚN SITIO, PROBABLEMENTE ESTÁ A MEDIO HACER
"""


@implementer(IPolicyForHTTPS)
class SegSocialGobEsContextFactory(ScrapyClientContextFactory):
    def __init__(self, *args, **kwargs):
        # Use SSLv23_METHOD so we can use protocol negotiation
        super().__init__(*args, **kwargs)
        # self.ssl_method = SSL.SSLv23_METHOD

    # def getCertificateOptions(self):
    #     return CertificateOptions(
    #         verify=False,
    #         method=getattr(self, 'method', getattr(self, '_ssl_method', None)),
    #         fixBrokenPeers=True,
    #         acceptableCiphers=self.tls_ciphers,
    #     )

    def creatorForNetloc(self, hostname, port):
        crawling_cert = None
        with open(
            'cirbox_scraper/certificates/'\
                f'{SpiderVidaLaboral.custom_settings["REQUEST_ID"].value}/'\
                f'{SpiderVidaLaboral.custom_settings["REQUEST_ID"].value}.pem',
            'rb'
        ) as cert_pem_file, open(
            'cirbox_scraper/certificates/'\
                f'{SpiderVidaLaboral.custom_settings["REQUEST_ID"].value}/'\
                f'{SpiderVidaLaboral.custom_settings["REQUEST_ID"].value}.key',
            'rb'
        ) as key_pem_file:
            key = KeyPair.load(key_pem_file.read(), crypto.FILETYPE_PEM)
            crawling_cert = PrivateCertificate.load(
                cert_pem_file.read(),
                privateKey=key,
                format=crypto.FILETYPE_PEM
            )
        # return crawling_cert.options()
        return optionsForClientTLS(
            hostname.decode("ascii"),
            trustRoot=platformTrust(),
            clientCertificate=crawling_cert,
            extraCertificateOptions={'method': self._ssl_method,}
        )
