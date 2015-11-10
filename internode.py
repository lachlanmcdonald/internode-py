import settings
import requests
import errno
from xml.etree import ElementTree
from datetime import datetime
from json import dumps
from os import path, makedirs


def timestamp():
    return str(datetime.utcnow().isoformat())


class Api:
    host = "https://customer-webtools-api.internode.on.net/api/v1.5"

    def __init__(self, username, password):
        self.auth = (username, password)

    def get(self, url=""):
        url = "%s/%s" % (self.host, url)

        response = requests.get(url, auth=self.auth)

        # It is possible for the server to return a 500 error,
        # but still respond with a valid body.
        assert response.status_code != 401, "Request failed. Authorisation was missing or invalid."
        return ElementTree.fromstring(response.content)


class Account:
    services = {}

    def __init__(self, username, password):
        self.api = Api(username, password)
        self.get_services()

    def get_services(self):
        tree = self.api.get()
        services_tree = tree.find('api/services')
        assert services_tree is not None, "XML was not as expected"
        assert int(services_tree.get('count')) > 0, "There are no services for this account"

        self.services = {}
        for i in services_tree:
            self.services[i.text] = Service(int(i.text), self.api)


class Service:
    def __init__(self, id, api):
        self.id = id
        self.api = api
        self.get_service()
        self.get_history()
        self.get_usage()

    def get_service(self):
        tree = self.api.get('/api/v1.5/api/v1.5/%s/service' % self.id)
        service_tree = tree.find('api/service')
        assert service_tree is not None, "XML was not as expected"

        self.service = {}
        for i in service_tree:
            self.service[i.tag] = i.text

        # Convert to bool where appropriate
        if "excess-charged" in self.service:
            self.service["excess-charged"] = self.service["excess-charged"] == 'yes'
        if "excess-restrict-access" in self.service:
            self.service["excess-restrict-access"] = self.service["excess-restrict-access"] == 'yes'
        if "excess-shaped" in self.service:
            self.service["excess-shaped"] = self.service["excess-shaped"] == 'yes'

        # Convert to int where appropriate
        if "id" in self.service:
            self.service["id"] = int(self.service["id"])
        if "quota" in self.service:
            self.service["quota"] = int(self.service["quota"])

    def get_history(self):
        tree = self.api.get('/api/v1.5/api/v1.5/%s/history' % self.id)
        history_tree = tree.find('api/usagelist')
        assert history_tree is not None, "Response was not as expected and can not be processed further."

        self.history = {}
        for i in history_tree:
            self.history[i.get('day')] = int(i[0].text)

    def get_usage(self):
        tree = self.api.get('/api/v1.5/api/v1.5/%s/usage' % self.id)
        traffic_tree = tree.find('api/traffic')
        assert traffic_tree is not None, "Response was not as expected and can not be processed further."

        self.usage = {}
        for i in ['name', 'plan-interval', 'rollover', 'unit']:
            self.usage[i] = traffic_tree.get(i)

        self.usage['quota'] = int(traffic_tree.get('quota'))
        self.usage['usage'] = int(traffic_tree.text)

    def dump(self):
        return {
            "generated": timestamp(),
            "service": self.service,
            "history": self.history,
            "usage": self.usage
        }


if __name__ == "__main__":

    # Check if data directory exists
    try:
        makedirs(settings.EXPORT_DIRECTORY)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

    # Create a new account instance
    account = Account(settings.USERNAME, settings.PASSWORD)

    # Prettify JSON output, making it more
    # human-readable
    json_kwargs = {
        "sort_keys": True,
        "indent": 4,
        "separators": (',', ': ')
    }

    # Write-out list of services to JSON file
    with open(path.join(settings.EXPORT_DIRECTORY, 'account.json'), 'wb') as f:
        services = {}
        for i in account.services.keys():
            services[i] = "%s/%s.json" % (settings.EXPORT_DIRECTORY, i)

        data = {
            "generated": timestamp(),
            "services": services
        }
        f.write(dumps(data, **json_kwargs))

    # Write out each service as its own JSON fi;e
    for id in account.services:
        service = account.services[id]
        with open(path.join(settings.EXPORT_DIRECTORY, '%s.json' % id), 'wb') as f:
            f.write(dumps(service.dump(), **json_kwargs))
