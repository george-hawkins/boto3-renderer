import os.path
import glob

from blender import run_blender

_CYCLES_DEVICE = "OPTIX"


def _get_python_expr(samples, motion_blur):
    return f"""
        import bpy

        scene = bpy.context.scene
        scene.cycles.samples = {samples}
        scene.render.use_motion_blur = {motion_blur}
    """


def render_blend_file_frame(blender, input_file, samples, motion_blur, frame, output_prefix="frame-"):
    if os.path.isabs(output_prefix):
        raise RuntimeError(f"absolute output prefixes are not supported - {output_prefix}")

    def get_output_files():
        return set(glob.iglob(glob.escape(output_prefix) + "*"))

    existing = get_output_files()
    if len(existing) != 0:
        # Frames, that were not deleted after being uploaded, have been left lying around.
        raise RuntimeError(f"frame(s) {existing} must be removed")

    run_blender(blender, input_file, _get_python_expr(samples, motion_blur), [
        "-E", "CYCLES",
        "-o", f"//{output_prefix}",
        "-f", str(frame),
        "--",
        "--cycles-device", _CYCLES_DEVICE
    ])

    output_file = get_output_files()

    if len(output_file) != 1:
        # Maybe multiple workers are accidentally running concurrently.
        raise RuntimeError("couldn't determine output file")

    return next(iter(output_file))
