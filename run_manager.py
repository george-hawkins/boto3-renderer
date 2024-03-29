import os.path
import sys
from uuid import uuid4

from boto_basics import BotoBasics, report_non_terminated_instances
from ec2_instances import create_instances, monitor_and_terminate
from job_steps import (
    create_worker_files,
    upload_worker_files,
    create_db_table,
    download_results,
    USER_DATA,
    delete_temporary_files,
)
from names import Names
from pack import pack_blend_file
from settings import frames_str, get_settings
from utils import sizeof_fmt

PACKED_BLEND_FILE = "packed.blend"

basics = BotoBasics()
job_id = uuid4()
names = Names(job_id)


def confirm(settings, clean_up):
    print(
        f"instance count = {settings.instance_count}, .blend file = {settings.blend_file}, "
        f"{frames_str(settings.frames)}, file_format = {settings.file_format}, samples = {settings.samples} and motion_blur = {settings.motion_blur}"
    )
    if settings.interactive and input("Launch workers? [y/N] ") != "y":
        if input("Clean up? [Y/n] ") != "n":
            clean_up()
        sys.exit(0)


def main():
    settings = get_settings()

    basics.create_log_group(names.log_group)
    print(f"Created log group {names.log_group}")
    # Log output is tailed elsewhere by `LogsRetriever` but you can also tail it with:
    # $ aws logs tail <log-group-name> --follow'

    create_worker_files(
        job_id,
        names.bucket,
        settings.file_store,
        settings.blender_archive,
        settings.samples,
        settings.motion_blur
    )

    pack_blend_file(settings.blender, settings.blend_file, PACKED_BLEND_FILE)
    size = sizeof_fmt(os.path.getsize(PACKED_BLEND_FILE))
    print(f"Packed the .blend file to {size} (compressed)")

    bucket = basics.create_bucket(names.bucket)
    upload_worker_files(bucket)

    table = create_db_table(basics, names.dynamodb, settings.frames)

    def clean_up():
        basics.delete_log_group(names.log_group)
        basics.delete_bucket(bucket)
        table.delete()
        print("Deleted log group, bucket and table")
        delete_temporary_files()

    confirm(settings, clean_up)

    instance_ids, availability_zone = create_instances(
        basics,
        settings.instance_count,
        names.worker,
        settings.image_name_pattern,
        settings.image_owner,
        settings.instance_type,
        settings.security_group_name,
        settings.key_name,
        settings.iam_instance_profile,
        USER_DATA
    )
    monitor_and_terminate(
        basics,
        names.log_group,
        settings.instance_type,
        instance_ids,
        availability_zone,
        is_finished=lambda: table.get_remaining() == 0
    )

    count = download_results(basics, job_id, bucket, "frames")
    if count != len(settings.frames):
        print(f"Error: expected {len(settings.frames)} frames but downloaded {count}")

    clean_up()
    print("Job completed")

    # Reassure that there are no unexpected outstanding instances.
    report_non_terminated_instances(basics)


if __name__ == "__main__":
    main()
