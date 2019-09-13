# Storage exceptions
class StorageException(Exception):
    pass


class MultipleItemsFound(StorageException):
    """
    Multiple items in table
    """


class TableNotFound(StorageException):
    pass


class UnauthorizedStateChangeRequest(StorageException):
    """
    Raised when an update request has changes in private attrs
    """


class ItemNotFound(StorageException):
    """
    Item not in table
    """


class NoIdInPayload(StorageException):
    """
    ID not in arguments
    """


class BadUserId(StorageException):
    pass


class RepositoryException(Exception):
    pass


class BadParameters(RepositoryException):
    """Bad arguments to function"""
    pass


class MissingRequiredKey(RepositoryException):
    """If a required key-val pair is missing in POST request"""
    pass


class UnsupportedMediaType(RepositoryException):
    """If where a PNG or other media has to be uploaded, but the data is non decodable or has different media type"""
    pass


class NoSuchEntity(RepositoryException):
    pass


class InvalidNewEntity(RepositoryException):
    pass


class UserNotAvailable(RepositoryException):
    pass


class CannotModifyEntityStates(RepositoryException):
    pass


class Auth0Exception(Exception):
    pass


class Auth0UnableToAccess(Auth0Exception):
    pass


class Auth0AccessDenied(Auth0Exception):
    pass


class Auth0UnknownError(Auth0Exception):
    pass


class SupplierException(Exception):
    pass


class UnknownMainContact(SupplierException):
    pass


class NotAnAdminUser(SupplierException):
    pass


class CannotUpdateUsers(SupplierException):
    pass


class AuroraException(Exception):
    pass


class AuroraSchemaNotFound(AuroraException):
    pass


class AuroraSqlExecuteFailed(AuroraException):
    pass


class AuroraPrimaryKeySignatureMismatch(AuroraException):
    pass


class AuroraConnectionLinkFailure(AuroraException):
    pass


class AquireProjectionLockError(AuroraException):
    pass

class SqsException(Exception):
    pass


class UserIdNotInObject(SqsException):
    pass

