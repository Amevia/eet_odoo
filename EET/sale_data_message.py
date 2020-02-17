import uuid
from datetime import datetime
from lxml import etree
import pyt
import hashlib
from OpenSSL import crypto
from odoo import _
from odoo.exceptions import UserError
from base64 import b64encode, b64decode, b16encode
import re
import requests
import werkzeug
from string import Template
from requests.exceptions import ConnectionError

try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO


class SaleDataMessage:
    """
    The member functions of this class prepares values for sale data message items.

    There is a separate function for each message item.

    This class shall be imported in another modules for preparing sale data messages.
    """

    SALE_DATA_MESSAGE = None
    message_template = Template("""<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
        <SOAP-ENV:Header xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
            <wsse:Security
                xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
                xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"
                soap:mustUnderstand="1">
                <wsse:BinarySecurityToken
                    EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary"
                    ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"
                    wsu:Id="">
                </wsse:BinarySecurityToken>
                <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="">
                    <ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                        <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                            <ec:InclusiveNamespaces xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"
                                PrefixList="soap"/>
                        </ds:CanonicalizationMethod>
                        <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                        <ds:Reference URI="">
                            <ds:Transforms>
                                <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                    <ec:InclusiveNamespaces xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"
                                        PrefixList=""/>
                                </ds:Transform>
                            </ds:Transforms>
                            <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                            <ds:DigestValue></ds:DigestValue>
                        </ds:Reference>
                    </ds:SignedInfo>
                    <ds:SignatureValue></ds:SignatureValue>
                    <ds:KeyInfo Id="">
                        <wsse:SecurityTokenReference wsu:Id="">
                            <wsse:Reference URI=""
                                ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
                        </wsse:SecurityTokenReference>
                    </ds:KeyInfo>
                </ds:Signature>
            </wsse:Security>
        </SOAP-ENV:Header>
        <soap:Body xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"
            xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" wsu:Id=""/>
    </soap:Envelope>""")

    ns = {
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'SOAP-ENV': 'http://schemas.xmlsoap.org/soap/envelope/',
        'wsu': 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd',
        'wsse': 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd',
        'ds': 'http://www.w3.org/2000/09/xmldsig#',
        'ec': 'http://www.w3.org/2001/10/xml-exc-c14n#',
        'eet': 'http://fs.mfcr.cz/eet/schema/v3'
    }

    parser = etree.XMLParser(remove_blank_text=True, ns_clean=False)
    envelope = None
    cert_link_used = None
    cert_pwd_used = None

    def __init__(self, doc_obj, data_dict, environ='production', test_message=False, cert_path=None, cert_password=None):
        self.cert_link_used = None
        self.cert_pwd_used = None
        self.envelope = etree.XML(self.message_template.substitute(self.ns), parser=self.parser)
        self.prepare_sale_data_message(doc_obj, environ, data_dict, test_message=test_message,
            cert_path=cert_path, cert_password=cert_password)
        self.set_ID()
        self.attach_base64_encoded_x509_cert(doc_obj, environ, cert_path=cert_path, cert_password=cert_password)
        self.sign_sale_data_message(doc_obj, environ)
        self.set_sale_data_message()

    def set_tag_attribute(self, tag_name, attr_name, attr_value):
        self.envelope.find(tag_name, self.ns).set(attr_name, attr_value)

    def get_certificate(self, doc_obj, environ, cert_link, cert_pwd):
        param_obj = doc_obj.env['ir.config_parameter']
        if environ == 'playground':
            cert_link = param_obj.get_param('pkcs#12_playground_cert')
            cert_pwd = param_obj.get_param('pkcs#12_playground_cert_password')
        else:
            if not cert_link and not cert_pwd:
                cert_link = param_obj.get_param('pkcs#12_operational_cert')
                cert_pwd = param_obj.get_param('pkcs#12_operational_cert_password')
        if not cert_link:
            raise UserError(
                'Please configure a link to certificate under Settings/Technical/Parameters/System Parameters.')
        try:
            self.cert_link_used = cert_link
            self.cert_pwd_used = cert_pwd
            certificate = crypto.load_pkcs12(open(cert_link, 'rb').read(), cert_pwd)
        except (crypto.Error, IsADirectoryError) as e:
            error_message = _(
                'Please check link and password configuration of PKCS#12 certificate bundle.\n'
                'Error: %s') % (e)
            raise UserError(error_message)
        return certificate

    def set_uuid_zpravy(self):
        return str(uuid.UUID(bytes=datetime.now().strftime('%Y-%m-%d%H%M%S').encode(), version=4))

    def set_dat_odesl(self, doc_obj):
        current_time_obj = datetime.now(pytz.timezone(doc_obj.env.user.tz or 'UTC'))
        return current_time_obj.replace(microsecond=0).isoformat()

    def set_prvni_zaslani(self):
        # TODO: Improve when adding scheduler functionality
        first_attempt = '1'
        return first_attempt

    def set_overeni(self, header, environ, test_message=False):
        if test_message and environ == 'production':
            header.set('overeni', '1')

    def calculate_pkp(self, data, environ, doc_obj, cert_path=None, cert_password=None):
        dic_popl = data.attrib['dic_popl']
        id_provoz = data.attrib['id_provoz']
        id_pokl = data.attrib['id_pokl']
        porad_cis = data.attrib['porad_cis']
        dat_trzby = data.attrib['dat_trzby']
        celk_trzba = data.attrib['celk_trzba']
        plaintext = dic_popl + '|' + id_provoz + '|' + id_pokl + '|' + porad_cis \
            + '|' + dat_trzby + '|' + celk_trzba
        certificate = self.get_certificate(doc_obj, environ, cert_path, cert_password)
        pkey = certificate.get_privatekey()
        pkp_code = b64encode(crypto.sign(pkey, plaintext, 'sha256'))
        return pkp_code

    def calculate_bkp(self, pkp_value):
        decoded_string = b64decode(pkp_value)
        digest = hashlib.sha1(decoded_string).digest()
        base16_string = b16encode(digest)
        bkp_code = '-'.join(re.findall(r'.{8}', base16_string.decode()))
        return bkp_code

    def prepare_sale_data_message(self, doc_obj, environ, data_dict, test_message=False, cert_path=None, cert_password=None):
        trzba = etree.Element('Trzba', nsmap={None: 'http://fs.mfcr.cz/eet/schema/v3'})
        header = etree.Element(
            'Hlavicka',
            dat_odesl=self.set_dat_odesl(doc_obj),
            prvni_zaslani=self.set_prvni_zaslani(),
            uuid_zpravy=self.set_uuid_zpravy()
        )
        self.set_overeni(header, environ, test_message=test_message)
        trzba.append(header)

        data = etree.Element(
            'Data',
            celk_trzba=data_dict['celk_trzba'],
            dat_trzby=data_dict['dat_trzby'],
            dic_popl=data_dict['dic_popl'],
            id_pokl=data_dict['id_pokl'],
            id_provoz=data_dict['id_provoz'],
            porad_cis=data_dict['porad_cis'],
            zakl_dan1=data_dict.get('zakl_dan1', '0.00'),
            dan1=data_dict.get('dan1', '0.00'),
            zakl_dan2=data_dict.get('zakl_dan2', '0.00'),
            dan2=data_dict.get('dan2', '0.00'),
            zakl_dan3=data_dict.get('zakl_dan3', '0.00'),
            dan3=data_dict.get('dan3', '0.00'),
            cest_sluz=data_dict.get('cest_sluz', '0.00'),
            pouzit_zboz1=data_dict.get('pouzit_zboz1', '0.00'),
            pouzit_zboz2=data_dict.get('pouzit_zboz2', '0.00'),
            pouzit_zboz3=data_dict.get('pouzit_zboz3', '0.00'),
            urceno_cerp_zuct=data_dict.get('urceno_cerp_zuct', '0.00'),
            cerp_zuct=data_dict.get('cerp_zuct', '0.00'),
            rezim=data_dict['rezim']
        )
        if data_dict.get('dic_poverujiciho', False):
            data.set('dic_poverujiciho', data_dict['dic_poverujiciho'])
        trzba.append(data)

        codes = etree.Element('KontrolniKody')

        pkp_subelement = etree.SubElement(
            codes,
            'pkp',
            cipher='RSA2048',
            digest='SHA256',
            encoding='base64'
        )
        pkp_subelement.text = self.calculate_pkp(data, environ, doc_obj,
            cert_path=cert_path, cert_password=cert_password)

        bkp_subelement = etree.SubElement(
            codes,
            'bkp',
            digest='SHA1',
            encoding='base16'
        )
        bkp_subelement.text = self.calculate_bkp(pkp_subelement.text).lower()

        trzba.append(codes)
        self.envelope.find('soap:Body', self.ns).append(trzba)

    def set_ID(self):
        common_id = uuid.uuid4().hex
        self.set_tag_attribute('SOAP-ENV:Header/wsse:Security/wsse:BinarySecurityToken',
                               '{' + '{0}'.format(self.ns.get('wsu')) + '}Id',
                               'X509-{0}'.format(common_id))
        self.set_tag_attribute(
            'SOAP-ENV:Header/wsse:Security/ds:Signature/ds:SignedInfo/ds:Reference',
            'URI', '#id-{0}'.format(common_id))
        self.set_tag_attribute(
            'SOAP-ENV:Header/wsse:Security/ds:Signature/ds:KeyInfo/wsse:SecurityTokenReference/wsse:Reference',
            'URI', '#X509-{0}'.format(common_id))
        self.set_tag_attribute('soap:Body', '{' + '{0}'.format(self.ns.get('wsu')) + '}Id',
                               'id-{0}'.format(common_id))
        self.set_tag_attribute('SOAP-ENV:Header/wsse:Security/ds:Signature', 'Id',
                               'SIG-{0}'.format(common_id))
        self.set_tag_attribute('SOAP-ENV:Header/wsse:Security/ds:Signature/ds:KeyInfo', 'Id',
                               'KI-{0}'.format(common_id))
        self.set_tag_attribute(
            'SOAP-ENV:Header/wsse:Security/ds:Signature/ds:KeyInfo/wsse:SecurityTokenReference',
            '{' + '{0}'.format(self.ns.get('wsu')) + '}Id', 'STR-{0}'.format(common_id))

    def attach_base64_encoded_x509_cert(self, doc_obj, environ, cert_path=None, cert_password=None):
        certificate = self.get_certificate(doc_obj, environ, cert_path, cert_password)
        encoded_cert = b64encode(crypto.dump_certificate(crypto.FILETYPE_ASN1,
                                                         certificate.get_certificate()))
        token_tag_obj = self.envelope.find(
            'SOAP-ENV:Header/wsse:Security/wsse:BinarySecurityToken',
            self.ns)
        token_tag_obj.text = encoded_cert

    def get_normalized_subtree(self, node, includive_prefixes=[]):
        tree = etree.ElementTree(node)
        ss = StringIO()
        tree.write_c14n(
            ss, exclusive=True, inclusive_ns_prefixes=includive_prefixes)
        return ss.getvalue()

    def sign_sale_data_message(self, doc_obj, environ, cert_path=None, cert_password=None):
        e_sale_obj = self.envelope.find('soap:Body', self.ns)
        e_sale = self.get_normalized_subtree(e_sale_obj, ['soap'])
        digest = b64encode(hashlib.sha256(e_sale).digest())
        digest_val_tag = self.envelope.find(
            'SOAP-ENV:Header/wsse:Security/ds:Signature/ds:SignedInfo/ds:Reference/ds:DigestValue',
            self.ns)
        digest_val_tag.text = digest
        certificate = self.get_certificate(doc_obj, environ, cert_path, cert_password)
        pkey = certificate.get_privatekey()
        sign_info_obj = self.envelope.find(
            'SOAP-ENV:Header/wsse:Security/ds:Signature/ds:SignedInfo', self.ns)
        sign_info = self.get_normalized_subtree(sign_info_obj, ['soap'])
        signed_message = b64encode(crypto.sign(pkey, sign_info, 'sha256'))
        sign_value_tag = self.envelope.find(
            'SOAP-ENV:Header/wsse:Security/ds:Signature/ds:SignatureValue', self.ns)
        sign_value_tag.text = signed_message

    def set_sale_data_message(self):
        self.SALE_DATA_MESSAGE = etree.tostring(self.envelope)

    def send_request(self, document, test_message=False, url=None):
        if not url:
            url = 'https://prod.eet.cz/eet/services/EETServiceSOAP/v3'
        data = self.SALE_DATA_MESSAGE
        try:
            r = requests.post(url, data)
            response = werkzeug.utils.unescape(r.content.decode())
            self.register_sale_data_message(document, test_message=test_message, response=response)
        except ConnectionError as e:
            self.register_sale_data_message(document, test_message=test_message, exception=str(e), exception_class=str(e.__class__))

    def register_sale_data_message(self, doc_obj, test_message=False, **kwargs):
        try:
            company_id = doc_obj.company_id.id
        except AttributeError:
            company_id = doc_obj.env.user.company_id.id
        vals = {
            'res_id': doc_obj.id,
            'company_id': company_id,
            'res_model': doc_obj.__class__.id.model_name,
            'name': doc_obj.__class__.id.model_name + ',' + str(doc_obj.id),
            'cert_link': self.cert_link_used,
            'cert_pwd': self.cert_pwd_used,
            'message': self.SALE_DATA_MESSAGE,
            'test_message': test_message
        }
        if kwargs.get('response'):
            vals['response'] = kwargs['response']
        else:
            if kwargs.get('exception_class'):
                # If exception_class exists, then presence of exception key is obvious
                vals['exception'] = kwargs['exception']
        doc_obj.env['revenue.data.message'].create(vals)
