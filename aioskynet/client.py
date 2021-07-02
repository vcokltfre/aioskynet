"""
MIT License

Copyright (c) 2021 vcokltfre

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from copy import copy
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from aiohttp import ClientResponse, ClientSession, BasicAuth, FormData

from .constants import PORTAL_URL
from .errors import AIOSkynetError
from .file import File


RequestMethod = Literal["get", "post", "head", "delete", "put"]


@dataclass
class Skylink:
    skylink: str

    @property
    def http(self) -> str:
        return f"{PORTAL_URL}/{self.skylink}"


@dataclass
class SkynetResponse:
    skylink: Skylink
    merkleroot: str
    bitfield: int


class SkynetClient:
    def __init__(self, api_key: Optional[str] = None, *, portal_url: Optional[str] = None) -> None:
        """An async Skynet client.

        Args:
            api_key (str, optional): The Skynet API key to make requests with.
            portal_url (str, optional): The URL for the Kkynet portal. Defaults to None.
        """

        self._raw_session: Optional[ClientSession] = None

        self._auth = BasicAuth(api_key) if api_key else None
        self._portal_url = portal_url or PORTAL_URL

    @property
    def _session(self) -> ClientSession:
        if self._raw_session is None or not self._raw_session.closed:
            self._raw_session = ClientSession(auth=self._auth)
        return self._raw_session

    async def close(self) -> None:
        if not self._raw_session.closed:
            await self._raw_session.close()

    async def _request(self, method: RequestMethod, path: str, *, attempts: int = 3, **kwargs) -> ClientResponse:
        """Make a request to the Skynet API.

        Args:
            method (RequestMethod): The HTTP method to make the request with.
            path (str): The URL path to request on.
            attempts (int): The maximum number of attempts to make before giving up.

        Raises:
            AIOSkynetError: The request failed on all attempts.

        Returns:
            ClientResponse: The HTTP response.
        """

        assert attempts >= 1

        last_response: ClientResponse = None

        for i in range(attempts):
            _kwargs = copy(kwargs)

            if files := _kwargs.pop("files", []):
                files: List[File]

                formdata = FormData()

                for file in files:
                    if not isinstance(file, File):
                        raise TypeError(f"files must be a list of aioskynet.File, not {file.__class__.__qualname__}")
                    file.file.seek(0)
                    formdata.add_field(file.filename, file.file, filename=file.filename)

                _kwargs["data"] = formdata

            response = await self._session.request(method, self._portal_url + path, **_kwargs)

            if 200 <= response.status < 300:
                return response

            last_response = response

        raise AIOSkynetError(last_response, f"{method} on {path} failed after {attempts} attempts with final status {last_response.status}.")

    async def upload_file(self, file: File) -> SkynetResponse:
        path = f"/skynet/skyfile/{file.filename}"

        response = await (await self._request("post", path, files=[file])).json()

        return SkynetResponse(
            skylink=Skylink(response.pop("skylink")),
            **response,
        )
