# aioskynet

An async wrapper of the Sia Skynet API.

## Basic usage

### Uploading a file

```py
from asyncio import run

from aioskynet import SkynetClient, File


client = SkynetClient()


async def main():
    file = File("test.py", open("test.py"))
    data = await client.upload_file(file)

    print(data)  # Instance of aioskynet.SkynetResponse

    # Close the client when finished.
    await client.close()

run(main())
```
