"""
Always sync destination directory to match the source directory
==========================

1. If a file exists in the source but not in the destination, copy the file over
2. If a file exists in the source, but it has a different name than in the destination, rename the destination file to match
3. If a file exists in the destination but not in the source, remove it.
"""

import hashlib
import os
import shutil
from pathlib import Path

BLOCKSIZE = 65536


def hash_file(path):
    hasher = hashlib.sha1()
    with path.open("rb") as file:
        buf = file.read(BLOCKSIZE)
        while buf:
            hasher.update(buf)
            buf = file.read(BLOCKSIZE)
    return hasher.hexdigest()


def read_paths_and_hashes(root):
    hashes = {}
    for folder, _, files in os.walk(root):
        for fn in files:
            hashes[hash_file(Path(folder) / fn)] = fn
    return hashes


def determine_actions(src_hashes, dst_hashes, src_folder, dst_folder):
    for sha, filename in src_hashes.items():
        # If the file does not exist
        if sha not in dst_hashes:
            sourcepath = Path(src_folder) / filename
            destpath = Path(dst_folder) / filename
            yield "copy", sourcepath, destpath
        # If it has a different name
        elif dst_hashes[sha] != filename:
            origpath = Path(dst_folder) / dst_hashes[sha]
            newpath = Path(dst_folder) / filename
            yield "move", origpath, newpath
    # If an item exists in destination folder but not in the source folder, delete it
    for sha, filename in dst_hashes.items():
        if sha not in src_hashes:
            yield "delete", Path(dst_folder) / filename


def sync(source, dest):
    # imperative shell step 1, gather inputs
    source_hashes = read_paths_and_hashes(source)
    dest_hashes = read_paths_and_hashes(dest)

    # step 2: call functional core
    actions = determine_actions(source_hashes, dest_hashes, source, dest)

    # imperative shell step 3, apply outputs
    for action, *paths in actions:
        if action == "copy":
            shutil.copyfile(*paths)
        if action == "move":
            shutil.move(*paths)
        if action == "delete":
            os.remove(paths[0])
