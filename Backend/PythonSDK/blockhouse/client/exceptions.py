class BlockhouseError(Exception):
    """Base class for exceptions in the Blockhouse SDK."""

    pass


class S3UploadError(BlockhouseError):
    """Exception raised for errors during S3 upload."""

    pass
