import os
import mimetypes
import io
from PIL import Image

def s3_replace(key: str) -> str:
    return key.replace('\\', '/')

def join_s3(*parts) -> str:
    return s3_replace(os.path.join(*parts))

def is_image(mt: str) -> bool:
    return bool(mt and mt.startswith('image/'))

def delete_prefix(uploader, prefix: str):
    c = uploader.get_s3_client()
    b = uploader.bucket_name
    pfx = prefix if prefix.endswith('/') else prefix + '/'
    paginator = c.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=b, Prefix=pfx):
        objs = [{'Key': obj['Key']} for obj in page.get('Contents', [])]
        if objs:
            c.delete_objects(Bucket=b, Delete={'Objects': objs})

def delete_matching_uuid(uploader, base_prefix: str, uuid_str: str):
    c = uploader.get_s3_client()
    b = uploader.bucket_name
    pfx = base_prefix if base_prefix.endswith('/') else base_prefix + '/'
    paginator = c.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=b, Prefix=pfx):
        todel = []
        for obj in page.get('Contents', []):
            key = obj['Key']
            if uuid_str in key:
                todel.append({'Key': key})
        if todel:
            c.delete_objects(Bucket=b, Delete={'Objects': todel})
