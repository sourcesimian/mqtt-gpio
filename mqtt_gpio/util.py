import hashlib
import json


def blob_hash(blob):
    if not blob:
        return None
    md5 = hashlib.md5()
    md5.update(json.dumps(blob, sort_keys=True).encode())
    return md5.hexdigest()
