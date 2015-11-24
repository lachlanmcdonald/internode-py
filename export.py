import errno
from json import dumps
from os import path, makedirs
from internode import Account
from datetime import datetime

USERNAME = "username"
PASSWORD = "password"
EXPORT_DIRECTORY = "data"


def timestamp():
    return str(datetime.utcnow().isoformat())


if __name__ == "__main__":

    # Check if data directory exists
    try:
        makedirs(EXPORT_DIRECTORY)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

    # Create a new account instance
    account = Account(USERNAME, PASSWORD)

    # Get services for the account
    services = account.get_services()

    # Prettify JSON output, making it more
    # human-readable
    json_kwargs = {
        "sort_keys": True,
        "indent": 4,
        "separators": (',', ': ')
    }

    # Write-out list of services to JSON file
    with open(path.join(EXPORT_DIRECTORY, 'account.json'), 'wb') as f:
        output = {}
        for service_id in services.keys():
            output[service_id] = "%s/%s.json" % (EXPORT_DIRECTORY, service_id)

        data = {
            "generated": timestamp(),
            "services": output
        }
        f.write(dumps(data, **json_kwargs))

    # Write out each service as its own JSON file
    for id in services:
        service = services[id]
        with open(path.join(EXPORT_DIRECTORY, '%s.json' % id), 'wb') as f:
            f.write(dumps(service.dump(), **json_kwargs))
