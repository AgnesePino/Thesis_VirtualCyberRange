import requests
from checklib import *

PORT = 8080


class CheckMachine:

    def __init__(self, checker):
        self.checker = checker

    def ping(self):
        r = requests.get(f'http://{self.checker.host}:8080', timeout=2)
        self.checker.check_response(r, 'Check failed')
        
    def put_flag(self, flag, vuln):
        note_data={}
        note_data['title']= rnd_string(4)
        note_data['content']=flag
        resp = requests.post(f'http://{self.checker.host}:8080/new', data=note_data)
        if resp.status_code != 200:
            f'Bad, it doesn t work: {resp.status_code}'
            return

        parts= resp.url.split('/view/')
        if len(parts) != 2:
            print("Invalid note")
            return
        try:
            return int(parts[1])
        except ValueError:
            print("ERROR")

        self.checker.check_response(resp, 'Could not put flag')

        return new_id

    def get_flag(self, flag_id, vuln):
        r = requests.get(
            f'http://{self.checker.host}:8080/view/{flag_id}',
            timeout=2,
        )
        self.checker.check_response(r, 'Could not get flag')
        data = self.checker.get_json(r, 'Invalid response from /get/')
        self.checker.assert_in(
            'content', data,
            'Could not get flag',
            status=Status.CORRUPT,
        )
        return data['content']
