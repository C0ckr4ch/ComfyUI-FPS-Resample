"""
ComfyUI-FPS-Resample
Custom node to resample image batches / video frames from source FPS to target FPS
while strictly preserving the total video duration.
"""

import torch

class FPSResample:
    """
    Resample a batch of images from a source frame rate (e.g. 48 fps from RIFE 2x)
    to a target frame rate (e.g. 30 fps) while preserving the exact playback duration.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "source_fps": (
                    "FLOAT",
                    {
                        "default": 48.0,
                        "min": 0.01,
                        "max": 1000.0,
                        "step": 1.0,
                        "round": 0.001,
                        "display": "number",
                    },
                ),
                "target_fps": (
                    "FLOAT",
                    {
                        "default": 30.0,
                        "min": 0.01,
                        "max": 1000.0,
                        "step": 1.0,
                        "round": 0.001,
                        "display": "number",
                    },
                ),
                "resample_mode": (
                    [
                        "nearest (recommended)",
                        "exact_span",
                        "linear_blend",
                        "floor",
                    ],
                    {"default": "nearest (recommended)"},
                ),
            }
        }

    RETURN_TYPES = ("IMAGE", "FLOAT", "INT", "FLOAT")
    RETURN_NAMES = ("images", "target_fps", "frame_count", "duration_seconds")
    FUNCTION = "resample"
    CATEGORY = "video/timing"

    def resample(
        self,
        images,
        source_fps: float,
        target_fps: float,
        resample_mode: str = "nearest (recommended)",
    ):
        # Handle list of images if passed
        if isinstance(images, list):
            images = torch.cat(images, dim=0)

        total_frames = images.shape[0]
        if total_frames == 0:
            raise ValueError("[FPS Resample] Input image batch is empty.")

        if source_fps <= 0 or target_fps <= 0:
            raise ValueError(
                f"[FPS Resample] source_fps ({source_fps}) and target_fps ({target_fps}) must be > 0."
            )

        duration = total_frames / source_fps
        target_count = max(1, round(duration * target_fps))

        # Pass-through fast path if rates match and no blending requested
        if (
            source_fps == target_fps
            or total_frames == 1
            or (target_count == total_frames and resample_mode != "linear_blend")
        ):
            print(
                f"[FPS Resample] Passthrough: {total_frames} frames @ {target_fps} fps ({duration:.2f}s)"
            )
            return (images, float(target_fps), int(total_frames), float(duration))

        device = images.device

        if resample_mode == "nearest (recommended)":
            # Center-timestamp sampling: maps each target frame's midpoint to the active source frame.
            # Preserves unblurred source frames (ideal for RIFE outputs) with uniform cadence.
            indices = [
                min(int((i + 0.5) / target_fps * source_fps), total_frames - 1)
                for i in range(target_count)
            ]
            idx_tensor = torch.tensor(indices, dtype=torch.long, device=device)
            out_images = images.index_select(0, idx_tensor)

        elif resample_mode == "exact_span":
            # Spans linearly from frame 0 to frame (total_frames - 1)
            if target_count == 1:
                indices = [0]
            else:
                indices = [
                    min(
                        round(i * (total_frames - 1) / (target_count - 1)),
                        total_frames - 1,
                    )
                    for i in range(target_count)
                ]
            idx_tensor = torch.tensor(indices, dtype=torch.long, device=device)
            out_images = images.index_select(0, idx_tensor)

        elif resample_mode == "floor":
            # Start-of-frame timestamp sampling (drop-frame style)
            indices = [
                min(int(i / target_fps * source_fps), total_frames - 1)
                for i in range(target_count)
            ]
            idx_tensor = torch.tensor(indices, dtype=torch.long, device=device)
            out_images = images.index_select(0, idx_tensor)

        elif resample_mode == "linear_blend":
            # Weighted cross-fade blending between consecutive frames
            resampled_list = []
            ratio = (total_frames - 1) / max(target_count - 1, 1)
            for i in range(target_count):
                pos = i * ratio
                low = int(pos)
                high = min(low + 1, total_frames - 1)
                weight = pos - low
                if weight <= 0 or low == high:
                    resampled_list.append(images[low])
                else:
                    resampled_list.append(
                        (1.0 - weight) * images[low] + weight * images[high]
                    )
            out_images = torch.stack(resampled_list, dim=0)

        else:
            raise ValueError(f"[FPS Resample] Unknown mode: {resample_mode}")

        print(
            f"[FPS Resample] {total_frames} frames ({source_fps} fps) -> "
            f"{target_count} frames ({target_fps} fps) | "
            f"Duration preserved: {duration:.2f}s | Mode: {resample_mode}"
        )

        return (out_images, float(target_fps), int(target_count), float(duration))


class FPSDurationCalculator:
    """
    Utility node to calculate target frame count and video duration before rendering.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "frame_count": ("INT", {"default": 288, "min": 1, "max": 1000000, "step": 1}),
                "source_fps": ("FLOAT", {"default": 48.0, "min": 0.01, "max": 1000.0, "step": 1.0, "round": 0.001}),
                "target_fps": ("FLOAT", {"default": 30.0, "min": 0.01, "max": 1000.0, "step": 1.0, "round": 0.001}),
            }
        }

    RETURN_TYPES = ("INT", "FLOAT", "STRING")
    RETURN_NAMES = ("target_frame_count", "duration_seconds", "info_text")
    FUNCTION = "calculate"
    CATEGORY = "video/timing"

    def calculate(self, frame_count: int, source_fps: float, target_fps: float):
        if source_fps <= 0 or target_fps <= 0:
            raise ValueError("[FPS Calculator] FPS values must be > 0.")

        duration = frame_count / source_fps
        target_count = max(1, round(duration * target_fps))
        info = (
            f"Duration: {duration:.2f}s | "
            f"{frame_count} frames @ {source_fps} fps -> {target_count} frames @ {target_fps} fps"
        )
        return (int(target_count), float(duration), info)


NODE_CLASS_MAPPINGS = {
    "FPSResample": FPSResample,
    "FPSDurationCalculator": FPSDurationCalculator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FPSResample": "FPS Resample (Preserve Duration)",
    "FPSDurationCalculator": "FPS Duration Calculator",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
