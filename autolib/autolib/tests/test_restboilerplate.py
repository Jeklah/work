import functools
import pytest
import requests

from autolib.restboilerplate import RestBoilerPlate
from autolib.coreexception import CoreException


@pytest.fixture(scope='module')
def url_property_test():
    class RestBoilerPlateTest(metaclass=RestBoilerPlate, url_properties={
        "get_put_posts": {"GET": "posts", "PUT": "posts/1", "DOC": "Sample API"},
        "get_post_posts": {"GET": "posts", "POST": "posts", "DOC": "Sample API"},
        "get_patch_posts": {"GET": "posts", "PATCH": "posts/1", "DOC": "Sample API"}
    }):
        def __init__(self, base_url):
            self._meta_initialise(base_url)

    return RestBoilerPlateTest("http://jsonplaceholder.typicode.com")


def test_property_get_and_put(url_property_test):
    posts = url_property_test.get_put_posts
    assert posts
    posts[0]["userId"] = 9999
    assert posts[0]["userId"] == 9999
    url_property_test.get_put_posts = posts


def test_property_get_and_post(url_property_test):
    posts = url_property_test.get_post_posts
    assert posts
    posts[0]["userId"] = 9999
    assert posts[0]["userId"] == 9999
    url_property_test.get_post_posts = posts


def test_property_get_and_patch(url_property_test):
    posts = url_property_test.get_patch_posts
    assert posts
    posts[0]["userId"] = 9999
    assert posts[0]["userId"] == 9999
    url_property_test.get_patch_posts = posts


def test_too_many_property_setters():
    try:
        class UrlTooManySetters(metaclass=RestBoilerPlate, url_properties={
            "get_put_posts": {"GET": "posts", "POST": "posts", "PUT": "posts/1", "DOC": "Sample API"},
        }):
            pass
    except CoreException as e:
        print(e)


def test_property_404_response():
    with pytest.raises(CoreException):
        class Url404Response(metaclass=RestBoilerPlate, url_properties={
            "getter": {"GET": "puffins", "DOC": "Sample API"},
        }):
            def __init__(self, base_url):
                self._meta_initialise(base_url)

        a = Url404Response("http://jsonplaceholder.typicode.com")
        assert a.getter


@pytest.fixture(scope='module')
def url_property_and_method_test():
    class PostComments(metaclass=RestBoilerPlate,
                       url_properties={
                           "posts": {"GET": "posts", "DOC": "Get all posts"}},
                       url_methods={
                           "post": {"GET": ("posts/{index}", "Get post by index value")},
                           "postComments": {
                               "GET": ("posts/{index}/comments", "Get post comments by post index"),
                               "DELETE": ("comments/{index}", "Delete a comment by index"),
                               "POST": ("comments", "Add a new comment (POST)"),
                               "PUT": ("comments/{index}", "Update an existing comment (PUT)"),
                               "PATCH": ("comments/{index}", "Partial comment rewrite (PATCH)")}
                       }):
        """\
        Provides access to post comments in the mock API.
        """

        def __init__(self, base_url):
            self._meta_initialise(base_url)
            self._hostname = 'donkeytronix'
            super().__init__()

    return PostComments("http://jsonplaceholder.typicode.com")


def test_property_get_posts(url_property_and_method_test):
    """\
    """
    a = url_property_and_method_test.posts
    assert len(a)


def test_get_single_post(url_property_and_method_test):
    """\
    """
    a = url_property_and_method_test.get_post(2)
    assert a.get('title') == 'qui est esse'


def test_get_post_comments(url_property_and_method_test):
    """\
    """
    a = url_property_and_method_test.get_postComments(2)
    assert len(a) == 5
    assert a[2].get('name', None) == 'et omnis dolorem'


def test_del_single_comment(url_property_and_method_test):
    """\
    """
    url_property_and_method_test.delete_postComments(2)


def test_post_comment(url_property_and_method_test):
    """\
    """
    new_comment = {
        "postId": 1,
        "id": 1,
        "name": "id labore ex et quam laborum",
        "email": "Eliseo@gardner.biz",
        "body": "laudantium enim quasi est quidem magnam voluptate ipsam eos\ntempora quo necessitatibus\ndolor quam autem quasi\nreiciendis et nam sapiente accusantium"
    }

    url_property_and_method_test.post_postComments(new_comment)


