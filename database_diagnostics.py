"""Safe deployment diagnostics: never return raw exceptions or connection strings."""
from pymongo.errors import ConfigurationError, OperationFailure, ServerSelectionTimeoutError


def diagnose(database, error):
    if database == 'mysql':
        number = getattr(error, 'errno', None)
        if number in (1044, 1045, 1698):
            return {'code': 'mysql_credentials', 'message': 'Check the hosted MySQL username, password and database access permissions.'}
        if number == 1049:
            return {'code': 'mysql_database_missing', 'message': 'MYSQL_DATABASE does not exist on the hosted server. Create/import that database or use its actual name.'}
        if number in (2026, 3159):
            return {'code': 'mysql_tls', 'message': 'The MySQL connection requires valid TLS settings. Check the database provider requirements.'}
        if number in (2002, 2003, 2005, 2013):
            return {'code': 'mysql_network', 'message': 'Check MYSQL_HOST, MYSQL_PORT, database service state and network access rules.'}
        if isinstance(error, (ValueError, TypeError)):
            return {'code': 'mysql_configuration', 'message': 'Check MySQL environment variables; MYSQL_PORT must be a number.'}
        return {'code': 'mysql_connection', 'message': 'MySQL connection failed. Check hosted database settings in Render.'}

    if isinstance(error, OperationFailure):
        return {'code': 'mongodb_credentials', 'message': 'Check the MongoDB database-user credentials and permissions, not the Atlas website login.'}
    if isinstance(error, ConfigurationError):
        return {'code': 'mongodb_uri', 'message': 'Check the complete Atlas connection string, cluster hostname, placeholder replacement and password URL encoding.'}
    if isinstance(error, ServerSelectionTimeoutError):
        # Inspect text only for classification; never expose or log its contents.
        if 'certificate_verify_failed' in str(error).lower():
            return {'code': 'mongodb_tls', 'message': 'MongoDB TLS certificate verification failed. Check the cluster certificate chain.'}
        return {'code': 'mongodb_network', 'message': 'Check Atlas cluster state and Network Access: allow all outbound IP ranges listed by your Render service.'}
    return {'code': 'mongodb_connection', 'message': 'MongoDB connection failed. Check MONGO_URI and Atlas connectivity.'}
