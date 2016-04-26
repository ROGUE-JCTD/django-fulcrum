import json
import requests
from django.conf import settings


# post, get, get all, delete
class PzWorkflow:
    def __init__(self, url):
        self.addr = url
        self.map = {'trigger': "/v1/triggers/", 'eventtypes': '/v1/eventtypes/', 'event': "/v1/events/",
                    'alert': "/v1/alerts/"}
        print "Pz object created with url: " + self.addr

    def status(self):
        return requests.get(self.addr, verify=getattr(settings, 'SSL_VERIFY', True)).status_code

    def request(self, user_request):
        user_request = json.loads(user_request)
        if user_request.get('action') == 'post':
            return self.post(user_request)
        elif user_request.get('action') == 'get':
            return self.get(user_request)
        elif user_request.get('action') == 'get_all':
            return self.get_all(user_request)
        elif user_request.get('action') == 'delete':
            return self.delete(user_request)
        else:
            print "Could not find action"
            return None

    @staticmethod
    def find_by_id(items, user_request):
        print "Finding by ID"
        for item in items:
            if item is not None:
                if item.get('id') == user_request.get('data').get('id'):
                    return item
        print "Could not find item"
        return None

    @staticmethod
    def find_by_data(items, user_request):
        print "Finding by data objects"
        for item in items:
            if item is not None:
                un_passed = 0
                key_in_item = False
                for key in user_request.get('data'):
                    if key in item:
                        key_in_item = True
                        if item.get(key) != user_request.get('data').get(key):
                            un_passed -= 1
                if un_passed == 0 and key_in_item is True:
                    return item
        print "Could not find item by keys"
        return None

    def get(self, user_request):
        try:
            items = requests.get(self.addr + self.map.get(user_request.get('type')),
                                 verify=getattr(settings, 'SSL_VERIFY', True))
            items = items.json()
        except ValueError:
            print "Could not get items"
            return None

        if user_request.get('data').get('id'):
            print user_request.get('data').get('id')
            return self.find_by_id(items, user_request)
        else:
            return self.find_by_data(items, user_request)

    def post(self, user_request):
        check = self.get(user_request)
        if not check:
            print "Creating. . ."
            data = json.dumps(user_request.get('data'))
            if user_request.get('type') == 'event':
                eventtype = self.get({'type': 'eventtypes', 'data': {'id': user_request.get('data').get('type')}})
                posted = requests.post(self.addr + self.map.get(user_request.get('type')) + eventtype.get('name'),
                                       data=data,
                                       verify=getattr(settings, 'SSL_VERIFY', True))
            else:
                posted = requests.post(self.addr + self.map.get(user_request.get('type')),
                                       data=data,
                                       verify=getattr(settings, 'SSL_VERIFY', True))
            if posted.status_code == 201:
                print '{} created'.format(user_request.get('type'))
                return posted
            else:
                check = self.get(user_request)
                if not check:
                    print '{} not created with status code: {}'.format(user_request.get('type'), posted.status_code)
                else:
                    print '{} created with status code: {}'.format(user_request.get('type'), posted.status_code)
                return posted
        else:
            print '{} already exists'.format(user_request.get('type'))
            return None

    def get_all(self, user_request):
        return requests.get(self.addr + self.map.get(user_request.get('type')),
                            verify=getattr(settings, 'SSL_VERIFY', True))

    def delete(self, user_request):
        check = self.get(user_request)
        if check:
            print "Deleting"

            if user_request.get('type') == "event":
                deleted_id = requests.delete(self.addr + self.map.get(user_request.get('type')) +
                                             user_request.get('data').get('eventname') + "/" +
                                             user_request.get('data').get('id'),
                                             verify=getattr(settings, 'SSL_VERIFY', True))
            else:
                deleted_id = requests.delete(self.addr + self.map.get(user_request.get('type')) +
                                             user_request.get('data').get('id'),
                                             verify=getattr(settings, 'SSL_VERIFY', True))
            check = self.get(user_request)
            if check:
                print "Delete failed"
                return deleted_id
            else:
                print "Success"
                return deleted_id
        else:
            print "Could not find item to delete"
            return None


# post trigger, get trigger, post event, get event, delete trigger, get alerts
def main():
    pass


if __name__ == "__main__":
    main()
