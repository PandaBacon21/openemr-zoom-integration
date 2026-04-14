# Zoom / OpenEMR Integration

More README updates to follow as this project progresses.

## Usage

> **Note**
>
> The following sample application is a personal, open-source project shared by the app creator and not an officially supported Zoom Communications, Inc. sample application. Zoom Communications, Inc., its employees and affiliates are not responsible for the use and maintenance of this application.
>
> Please use this sample application for inspiration, exploration and experimentation at your own risk and enjoyment. You may reach out to the app creator and broader Zoom Developer community on https://devforum.zoom.us/ for technical discussion and assistance, but understand there is no service level agreement support for this application. Thank you and happy coding!

## Testing

Run backend tests from the repository root:

```bash
server/scripts/test.sh
```

This script runs `uv run pytest -q` with `UV_CACHE_DIR` pinned to `server/.uv-cache` by default so it works in restricted/sandboxed environments.
