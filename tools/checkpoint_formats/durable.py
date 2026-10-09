"""Atomic, durable local publication for Level-1 containers and staging.

The caller validates state before entering atomic_output. A successful return
means both file contents and the replacement directory entry were fsynced.
Interrupted writers may leave private .pending files; readers only use the
requested destination. No automatic recovery or deletion of other writers'
files is performed.
"""
from contextlib import contextmanager
import errno
import os
from pathlib import Path
import secrets
import stat
import sys


class PublicationError(OSError):
    """Publication failed; published marks a complete but unconfirmed rename."""

    def __init__(self, destination, published, cause):
        self.destination = str(destination)
        self.published = published
        state = 'complete replacement visible; directory durability unconfirmed' if published else 'destination unchanged'
        super().__init__(cause.errno, f'checkpoint publication failed ({state}): {cause}', str(destination))


@contextmanager
def atomic_output(destination, *, binary=False):
    """Write privately in the pinned destination directory, then replace it.

    Existing regular files are replaced atomically. Symlinks and special files
    reject. Each writer has an exclusive mode-0600 temporary file; concurrent
    publications expose complete files, with the last rename winning. Readers
    must open once and validate that file, rather than repeatedly reopen it.
    """
    destination = Path(destination)
    try:
        directory = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    except OSError as error:
        raise PublicationError(destination, False, error) from error
    temporary = None
    stream = None
    published = False
    try:
        try:
            existing = os.stat(destination.name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None and not stat.S_ISREG(existing.st_mode):
            raise OSError(errno.EINVAL, 'checkpoint destination must be a regular file')
        # Reject a filesystem without directory-sync support before publication.
        os.fsync(directory)
        name = f'.{destination.name}.pending-{secrets.token_hex(16)}'
        descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                             0o600, dir_fd=directory)
        temporary = name
        try:
            stream = os.fdopen(descriptor, 'wb' if binary else 'w',
                               **({} if binary else dict(encoding='ascii', newline='\n')))
        except BaseException:
            os.close(descriptor)
            raise
        yield stream
        stream.flush()
        os.fsync(stream.fileno())
        stream.close()
        os.replace(temporary, destination.name, src_dir_fd=directory, dst_dir_fd=directory)
        published = True
        temporary = None
        os.fsync(directory)
    except OSError as error:
        raise PublicationError(destination, published, error) from error
    finally:
        # A second flush/cleanup failure must not hide the original I/O failure
        # or its publication status (notably ENOSPC during buffered flush).
        active_error = sys.exc_info()[0] is not None
        cleanup_error = None
        if stream is not None and not stream.closed:
            try:
                stream.close()
            except OSError as error:
                cleanup_error = error
        if temporary is not None:
            try:
                os.unlink(temporary, dir_fd=directory)
            except OSError as error:
                cleanup_error = cleanup_error or error
        try:
            os.close(directory)
        except OSError as error:
            cleanup_error = cleanup_error or error
        if cleanup_error is not None and not active_error:
            raise PublicationError(destination, published, cleanup_error) from cleanup_error
