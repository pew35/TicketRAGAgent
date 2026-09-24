"""Application error code definitions and default messages."""

from enum import IntEnum


class ErrorCode(IntEnum):
    """Stable application response codes grouped by domain."""

    # Success
    SUCCESS = 0

    # Common request and validation errors: 1000-1099
    BAD_REQUEST = 1000
    VALIDATION_ERROR = 1001
    MISSING_REQUIRED_FIELD = 1002
    INVALID_INPUT_FORMAT = 1003
    INVALID_ID_FORMAT = 1004
    UNSUPPORTED_MEDIA_TYPE = 1005
    REQUEST_TOO_LARGE = 1006
    RATE_LIMITED = 1007
    RESOURCE_NOT_FOUND = 1008
    RESOURCE_CONFLICT = 1009
    METHOD_NOT_ALLOWED = 1010

    # Authentication and authorization errors: 1100-1199
    AUTH_REQUIRED = 1100
    INVALID_CREDENTIALS = 1101
    INVALID_TOKEN = 1102
    TOKEN_EXPIRED = 1103
    INVALID_ACCESS_TOKEN = 1104
    INVALID_REFRESH_TOKEN = 1105
    INACTIVE_USER = 1106
    PERMISSION_DENIED = 1107
    SUPERUSER_REQUIRED = 1108
    EMAIL_ALREADY_REGISTERED = 1109
    EMAIL_NOT_VERIFIED = 1110
    PASSWORD_TOO_WEAK = 1111

    # User account errors: 1200-1299
    USER_NOT_FOUND = 1200
    USER_ALREADY_EXISTS = 1201
    USER_CREATE_FAILED = 1202
    USER_UPDATE_FAILED = 1203
    USER_DELETE_FAILED = 1204
    USER_DISABLED = 1205

    # Conversation and message errors: 1300-1399
    CONVERSATION_NOT_FOUND = 1300
    CONVERSATION_CREATE_FAILED = 1301
    CONVERSATION_UPDATE_FAILED = 1302
    CONVERSATION_DELETE_FAILED = 1303
    MESSAGE_NOT_FOUND = 1304
    MESSAGE_CREATE_FAILED = 1305
    MESSAGE_UPDATE_FAILED = 1306
    MESSAGE_DELETE_FAILED = 1307
    MESSAGE_SEQUENCE_CONFLICT = 1308
    EMPTY_MESSAGE = 1309
    TITLE_GENERATION_FAILED = 1310

    # Database and cache errors: 1400-1499
    DATABASE_ERROR = 1400
    DATABASE_CONNECTION_FAILED = 1401
    DATABASE_TRANSACTION_FAILED = 1402
    DATABASE_MIGRATION_FAILED = 1403
    DATABASE_INTEGRITY_ERROR = 1404
    REDIS_ERROR = 1410
    REDIS_CONNECTION_FAILED = 1411
    REDIS_CACHE_MISS = 1412
    REDIS_WRITE_FAILED = 1413

    # External HTTP/service errors: 1500-1599
    EXTERNAL_SERVICE_ERROR = 1500
    EXTERNAL_SERVICE_TIMEOUT = 1501
    EXTERNAL_SERVICE_UNAVAILABLE = 1502
    AGENT_SERVICE_UNAVAILABLE = 1510
    AGENT_SERVICE_TIMEOUT = 1511
    AGENT_SERVICE_BAD_RESPONSE = 1512

    # File and upload errors: 1600-1699
    FILE_NOT_FOUND = 1600
    FILE_UPLOAD_FAILED = 1601
    FILE_READ_FAILED = 1602
    FILE_WRITE_FAILED = 1603
    INVALID_FILE_TYPE = 1604
    FILE_TOO_LARGE = 1605

    # Internal server errors: 1900-1999
    INTERNAL_ERROR = 1900
    CONFIGURATION_ERROR = 1901
    LOGGING_CONFIGURATION_ERROR = 1902
    UNKNOWN_ERROR = 1999

    # Agent/RAG errors: 2000-2099
    AGENT_ERROR = 2000
    AGENT_INVALID_QUESTION = 2001
    AGENT_EMBEDDING_FAILED = 2002
    AGENT_SEARCH_FAILED = 2003
    AGENT_NO_RESULTS = 2004
    AGENT_CONTEXT_BUILD_FAILED = 2005
    AGENT_GENERATION_FAILED = 2006
    AGENT_STREAM_FAILED = 2007
    AGENT_MODEL_UNAVAILABLE = 2008
    AGENT_VECTOR_DB_UNAVAILABLE = 2009
    AGENT_RESPONSE_PARSE_FAILED = 2010


ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.SUCCESS: "Success.",
    ErrorCode.BAD_REQUEST: "The request is invalid.",
    ErrorCode.VALIDATION_ERROR: "Request validation failed.",
    ErrorCode.MISSING_REQUIRED_FIELD: "A required field is missing.",
    ErrorCode.INVALID_INPUT_FORMAT: "The input format is invalid.",
    ErrorCode.INVALID_ID_FORMAT: "The id format is invalid.",
    ErrorCode.UNSUPPORTED_MEDIA_TYPE: "The media type is not supported.",
    ErrorCode.REQUEST_TOO_LARGE: "The request is too large.",
    ErrorCode.RATE_LIMITED: "Too many requests.",
    ErrorCode.RESOURCE_NOT_FOUND: "The requested resource was not found.",
    ErrorCode.RESOURCE_CONFLICT: "The resource already exists or conflicts.",
    ErrorCode.METHOD_NOT_ALLOWED: "The HTTP method is not allowed.",
    ErrorCode.AUTH_REQUIRED: "Authentication is required.",
    ErrorCode.INVALID_CREDENTIALS: "Invalid email or password.",
    ErrorCode.INVALID_TOKEN: "Invalid authentication token.",
    ErrorCode.TOKEN_EXPIRED: "Authentication token has expired.",
    ErrorCode.INVALID_ACCESS_TOKEN: "Invalid access token.",
    ErrorCode.INVALID_REFRESH_TOKEN: "Invalid refresh token.",
    ErrorCode.INACTIVE_USER: "The user account is inactive.",
    ErrorCode.PERMISSION_DENIED: "Permission denied.",
    ErrorCode.SUPERUSER_REQUIRED: "Superuser permission is required.",
    ErrorCode.EMAIL_ALREADY_REGISTERED: "Email is already registered.",
    ErrorCode.EMAIL_NOT_VERIFIED: "Email address has not been verified.",
    ErrorCode.PASSWORD_TOO_WEAK: "Password does not meet security requirements.",
    ErrorCode.USER_NOT_FOUND: "User was not found.",
    ErrorCode.USER_ALREADY_EXISTS: "User already exists.",
    ErrorCode.USER_CREATE_FAILED: "Failed to create user.",
    ErrorCode.USER_UPDATE_FAILED: "Failed to update user.",
    ErrorCode.USER_DELETE_FAILED: "Failed to delete user.",
    ErrorCode.USER_DISABLED: "User account is disabled.",
    ErrorCode.CONVERSATION_NOT_FOUND: "Conversation was not found.",
    ErrorCode.CONVERSATION_CREATE_FAILED: "Failed to create conversation.",
    ErrorCode.CONVERSATION_UPDATE_FAILED: "Failed to update conversation.",
    ErrorCode.CONVERSATION_DELETE_FAILED: "Failed to delete conversation.",
    ErrorCode.MESSAGE_NOT_FOUND: "Message was not found.",
    ErrorCode.MESSAGE_CREATE_FAILED: "Failed to create message.",
    ErrorCode.MESSAGE_UPDATE_FAILED: "Failed to update message.",
    ErrorCode.MESSAGE_DELETE_FAILED: "Failed to delete message.",
    ErrorCode.MESSAGE_SEQUENCE_CONFLICT: "Message sequence already exists.",
    ErrorCode.EMPTY_MESSAGE: "Message content cannot be empty.",
    ErrorCode.TITLE_GENERATION_FAILED: "Failed to generate conversation title.",
    ErrorCode.DATABASE_ERROR: "Database operation failed.",
    ErrorCode.DATABASE_CONNECTION_FAILED: "Database connection failed.",
    ErrorCode.DATABASE_TRANSACTION_FAILED: "Database transaction failed.",
    ErrorCode.DATABASE_MIGRATION_FAILED: "Database migration failed.",
    ErrorCode.DATABASE_INTEGRITY_ERROR: "Database integrity constraint failed.",
    ErrorCode.REDIS_ERROR: "Redis operation failed.",
    ErrorCode.REDIS_CONNECTION_FAILED: "Redis connection failed.",
    ErrorCode.REDIS_CACHE_MISS: "Redis cache entry was not found.",
    ErrorCode.REDIS_WRITE_FAILED: "Failed to write data to Redis.",
    ErrorCode.EXTERNAL_SERVICE_ERROR: "External service request failed.",
    ErrorCode.EXTERNAL_SERVICE_TIMEOUT: "External service request timed out.",
    ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE: "External service is unavailable.",
    ErrorCode.AGENT_SERVICE_UNAVAILABLE: "Agent service is unavailable.",
    ErrorCode.AGENT_SERVICE_TIMEOUT: "Agent service request timed out.",
    ErrorCode.AGENT_SERVICE_BAD_RESPONSE: "Agent service returned an invalid response.",
    ErrorCode.FILE_NOT_FOUND: "File was not found.",
    ErrorCode.FILE_UPLOAD_FAILED: "Failed to upload file.",
    ErrorCode.FILE_READ_FAILED: "Failed to read file.",
    ErrorCode.FILE_WRITE_FAILED: "Failed to write file.",
    ErrorCode.INVALID_FILE_TYPE: "File type is not supported.",
    ErrorCode.FILE_TOO_LARGE: "File is too large.",
    ErrorCode.INTERNAL_ERROR: "Internal server error.",
    ErrorCode.CONFIGURATION_ERROR: "Server configuration error.",
    ErrorCode.LOGGING_CONFIGURATION_ERROR: "Logging configuration error.",
    ErrorCode.UNKNOWN_ERROR: "Unknown error.",
    ErrorCode.AGENT_ERROR: "Agent request failed.",
    ErrorCode.AGENT_INVALID_QUESTION: "Agent question is invalid.",
    ErrorCode.AGENT_EMBEDDING_FAILED: "Agent failed to create question embedding.",
    ErrorCode.AGENT_SEARCH_FAILED: "Agent failed to search knowledge base.",
    ErrorCode.AGENT_NO_RESULTS: "Agent could not find relevant knowledge base results.",
    ErrorCode.AGENT_CONTEXT_BUILD_FAILED: "Agent failed to build prompt context.",
    ErrorCode.AGENT_GENERATION_FAILED: "Agent failed to generate an answer.",
    ErrorCode.AGENT_STREAM_FAILED: "Agent failed while streaming the answer.",
    ErrorCode.AGENT_MODEL_UNAVAILABLE: "Agent model is unavailable.",
    ErrorCode.AGENT_VECTOR_DB_UNAVAILABLE: "Agent vector database is unavailable.",
    ErrorCode.AGENT_RESPONSE_PARSE_FAILED: "Agent response parsing failed.",
}


def get_error_message(code: ErrorCode | int) -> str:
    """Return the default message for an application error code."""
    try:
        error_code = ErrorCode(code)
    except ValueError:
        return ERROR_MESSAGES[ErrorCode.UNKNOWN_ERROR]

    return ERROR_MESSAGES.get(error_code, ERROR_MESSAGES[ErrorCode.UNKNOWN_ERROR])

