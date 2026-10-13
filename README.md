# ComfyUI-FPS-Resample

A lightweight, high-performance custom node for [ComfyUI](https://github.com/comfyanonymous/ComfyUI) to dynamically resample image batches / video frame sequences to any target frame rate (FPS) while **strictly preserving playback duration**.

---

## 🚀 Why This Node?

When generating AI video (e.g. via LTX-Video, Wan, CogVideoX, or AnimateDiff), generations typically output at **24 fps**. 

To smooth out motion, many creators use **RIFE 2×** (which doubles the frame rate to **48 fps**). However, standard video delivery platforms (and client specs) usually demand **30 fps** or **60 fps**.

If you plug a 48 fps frame batch directly into a 30 fps video combine node, one of two bad things happens:
1. **Duration Stretch (Slow Motion):** VHS Video Combine plays 48 frames per second at 30 fps, causing the video duration to balloon by 60%.
2. **Choppy Stutter / External FFmpeg:** Manually re-encoding with external FFmpeg drops frames ungracefully or requires manual command-line processing outside ComfyUI.

**ComfyUI-FPS-Resample** calculates the exact timing distribution natively inside PyTorch in milliseconds, selecting the optimal frame sequence so your video stays **100% duration-accurate**.

```
[ AI Video (24 fps) ]
         │
         ▼
[ RIFE 2× VFI (48 fps) ]
         │
         ▼
[ FPS Resample (Preserve Duration) ]  ◄── source_fps: 48, target_fps: 30
         │  images (180 frames)
         │  target_fps (30.0)
         ▼
[ VHS Video Combine ]  (fps: 30)
```

---

## ⏱️ Mathematical Timing Examples

The formula calculates:
$$\text{Duration} = \frac{\text{Total Source Frames}}{\text{Source FPS}}$$
$$\text{Target Frames} = \text{round}(\text{Duration} \times \text{Target FPS})$$

| Scenario | Original (24 fps) | After RIFE 2× (48 fps) | Target (30 fps) | Video Duration |
| :--- | :--- | :--- | :--- | :--- |
| **6-Second Clip** | 144 frames | 288 frames | **180 frames** | **6.00 seconds** (Exact) |
| **20-Second Clip** | 480 frames | 960 frames | **600 frames** | **20.00 seconds** (Exact) |
| **RIFE 4× (96 fps)** | 144 frames | 576 frames | **360 frames (60 fps)** | **6.00 seconds** (Exact) |

---

## 🧩 Nodes Included

### 1. `FPS Resample (Preserve Duration)`
The core resampling node.

#### Inputs:
* `images` (*IMAGE*): Input image batch tensor (`[B, H, W, C]`).
* `source_fps` (*FLOAT*, default: `48.0`): Framerate of the input sequence (e.g. 48 after RIFE 2×).
* `target_fps` (*FLOAT*, default: `30.0`): Framerate of the target sequence (e.g. 24, 25, 30, 60).
* `resample_mode` (*ENUM*):
  * `nearest (recommended)`: Center-timestamp sampling. Preserves unblurred source frames (ideal for RIFE/AI generated video) with uniform cadence.
  * `exact_span`: Linear mapping from first frame (0) to last frame ($N-1$).
  * `linear_blend`: Cross-fades adjacent frames using weighted alpha blending (useful for smoothing non-interpolated inputs).
  * `floor`: Start-timestamp cadence sampling.

#### Outputs:
* `images` (*IMAGE*): Resampled frame batch tensor.
* `target_fps` (*FLOAT*): Pass-through of target FPS (can be wired directly to `VHS Video Combine`'s `frame_rate`).
* `frame_count` (*INT*): Total count of resampled frames.
* `duration_seconds` (*FLOAT*): Total duration of the clip in seconds.

---

### 2. `FPS Duration Calculator`
Helper utility to calculate frame counts and duration before rendering (useful for KSampler / AnimateDiff context planning).

#### Inputs:
* `frame_count` (*INT*, default: `288`)
* `source_fps` (*FLOAT*, default: `48.0`)
* `target_fps` (*FLOAT*, default: `30.0`)

#### Outputs:
* `target_frame_count` (*INT*)
* `duration_seconds` (*FLOAT*)
* `info_text` (*STRING*)

---

## 📦 Installation

### Option 1: Git Clone (Manual / Server)
Navigate to your ComfyUI `custom_nodes` directory:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/C0ckr4ch/ComfyUI-FPS-Resample.git
```

Restart ComfyUI and search for **FPS Resample (Preserve Duration)**.

### Option 2: ComfyUI Manager
Search for `ComfyUI-FPS-Resample` in the ComfyUI Manager and click **Install**.

---

## 🛠️ Usage Quickstart

1. Connect your high-FPS output from RIFE (e.g. 48 fps) to `images`.
2. Set `source_fps` to `48.0`.
3. Set `target_fps` to `30.0`.
4. Connect the output `images` to `VHS Video Combine`'s `images`.
5. Connect `target_fps` to `VHS Video Combine`'s `frame_rate`.
6. Render! Your video will now output at a smooth 30 fps with the exact intended duration.

---

## 📄 License
MIT License. Created by [c0ckr4ch](https://github.com/C0ckr4ch).
