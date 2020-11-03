import collections
import datetime
import json

import pytz
from graia.broadcast import Broadcast
from graia.application import GraiaMiraiApplication, Session, Group, Member
from graia.application.message.chain import MessageChain
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

from graia.application.message.elements.internal import Plain
from graia.application.friend import Friend

from bigfun import BigFun
from configs import GroupTokens, MIRAI_QQ, MIRAI_KEY

tz = pytz.timezone("Asia/Shanghai")


def convert_ts(timestamp, fmt="%H:%M:%S"):
    return datetime.datetime.fromtimestamp(
        timestamp, tz=tz
    ).strftime(fmt)


class Bot:
    bcc: Broadcast
    mirai: GraiaMiraiApplication

    token_client = {}
    token_group = collections.defaultdict(list)

    def __init__(self, account, key):
        self.loop = asyncio.get_event_loop()
        self.bcc = Broadcast(loop=self.loop)
        self.scheduler = AsyncIOScheduler()
        self.mirai = GraiaMiraiApplication(
            broadcast=self.bcc,
            connect_info=Session(
                host="http://localhost:8080",
                authKey=key,
                account=account,
                websocket=True
            )
        )

    def init(self):
        self.scheduler.start()

        @self.bcc.receiver("ApplicationLaunched")
        async def init(app: GraiaMiraiApplication):
            for group in await app.groupList():
                if group.id in GroupTokens:
                    t = GroupTokens[group.id]
                    self.token_client[t] = BigFun(t)
                    self.token_group[t].append(group)

        @self.bcc.receiver("GroupMessage")
        async def group_message_handler(
            app: GraiaMiraiApplication, message: MessageChain, group: Group, member: Member
        ):
            if message.asDisplay().startswith("对刀"):
                if group.id in GroupTokens:
                    t = GroupTokens[group.id]
                    bf = self.token_client[t]
                    data = bf.fetch_clan_status()
                    day_report = bf.fetch_day_report()

                    total_number = sum([x['number'] for x in day_report])
                    est_number = len(day_report) * 3

                    msg = "今日出刀 (%s/%s)" % (
                        total_number, est_number
                    )
                    for row in day_report:
                        msg += "\n({}) {} [{:,}]".format(
                            row['number'], row['name'], row['damage']
                        )

                    x = [Plain("%s #%d\n进度：L%d-%s (%d/%d)\n" % (
                        data['clan_info']['name'],
                        data['clan_info']['last_ranking'],
                        data['boss_info']['lap_num'],
                        data['boss_info']['name'],
                        data['boss_info']['current_life'],
                        data['boss_info']['total_life'],
                    )), Plain(msg)]

                    await app.sendGroupMessage(group, MessageChain(__root__=x))
            if message.asDisplay().startswith("进度"):
                if group.id in GroupTokens:
                    t = GroupTokens[group.id]
                    bf = self.token_client[t]
                    data = bf.fetch_clan_status()
                    day_report = bf.fetch_day_report()

                    total_number = sum([x['number'] for x in day_report])
                    est_number = len(day_report) * 3

                    msg = "今日出刀 (%s/%s)" % (
                        total_number, est_number
                    )

                    x = [Plain("%s #%d\n进度：L%d-%s (%d/%d)\n" % (
                        data['clan_info']['name'],
                        data['clan_info']['last_ranking'],
                        data['boss_info']['lap_num'],
                        data['boss_info']['name'],
                        data['boss_info']['current_life'],
                        data['boss_info']['total_life'],
                    )), Plain(msg)]

                    await app.sendGroupMessage(group, MessageChain(__root__=x))

        @self.scheduler.scheduled_job('interval', seconds=120)
        async def fetch_battle_log():
            for t in self.token_client:
                bf: BigFun = self.token_client[t]
                data = bf.fetch_incremental_battle_data()
                if len(data):
                    msg = []
                    if len(data) >= 1:
                        msg.append(Plain("获取到 %d 条出刀记录：" % len(data)))
                    for row in data[-10:]:
                        msg.append(Plain("\n%s %d-%s %s %s%s" % (
                            convert_ts(row["datetime"]), row["lap_num"], row["boss_id"][-1],
                            "{:,}".format(row["damage"]), row["name"],
                            "(R)" if row["reimburse"] else "(K)" if row["kill"] else ""
                        )))
                    for group in self.token_group[t]:
                        await self.mirai.sendGroupMessage(group, MessageChain(__root__=msg))

        @self.scheduler.scheduled_job('cron', minute="8,38")
        async def fetch_position():
            for t in self.token_client:
                bf: BigFun = self.token_client[t]
                data = bf.fetch_clan_status()
                day_report = bf.fetch_day_report()

                total_number = sum([x['number'] for x in day_report])
                est_number = len(day_report) * 3

                msg = [Plain("%s #%d\n进度：L%d-%s (%d/%d)\n出刀 %s/%d" % (
                    data['clan_info']['name'],
                    data['clan_info']['last_ranking'],
                    data['boss_info']['lap_num'],
                    data['boss_info']['name'],
                    data['boss_info']['current_life'],
                    data['boss_info']['total_life'],
                    total_number, est_number
                ))]
                for group in self.token_group[t]:
                    await self.mirai.sendGroupMessage(group, MessageChain(__root__=msg))

    def launch(self):
        self.mirai.launch_blocking()


if __name__ == '__main__':
    bot = Bot(MIRAI_QQ, MIRAI_KEY)
    bot.init()
    bot.launch()
