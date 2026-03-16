class TransientGSCError(Exception):
    """Exception for transient GSC errors (e.g., 429, 500, 503)"""
    pass

class PermanentGSCError(Exception):
    """Exception for permanent GSC errors (e.g., 400, 401, 403, 404)"""
    pass

class UnsupportedContextVersionError(Exception):
    """Exception for unsupported context versions"""
    pass
