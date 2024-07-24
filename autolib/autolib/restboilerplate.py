from enum import Enum, unique
import re
import requests
from textwrap import dedent
from autolib.coreexception import CoreException


@unique
class RequestType(Enum):
    GET = 'get'
    DELETE = 'delete'
    POST = 'post'
    PATCH = 'patch'
    PUT = 'put'


class RestBoilerPlate(type):
    """\
    This metaclass is used to create wrapper classes for HTTP based Rest APIs.

    @DUNC Full documentation for use.
    """

    def __new__(mcs, name, bases, namespace, **kwargs):

        def make_init():
            def init(self, base_url, http_session=None):
                """\
                Set the base URL used by generated properties and methods.
                """
                self._property_base_url = base_url
                self._base_url = base_url
                if http_session is None:
                    self._default_session = kwargs.get("http_session", requests.Session())
                    self._http_session = kwargs.get("http_session", requests.Session())
                else:
                    self._default_session = http_session
                    self._http_session = http_session
            return init

        def make_set_session():
            def _set_session(self, session_object):
                """\
                Replace the current http requests Session object with an alternative one or Mock.
                """
                self._http_session = session_object
            return _set_session

        def make_default_session():
            def _default_session(self, session_object):
                """\
                Return the default http requests Session object (useful to pass to a mock instance to partially mock).
                """
                return self._default_session
            return _default_session

        def make_reset_session():
            def _reset_session(self):
                """\
                Restore the http requests Session object to the original one defined at class instantiation time.
                """
                self._http_session = self._default_session
            return _reset_session

        def make_property_getter(url):
            def getter(self):
                request_url = f'{self._property_base_url.rstrip("/")}/{url}'
                response = None
                try:
                    response = self._http_session.get(request_url)
                    if response.status_code == 200:
                        return response.json()
                    else:
                        raise CoreException(dict(message=f"GET Request to {self._property_base_url.rstrip('/')}/{url} produced status code: {response.status_code} - {response.json().get('message', None)}", url=request_url, response=response))
                except requests.exceptions.RequestException as exc:
                    raise CoreException(dict(message=str(exc), exception=exc, url=request_url, response=response))

            return getter

        def make_property_setter(request_method, url):
            def property_setter(self, data_dict):
                request_url = f'{self._property_base_url.rstrip("/")}/{url}'
                request_callable = None
                response = None

                if request_method is RequestType.POST:
                    request_callable = self._http_session.post
                elif request_method is RequestType.PATCH:
                    request_callable = self._http_session.patch
                elif request_method is RequestType.PUT:
                    request_callable = self._http_session.put

                try:
                    response = request_callable(request_url, headers={'Content-Type': 'application/json'}, json=data_dict)
                except requests.exceptions.RequestException as exc:
                    raise CoreException(dict(message=str(exc), exception=exc, url=request_url, response=response))

                expected_status = [200, 201]

                if response.status_code not in expected_status:
                    raise CoreException(dict(message=f"{request_method.name} Request to {self._property_base_url.rstrip('/')}/{url} produced status code: {response.status_code} - {response.json().get('message', None)}", url=request_url, response=response))
            return property_setter

        # Create the property wrappers
        for k, v in kwargs.get("url_properties", {}).items():
            getter_name = v.get("GET", None)
            patch_setter_name = v.get("PATCH", None)
            put_setter_name = v.get("PUT", None)
            post_setter_name = v.get("POST", None)
            doc_string = v.get("DOC", None)

            if not doc_string:
                raise CoreException(dict(message="Every generated property requires a DOC entry containing it's docstring."))

            # Use a set to determine whether any more than a single POST, PUT or PATCH is in use
            if len({put_setter_name, post_setter_name, patch_setter_name}) > 2:
                raise CoreException(dict(message="Error: Only define PUT, POST or PATCH setters for a property"))

            setter = None
            if patch_setter_name:
                setter = make_property_setter(RequestType.PATCH, patch_setter_name)
            elif put_setter_name:
                setter = make_property_setter(RequestType.PUT, put_setter_name)
            elif post_setter_name:
                setter = make_property_setter(RequestType.POST, post_setter_name)

            namespace[k] = property(fget=make_property_getter(getter_name) if getter_name else None,
                                    fset=setter,
                                    fdel=None,
                                    doc=doc_string)

        def _make_getter_method(method_config):

            # @DUNC We need a way to also allow query strings to be defined and used!

            format_string, inner_doc_string = method_config
            matches = [x[1] for x in re.findall(r'({(?P<name>\w+)})', format_string)]
            func_body = dedent(f'''
            def _getter(self, {",".join(matches) if matches else ""}): 
                """\\
                {inner_doc_string}
                """ 
                request_url = self._base_url.rstrip("/") + '/' + f'{format_string}'
                response = None

                try:
                    response = self._http_session.get(request_url)
                except requests.exceptions.RequestException as exc:
                    raise CoreException(dict(message=str(exc), exception=exc, url=request_url, response=response))

                if response.status_code == 200:
                    return response.json()
                else:
                    raise CoreException(dict(
                        message='Could not get specified resource: ' + str(response.status_code) + ': ' + response.json().get("message", "No message"),
                            url=request_url, response=response))
            ''')
            local_dict = locals().copy()
            exec(func_body, globals(), local_dict)
            return local_dict['_getter']

        def _make_deller_method(method_config):

            # @DUNC We need a way to also allow query strings to be defined and used!

            format_string, inner_doc_string = method_config
            matches = [x[1] for x in re.findall(r'({(?P<name>\w+)})', format_string)]
            func_body = dedent(f'''
            def _deller(self, {",".join(matches) if matches else ""}): 
                """\\
                {inner_doc_string}
                """ 
                request_url = self._base_url.rstrip("/") + '/' + f'{format_string}'
                response = None

                try:
                    response = self._http_session.delete(request_url)
                except requests.exceptions.RequestException as exc:
                    raise CoreException(dict(message=str(exc), exception=exc, url=request_url, response=response))

                if response.status_code == 200:
                    return response.json()
                else:
                    raise CoreException(dict(
                        message='Could not del specified resource: ' + str(response.status_code) + ': ' + response.json().get("message", "No message"),
                            url=request_url, response=response))
            ''')
            local_dict = locals().copy()
            exec(func_body, globals(), local_dict)
            return local_dict['_deller']

        def _make_setter_method(request_method, method_config):
            format_string, inner_doc_string = method_config
            matches = [x[1] for x in re.findall(r'({(?P<name>\w+)})', format_string)]
            expected_response = [200, 201]
            func_body = dedent(f'''
            def _setter(self, {",".join(matches) + ',' if matches else ""} data): 
                """\\
                {inner_doc_string}
                """ 
                request_url = self._base_url.rstrip("/") + '/' + f'{format_string}'
                response = None
                
                try:
                    response = self._http_session.{request_method.value}(request_url, json=data)
                except requests.exceptions.RequestException as exc:
                    raise CoreException(dict(message=str(exc), exception=exc, url=request_url, response=response))

                if response.status_code in {expected_response}:
                    return response.json()
                else:
                    raise CoreException(dict(
                        message='Could not {request_method.value.upper()} specified resource: ' + str(response.status_code) + ': ' + response.json().get("message", "No message"),
                            url=request_url, response=response))
            ''')
            local_dict = locals().copy()
            exec(func_body, globals(), local_dict)
            return local_dict['_setter']

        namespace['_meta_initialise'] = make_init()
        namespace['set_session'] = make_set_session()
        namespace['default_session'] = make_default_session()
        namespace['reset_session'] = make_reset_session()

        # Create any getter and setter methods for multi-parameter requests
        for k, v in kwargs.get("url_methods", {}).items():
            getter_config = v.get("GET", None)
            deller_config = v.get("DELETE", None)
            patch_setter_config = v.get("PATCH", None)
            put_setter_config = v.get("PUT", None)
            post_setter_config = v.get("POST", None)

            if getter_config:
                if len(getter_config) == 2:
                    namespace[f'get_{k}'] = _make_getter_method(getter_config)
                else:
                    raise CoreException(dict(message="Method GET tuple requires a path / parameter template and a docstring"))

            if deller_config:
                if len(deller_config) == 2:
                    namespace[f'delete_{k}'] = _make_deller_method(deller_config)
                else:
                    raise CoreException(dict(message="Method DELETE tuple requires a path / parameter template and a docstring"))

            if patch_setter_config:
                if len(patch_setter_config) == 2:
                    namespace[f'patch_{k}'] = _make_setter_method(RequestType.PATCH, patch_setter_config)
                else:
                    raise CoreException(dict(message="Method PATCH tuple requires a path / parameter template and a docstring"))

            if put_setter_config:
                if len(put_setter_config) == 2:
                    namespace[f'put_{k}'] = _make_setter_method(RequestType.PUT, put_setter_config)
                else:
                    raise CoreException(dict(message="Method PUT tuple requires a path / parameter template and a docstring"))

            if post_setter_config:
                if len(post_setter_config) == 2:
                    namespace[f'post_{k}'] = _make_setter_method(RequestType.POST, post_setter_config)
                else:
                    raise CoreException(dict(message="Method POST tuple requires a path / parameter template and a docstring"))

        return super().__new__(mcs, name, bases, namespace)

    def __init__(cls, name, bases, namespace, *args, **kwargs):
        super().__init__(name, bases, namespace)
