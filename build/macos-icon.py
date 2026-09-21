"""Draw the application icon into a .icns.

One drawing, rasterised at every size macOS asks for. The drawing is
src/libera/icon.svg -- the same file the Flatpak exports as its icon and the
same one the host sets as the Dock icon at runtime, so the three cannot drift.
This script used to draw a lettered tile with AppKit primitives because there
was no artwork; the comment it carried, that the one thing which had to agree
between the two was the blue, is the reason it now reads the SVG instead.

NSImage has rasterised SVG since macOS 13. Nothing else here can, so a build
machine older than that will fail at the first draw rather than produce a
blank icon -- which is the right way round.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import AppKit
import Foundation

HERE = pathlib.Path(__file__).parent
ICON = HERE.parent / "src" / "libera" / "icon.svg"

# All seven from the same drawing, 16 included. The brand keeps a second mark
# without the glyph for 16 to 31 px, on the grounds that below 32 the glyph
# collapses and colour does the telling -- but that variant is for a favicon or
# a menu bar, somewhere that picks a file per size. An .icns is one artwork at
# seven sizes by construction, and rendered at 16 the dot is still a dot.
SIZES = [16, 32, 64, 128, 256, 512, 1024]

# Apple's icon grid: on a 1024 canvas the body is 824 square and centred, so
# the margin is 100 a side. The tile is drawn to that and not edge to edge -- a
# macOS icon filling its canvas sits visibly larger than everything beside it
# in the Dock. Linux has no such convention, which is why the SVG itself is
# cropped to the tile and the inset lives here.
MARGIN = 100 / 1024


def draw(image: AppKit.NSImage, size: int) -> bytes:
    """The mark, rasterised into a `size` by `size` PNG."""
    rep = AppKit.NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, size, size, 8, 4, True, False, AppKit.NSDeviceRGBColorSpace, 0, 0
    )
    ctx = AppKit.NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    AppKit.NSGraphicsContext.saveGraphicsState()
    AppKit.NSGraphicsContext.setCurrentContext_(ctx)

    inset = round(size * MARGIN)
    body = Foundation.NSMakeRect(inset, inset, size - 2 * inset, size - 2 * inset)
    # No setSize_ before this. The SVG declares width and height of 1024, so
    # every size here is a downscale of it and comes out clean -- checked, the
    # bytes are identical with and without. Were the drawing sized to its
    # 80-unit box instead, the largest icons would be upscaled from an 80px
    # cache and this would need one.
    image.drawInRect_fromRect_operation_fraction_(
        body, Foundation.NSZeroRect, AppKit.NSCompositingOperationSourceOver, 1.0
    )

    AppKit.NSGraphicsContext.restoreGraphicsState()
    return rep.representationUsingType_properties_(AppKit.NSPNGFileType, {})


def main() -> int:
    out = pathlib.Path(sys.argv[1])
    image = AppKit.NSImage.alloc().initWithContentsOfFile_(str(ICON))
    if image is None:
        print(f"FATAL: could not read {ICON}", file=sys.stderr)
        return 1

    iconset = out.with_suffix(".iconset")
    iconset.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        png = bytes(draw(image, size))
        (iconset / f"icon_{size}x{size}.png").write_bytes(png)
        # Retina variants are the same pixels under a different name.
        half = size // 2
        if half in SIZES:
            (iconset / f"icon_{half}x{half}@2x.png").write_bytes(png)
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out)], check=True)
    print(f"    {out} ({out.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
