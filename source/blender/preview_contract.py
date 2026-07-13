"""Shared artifact contract for Blender preview generation and verification."""

SAMPLED_FRAMES = tuple(round(1 + index * 95 / 23) for index in range(24))
ANIMATIC_FRAME_NAMES = tuple(f"f{frame:04d}.webp" for frame in SAMPLED_FRAMES)
ANIMATIC_SIZE = (480, 270)
STILL_CONTRACT = {
    "graybox-desktop.webp": (960, 540),
    "lookdev-desktop.webp": (960, 540),
    "mobile-lookdev.webp": (540, 720),
    "act01-system.webp": (960, 540),
    "act02-flow.webp": (960, 540),
    "act03-cutaway.webp": (960, 540),
    "act04-exploded.webp": (960, 540),
    "act05-delivery.webp": (960, 540),
}
