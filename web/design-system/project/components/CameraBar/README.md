# CameraBar

Camera controls laid out like Apple Camera, over a full-screen dark viewfinder.

Top: close, and flash only when the phone supports it. Bottom: the hint, upload, the shutter, and (in tag mode) Type it in. `TagFrame` adds the care-label shaped guide for tags. `Shutter` is the ring alone.

**You provide:** `mode` (`outfit` or `tag`), `flash` (leave undefined to hide the button), `onFlash`, `onClose`, `onShutter`, `onUpload`, `onTypeInstead`, optional `hint`.