def test_put_comment(url_property_and_method_test):
    """\
    """
    new_comment = {
        "postId": 1,
        "id": 1,
        "name": "id labore ex et quam laborum",
        "email": "Eliseo@gardner.biz",
        "body": "laudantium enim quasi est quidem magnam voluptate ipsam eos\ntempora quo necessitatibus\ndolor quam autem quasi\nreiciendis et nam sapiente accusantium"
    }

    url_property_and_method_test.put_postComments(2, new_comment)


def test_patch_comment(url_property_and_method_test):
    """\
    """
    new_comment = {
        "name": "partialium updateum epicum"
    }

    url_property_and_method_test.patch_postComments(3, new_comment)


class MockSession:
    def get(self, *args, **kwargs):
        """\
        Construct a requests Response object and return that to the calling code.
        """
        response = requests.Response()
        response.status_code = 200
        response._content = b'{"title": "These are not the droids you are looking for"}'
        return response


def test_get_with_mock_session(url_property_and_method_test):
    """\
    Replace the requests.Session that's used by the PostComments class built by the metaclass so that get()
    just returns an expected requests.Response object with a set status_code and body. Check that we receive this.
    Then, reset the Session back to the original one and make a genuine GET as before.
    """
    url_property_and_method_test.set_session(MockSession())
    a = url_property_and_method_test.get_post(2)
    assert a.get('title') == "These are not the droids you are looking for"
    url_property_and_method_test.reset_session()
    a = url_property_and_method_test.get_post(2)
    assert a.get('title') == 'qui est esse'


@pytest.fixture(scope='module')
def custom_session_class():
    """\
    Pass a custom requests Session object into the metaclass as it's used to create
    a class. Use a partial function to set the timeouts for all method types!
    """

    session = requests.Session()
    session.request = functools.partial(session.request, timeout=1)

    class CustomSession(metaclass=RestBoilerPlate,
                        url_properties={"test_prop": {"GET": "delay/10", "DOC": "Test 10s delay GET"}},
                        url_methods={
                            "test_method": {
                                "GET": ("delay/{timeout}", "GET operation with specified response delay"),
                                "POST": ("delay/{timeout}", "POST operation with specified response delay"),
                                "PUT": ("delay/{timeout}", "PUT operation with specified response delay"),
                                "PATCH": ("delay/{timeout}", "PATCH operation with specified response delay"),
                                "DELETE": ("delay/{timeout}", "DELETE operation with specified response delay")
                            }
                        },
                        http_session=session
                        ):
        def __init__(self, base_url):
            self._meta_initialise(base_url)

    return CustomSession("http://httpbin.org")


def test_property_timeout(custom_session_class):
    """\
    Request a property that makes a GET http request that takes 10s to respond
    but with a 3s timeout. This should raise a requests.exceptions.ReadTimeout
    """
    with pytest.raises(CoreException) as exc:
        _ = custom_session_class.test_prop

    assert type(exc.value.args[0].get("exception", None)) == requests.exceptions.ReadTimeout


def test_get_method_timeout(custom_session_class):
    """\
    Call a method that makes a GET http request that takes 10s to respond
    but with a 3s timeout. This should raise a requests.exceptions.ReadTimeout
    """
    with pytest.raises(CoreException) as exc:
        _ = custom_session_class.get_test_method(10)

    assert type(exc.value.args[0].get("exception", None)) == requests.exceptions.ReadTimeout


def test_post_method_timeout(custom_session_class):
    """\
    Call a method that makes a POST http request that takes 10s to respond
    but with a 3s timeout. This should raise a requests.exceptions.ReadTimeout
    """
    with pytest.raises(CoreException) as exc:
        _ = custom_session_class.post_test_method(10, None)

    assert type(exc.value.args[0].get("exception", None)) == requests.exceptions.ReadTimeout


def test_put_method_timeout(custom_session_class):
    """\
    Call a method that makes a PUT http request that takes 10s to respond
    but with a 3s timeout. This should raise a requests.exceptions.ReadTimeout
    """
    with pytest.raises(CoreException) as exc:
        _ = custom_session_class.put_test_method(10, None)

    assert type(exc.value.args[0].get("exception", None)) == requests.exceptions.ReadTimeout


