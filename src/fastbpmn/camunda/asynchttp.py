import json
from typing import Any, Optional, Union

import httpx
from httpx_auth import Basic
from pydantic import HttpUrl
from structlog import getLogger

from .json import CamundaJSONEncoder

ACCEPT_HEADER = {"accept": "application/json"}
CONTENT_TYPE_HEADER = {"content-type": "application/json"}
FOLLOW_REDIRECTS = True

logger = getLogger(__name__)


def prepare_http_data(data: Optional[Union[str, dict, Any]]) -> Optional[str]:
    """
    Prepare the given data element to be used in a http request.
    :param data:
    :return:
    """
    if data is None:
        return None

    if isinstance(data, str):
        # Might be a json already
        return data

    return json.dumps(data, cls=CamundaJSONEncoder)


class AsyncCamundaHTTP:
    """
    Perform http requests
    """

    def __init__(
        self,
        base_url: httpx.URL
        | HttpUrl
        | str,  # ToDo[fd]: let settings export as httpx.URL
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float | None = None,
    ):
        """
        Initialize Class
        """
        if not timeout:
            timeout = 30.0

        if not base_url:
            raise ValueError("base_url cannot be None")

        try:
            # if base_url is HttpURL we use unicode_string to transform
            base_url = base_url.unicode_string()
        except AttributeError:
            # on failure, we assume it's already a string
            pass

        # force trailing slash
        # base_url += '' if base_url.endswith('/') else '/'

        auth = Basic(username, password) if username and password else None
        self.http_client = httpx.AsyncClient(
            base_url=base_url,
            headers=ACCEPT_HEADER,
            auth=auth,
            follow_redirects=FOLLOW_REDIRECTS,
            timeout=timeout,
        )
        self.shttp_client = httpx.Client(
            base_url=base_url,
            headers=ACCEPT_HEADER,
            auth=auth,
            follow_redirects=FOLLOW_REDIRECTS,
            timeout=timeout,
        )

    def __del__(self):
        """
        Delete session object
        """
        try:
            del self.http_client
        except AttributeError:
            pass

    async def get(
        self, resource: str, params: dict = None, binary: bool = False
    ) -> Optional[dict]:
        """
        Perform GET request and return result as dict

        :param resource: path to Camunda API endpoint
        :param params: optional query parameters
        :param binary: for file download (I assume)
        """

        try:
            res = await self.http_client.get(resource, params=params)
            res.raise_for_status()
        except httpx.TimeoutException as exc:
            # Maybe set up for a retry, or continue in a retry loop
            raise SystemExit("Timeout") from exc
        except httpx.TooManyRedirects as exc:
            # Tell the user their URL was bad and try a different one
            raise SystemExit("Too Many Redirects") from exc
        except httpx.HTTPError as exc:
            logger.error(exc)
            raise SystemExit(exc) from exc

        try:
            j = res.content if binary else res.json()
        except ValueError:
            logger.error("%s %s", res.status_code, res.text)
            raise
        return j

    def sget(
        self, resource: str, params: dict = None, binary: bool = False
    ) -> Optional[dict]:
        """
        Perform GET request and return result as dict

        :param resource: path to Camunda API endpoint
        :param params: optional query parameters
        :param binary: for file download (I assume)
        """

        try:
            res = self.shttp_client.get(resource, params=params)
            res.raise_for_status()
        except httpx.TimeoutException as exc:
            # Maybe set up for a retry, or continue in a retry loop
            raise SystemExit("Timeout") from exc
        except httpx.TooManyRedirects as exc:
            # Tell the user their URL was bad and try a different one
            raise SystemExit("Too Many Redirects") from exc
        except httpx.HTTPError as exc:
            logger.error(exc)
            raise SystemExit(exc) from exc

        try:
            j = res.content if binary else res.json()
        except ValueError:
            logger.error("%s %s", res.status_code, res.text)
            raise
        return j

    async def get_raw(
        self, resource: str, params: dict = None, binary: bool = False
    ) -> Optional[dict] | bytes:
        """
        Perform GET request and return result as dict

        :param resource: path to Camunda API endpoint
        :param params: optional query parameters
        :param binary: for file download (I assume)
        """

        try:
            res = await self.http_client.get(resource, params=params)
            res.raise_for_status()
        except httpx.TimeoutException as exc:
            raise exc
        except httpx.TooManyRedirects as exc:
            raise exc
        except httpx.HTTPStatusError as exc:
            raise exc
        except httpx.HTTPError as exc:
            raise exc

        try:
            j = res.content if binary else res.json()
        except ValueError:
            logger.error("%s %s", res.status_code, res.text)
            raise
        return j

    async def post_raw(
        self, resource: str, data: Optional[Union[dict, str]]
    ) -> Optional[dict]:
        """
        Perform POST request and return result

        :param resource: path to Camunda API endpoint
        :param data:
        """

        data_json = prepare_http_data(data)

        try:
            res = await self.http_client.post(
                resource, data=data_json, headers=CONTENT_TYPE_HEADER
            )
            res.raise_for_status()
        except httpx.TimeoutException as exc:
            raise exc
        except httpx.TooManyRedirects as exc:
            raise exc
        except httpx.HTTPStatusError as exc:
            raise exc
        except httpx.HTTPError as exc:
            raise exc

        if res.status_code == 204:
            return None
        if res.status_code != 200:
            logger.warning(res)

        try:
            j = res.json()
        except ValueError:
            logger.error("%s %s", res.status_code, res.text)
            # Todo: should we really return None here?
            return None
        return j

    async def post(
        self, resource: str, data: Optional[Union[dict, str]]
    ) -> Optional[dict] | list:
        """
        Perform POST request and return result

        :param resource: path to Camunda API endpoint
        :param data:
        """

        data_json = prepare_http_data(data)

        try:
            res = await self.http_client.post(
                resource, data=data_json, headers=CONTENT_TYPE_HEADER
            )
            res.raise_for_status()
        except httpx.TimeoutException as exc:
            # Maybe set up for a retry, or continue in a retry loop
            raise SystemExit("Timeout") from exc
        except httpx.TooManyRedirects as exc:
            # Tell the user their URL was bad and try a different one
            raise SystemExit("Too Many Redirects") from exc
        except httpx.HTTPStatusError as exc:
            # Todo: here we should catch Camunda PE HTTP responses and indicate as a Taskfailure.
            #   in the meantime, just show the log
            logger.error(exc.response.status_code)
            logger.error(exc.response.text)
            raise SystemExit(exc) from exc
        except httpx.HTTPError as exc:
            # Todo: here we should catch Camunda PE HTTP responses and indicate as a Taskfailure.
            #   in the meantime, just show the log
            logger.error(exc)
            raise SystemExit(exc) from exc

        if res.status_code == 204:
            return None
        if res.status_code != 200:
            logger.warning(res)

        try:
            j = res.json()
        except ValueError:
            logger.error("%s %s", res.status_code, res.text)
            # Todo: should we really return None here?
            return None
        return j

    async def put(self, resource: str, data=Optional[dict]) -> Optional[dict]:
        """
        Perform PUT request and return result as dict

        :param resource: path to Camunda API endpoint
        :param data:
        :return: Result as dict, None on failure
        """

        j = json.dumps(data, cls=CamundaJSONEncoder) if data else None

        try:
            res = await self.http_client.put(
                resource, data=j, headers=CONTENT_TYPE_HEADER
            )
            res.raise_for_status()
        except httpx.TimeoutException as exc:
            # Maybe set up for a retry, or continue in a retry loop
            raise SystemExit("Timeout") from exc
        except httpx.TooManyRedirects as exc:
            # Tell the user their URL was bad and try a different one
            raise SystemExit("Too Many Redirects") from exc
        except httpx.HTTPStatusError as exc:
            # Todo: here we should catch Camunda PE HTTP responses and indicate as a Taskfailure.
            #   in the meantime, just show the log
            logger.error(exc.response.status_code)
            logger.error(exc.response.text)
            raise SystemExit(exc) from exc
        except httpx.HTTPError as exc:
            # Todo: here we should catch Camunda PE HTTP responses and indicate as a Taskfailure.
            #   in the meantime, just show the log
            logger.error(exc)
            raise SystemExit(exc) from exc

        logger.debug("PUT %s %s", res.status_code, resource)
        try:
            j = res.json()
        except ValueError:
            logger.error("%s %s", res.status_code, res.text)
            return None
        return j

    async def delete(self, resource: str):
        """
        Perform DELETE request

        :param resource: path to Camunda API endpoint
        """

        try:
            res = await self.http_client.delete(resource)
            res.raise_for_status()
        except httpx.TimeoutException as exc:
            # Maybe set up for a retry, or continue in a retry loop
            raise SystemExit("Timeout") from exc
        except httpx.TooManyRedirects as exc:
            # Tell the user their URL was bad and try a different one
            raise SystemExit("Too Many Redirects") from exc
        except httpx.HTTPStatusError as exc:
            # Todo: here we should catch Camunda PE HTTP responses and indicate as a Taskfailure.
            #   in the meantime, just show the log
            logger.error(exc.response.status_code)
            logger.error(exc.response.text)
            # raise SystemExit(exc) from exc
        except httpx.HTTPError as exc:
            # Todo: here we should catch Camunda PE HTTP responses and indicate as a Taskfailure.
            #   in the meantime, just show the log
            logger.error(exc)
        else:
            return res
