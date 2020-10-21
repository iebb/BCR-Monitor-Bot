import datetime
import json
import os

import pytz
import requests


class BigFun:
    s = requests.Session()
    user_id = 0
    session = ""
    clan_info = {}
    last_report = 0

    def save(self):
        json.dump({
            'last_report': self.last_report,
        }, open("data/%d/config.json" % self.user_id, "w+"), indent=2, ensure_ascii=False)

    def load(self):
        try:
            data = json.load(open("data/%d/config.json" % self.user_id))
            self.last_report = data['last_report']
        except:
            pass

    def api(self, target, params):
        url = "https://www.bigfun.cn/api/feweb"
        params['target'] = target
        return self.s.get(url, params=params, headers={
            'Cookie': 'session-api=%s' % self.session
        }).json()

    def __init__(self, session):
        self.session = session
        print(session)
        user_info = self.api('get-gzlj-user-info/a', {})
        print(user_info)
        if 'data' not in user_info:
            print("error", session)
        self.user_info = user_info['data']
        self.user_id = user_info['data']['player_id']
        self.clan_info = self.api('gzlj-clan-day-report-collect/a', {})['data']
        os.makedirs("data/%d" % self.user_id, exist_ok=True)
        self.load()

    def fetch_clan_status(self):
        self.clan_info = self.api('gzlj-clan-day-report-collect/a', {})['data']
        return self.clan_info

    def fetch_day_report(self, date=None):
        params = {'size': 35}
        if date:
            params['date'] = self.clan_info['day_list'][0]
        return self.api('gzlj-clan-day-report/a', params)['data']

    def fetch_battle_data(self):
        all_data = []
        rc = self.api('gzlj-clan-boss-report-collect/a', {})
        for boss in rc['data']['boss_list']:
            boss_id = boss['id']
            br = self.api('gzlj-clan-boss-report/a', {'boss_id': boss_id})
            for k in br['data']:
                k['boss_name'] = boss['boss_name']
                k['boss_id'] = boss['id']
                all_data.append(k)

        all_data.sort(key=lambda x: x['datetime'])
        json.dump(all_data, open("data/%d/boss_data.json" % self.user_id, "w+"), indent=2, ensure_ascii=False)
        return all_data

    def fetch_incremental_battle_data(self):
        all_data = self.fetch_battle_data()
        data = list(filter(lambda x: x['datetime'] > self.last_report, all_data))
        if len(data):
            self.last_report = data[-1]['datetime']
            self.save()
        return data


if __name__ == '__main__':
    API = BigFun("svbbhlkd9qs964190dvuingahd")
    print(API.fetch_clan_status())