def test_patch_method_timeout(custom_session_class):
    """\
    Call a method that makes a PATCH http request that takes 10s to respond
    but with a 3s timeout. This should raise a requests.exceptions.ReadTimeout
    """
    with pytest.raises(CoreException) as exc:
        _ = custom_session_class.patch_test_method(10, None)

    assert type(exc.value.args[0].get("exception", None)) == requests.exceptions.ReadTimeout


def test_delete_method_timeout(custom_session_class):
    """\
    Call a method that makes a DELETE http request that takes 10s to respond
    but with a 3s timeout. This should raise a requests.exceptions.ReadTimeout
    """
    with pytest.raises(CoreException) as exc:
        _ = custom_session_class.delete_test_method(10)

    assert type(exc.value.args[0].get("exception", None)) == requests.exceptions.ReadTimeout


def test_required_property_docstring():
    """\
    Try to create a class from the metaclass with a property missing its docstring
    """

    with pytest.raises(CoreException) as exc:
        class CustomSession(metaclass=RestBoilerPlate,
                            url_properties={"test_prop": {"GET": "delay/10"}},
                            url_methods={
                                "test_method": {
                                    "GET": ("delay/{timeout}", "GET operation with specified response delay"),
                                }
                            }
                            ):
            def __init__(self, base_url):
                self._meta_initialise(base_url)

    assert exc.value.args[0].get("message", None) == "Every generated property requires a DOC entry containing it's docstring."


def test_required_method_docstring_get():
    """\
    Try to create a class from the metaclass with a GET method with no docstring
    """

    with pytest.raises(CoreException) as exc:
        class CustomSession(metaclass=RestBoilerPlate,
                            url_methods={
                                "test_method": {
                                    "GET": ("delay/{timeout}"),
                                }
                            }
                            ):
            def __init__(self, base_url):
                self._meta_initialise(base_url)

    assert exc.value.args[0].get("message", None) == "Method GET tuple requires a path / parameter template and a docstring"


def test_required_method_docstring_delete():
    """\
    Try to create a class from the metaclass with a DELETE method with no docstring
    """

    with pytest.raises(CoreException) as exc:
        class CustomSession(metaclass=RestBoilerPlate,
                            url_methods={
                                "test_method": {
                                    "DELETE": ("delay/{timeout}"),
                                }
                            }
                            ):
            def __init__(self, base_url):
                self._meta_initialise(base_url)

    assert exc.value.args[0].get("message", None) == "Method DELETE tuple requires a path / parameter template and a docstring"


def test_required_method_docstring_put():
    """\
    Try to create a class from the metaclass with a PUT method with no docstring
    """

    with pytest.raises(CoreException) as exc:
        class CustomSession(metaclass=RestBoilerPlate,
                            url_methods={
                                "test_method": {
                                    "PUT": ("delay/{timeout}"),
                                }
                            }
                            ):
            def __init__(self, base_url):
                self._meta_initialise(base_url)

    assert exc.value.args[0].get("message", None) == "Method PUT tuple requires a path / parameter template and a docstring"


def test_required_method_docstring_patch():
    """\
    Try to create a class from the metaclass with a PATCH method with no docstring
    """

    with pytest.raises(CoreException) as exc:
        class CustomSession(metaclass=RestBoilerPlate,
                            url_methods={
                                "test_method": {
                                    "PATCH": ("delay/{timeout}"),
                                }
                            }
                            ):
            def __init__(self, base_url):
                self._meta_initialise(base_url)

    assert exc.value.args[0].get("message", None) == "Method PATCH tuple requires a path / parameter template and a docstring"


def test_required_method_docstring_post():
    """\
    Try to create a class from the metaclass with a POST method with no docstring
    """

    with pytest.raises(CoreException) as exc:
        class CustomSession(metaclass=RestBoilerPlate,
                            url_methods={
                                "test_method": {
                                    "POST": ("delay/{timeout}"),
                                }
                            }
                            ):
            def __init__(self, base_url):
                self._meta_initialise(base_url)

    assert exc.value.args[0].get("message", None) == "Method POST tuple requires a path / parameter template and a docstring"
