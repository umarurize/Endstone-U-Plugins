import json
import os
import time
import random
from endstone.plugin import Plugin
from endstone.scoreboard import Criteria
from endstone import ColorFormat, Player
from endstone.event import event_handler, PlayerJoinEvent, PlayerQuitEvent, PlayerChatEvent
from endstone.command import Command, CommandSender
from endstone.form import ActionForm, Dropdown, TextInput, ModalForm
from endstone.boss import BarColor, BarStyle


current_dir = os.getcwd()
first_dir = os.path.join(current_dir, 'plugins', 'u-red-packets')
player_file_path = os.path.join(first_dir, 'player.data')
config_file_path = os.path.join(first_dir, 'config.data')
money_file_path = os.path.join(current_dir, 'plugins', 'money', 'money.json')
try:
    os.mkdir(first_dir)
except:
    pass

class u_red_packets(Plugin):
    api_version = '0.5'

    commands = {
        'red': {
            'description': '打开发红包主表单',
            'usages': ['/red'],
            'permissions': ['u_red_packets.command.red']
        }
    }

    permissions = {
        'u_red_packets.command.red': {
            'description': '打开发红包主表单',
            'default': True
        }
    }

    def on_enable(self):
        self.send_group_money_flag = False
        self.on_send_group_money = []
        self.task = None
        # 尝试加载配置文件
        try:
            f = open(config_file_path, 'r', encoding='utf-8')
            config = eval(f.read())
            f.close()
            self.logger.info(f'{ColorFormat.YELLOW}config.data 加载成功...')
        except:
            f = open(config_file_path, 'w', encoding='utf-8')
            default_config = {'economy': 'scoreboard', 'objective': 'money', 'default_money': 1000, 'max_time_out': 120}
            config = default_config
            f.write(str(default_config))
            f.close()
            self.logger.info(f'{ColorFormat.YELLOW}config.data 已生成，位置：{player_file_path}')
        self.config_data = config
        # 尝试加载经济系统
        if self.config_data['economy'] == 'scoreboard':
            self.money_objective = self.initial_money_objective()
            self.logger.info(f'{ColorFormat.YELLOW}u-red-packets 已启用，经济系统：scoreboard...')
        else:
            self.jsonmoney_data = {}
            self.logger.info(f'{ColorFormat.YELLOW}u-red-packets 已启用，经济系统：jsonmoney...')
        # 注册 event
        self.register_events(self)

    def initial_money_objective(self):
        money_objective = self.server.scoreboard.get_objective(self.config_data['objective'])
        if not money_objective:
            money_objective = self.server.scoreboard.add_objective(
                self.config_data['objective'],
                Criteria.Type.DUMMY,
                display_name='金币'
            )
            self.logger.info(f'{ColorFormat.YELLOW}默认计分板 money 已创建...')
        return money_objective

    def reload_config_data(self, p: Player):
        if p.is_op == False:
            p.send_message(f'{ColorFormat.RED}你没有权限执行此操作...')
            return
        else:
            f = open(config_file_path, 'r', encoding='utf-8')
            config = eval(f.read())
            f.close()
            self.config_data = config
            if self.config_data['economy'] == 'scoreboard':
                self.money_objective = self.initial_money_objective()
                for player in self.server.online_players:
                    if self.money_objective.get_score(player).is_score_set == False:
                        self.money_objective.get_score(player).value = self.config_data['default_money']
                        player.send_message(f'经济系统已更换为计分板/计分板已更换，没有检测到你的分数记录，已发放{ColorFormat.GREEN}{self.config_data['default_money']}{ColorFormat.WHITE}金币')
            else:
                self.load_jsonmoney_data()
                for player in self.server.online_players:
                    if not self.jsonmoney_data.get(player.name):
                        self.jsonmoney_data[player.name] = self.config_data['default_money']
                        player.send_message(f'经济系统已更换为 jsonmoney，没有检测到你的账户余额，已发放{ColorFormat.GREEN}{self.config_data['default_money']}{ColorFormat.WHITE}金币')
                self.save_jsonmoney_data()
            p.send_message('config.data 已重载...')

    def load_jsonmoney_data(self):
        f = open(money_file_path, 'r', encoding='utf-8')
        dict = json.loads(f.read())
        self.jsonmoney_data = dict
        f.close()

    def save_jsonmoney_data(self):
        f = open(money_file_path, 'w+', encoding='utf-8')
        json_str = json.dumps(self.jsonmoney_data, indent=4)
        f.write(json_str)
        f.close()

    @event_handler
    def on_player_join(self, event: PlayerJoinEvent):
        if self.config_data['economy'] == 'scoreboard':
            if self.money_objective.get_score(event.player).is_score_set == False:
                self.money_objective.get_score(event.player).value = self.config_data['default_money']
                event.player.send_message(f'经济系统：计分板，没有检测到你的分数记录，已为你发放{ColorFormat.GREEN}{self.config_data['default_money']}{ColorFormat.WHITE}金币')
        else:
            self.load_jsonmoney_data()
            if not self.jsonmoney_data.get(event.player.name):
                self.jsonmoney_data[event.player.name] = self.config_data['default_money']
                event.player.send_message(f'经济系统：jsonmoney，没有检测到你的余额，已为你发放{ColorFormat.GREEN}{self.config_data['default_money']}{ColorFormat.WHITE}金币')
            self.save_jsonmoney_data()

    @event_handler
    def on_player_quit(self, event: PlayerQuitEvent):
        if self.send_group_money_flag == True:
            self.on_send_group_money[8].remove_player(event.player)
            if len(self.server.online_players) == 1:
                self.on_send_group_money = []
                self.send_group_money_flag = False
                self.server.scheduler.cancel_task(self.task.task_id)
        else:
            return

    def on_command(self, sender: CommandSender, command: Command, args: list[str]):
        if not isinstance(sender, Player):
            sender.send_message(f'{ColorFormat.YELLOW}该命令只能由玩家执行...')
            return
        player = sender
        if command.name == 'red':
            main_form = ActionForm(
                title=f'{ColorFormat.BOLD}发{ColorFormat.RED}红包{ColorFormat.BLACK}主表单',
                content='请选择操作...'
            )
            if self.config_data['economy'] == 'scoreboard':
                main_form.add_button(f'{ColorFormat.BOLD}余额：{ColorFormat.GREEN}{self.money_objective.get_score(player).value}{ColorFormat.BLACK}金币', icon='textures/ui/MCoin')
            else:
                self.load_jsonmoney_data()
                main_form.add_button(f'{ColorFormat.BOLD}余额：{ColorFormat.GREEN}{self.jsonmoney_data[player.name]}{ColorFormat.BLACK}金币',icon='textures/ui/MCoin')
            main_form.add_button(f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}专属{ColorFormat.RED}红包', icon='textures/ui/promo_gift_small_blue', on_click=self.send_private_money)
            main_form.add_button(f'{ColorFormat.BOLD}普通{ColorFormat.RED}红包', icon='textures/items/emerald', on_click=self.send_normal_group_money)
            main_form.add_button(f'{ColorFormat.BOLD}{ColorFormat.MATERIAL_DIAMOND}拼手气{ColorFormat.RED}红包',icon='textures/items/diamond', on_click=self.send_lucky_group_money)
            main_form.add_button(f'{ColorFormat.BOLD}关闭表单',icon='textures/ui/cancel', on_click=None)
            main_form.add_button(f'{ColorFormat.BOLD}重载配置文件', icon='textures/ui/icon_setting', on_click=self.reload_config_data)
            player.send_form(main_form)

    def send_private_money(self, p: Player):
        dropdown = Dropdown(
            label='请选择玩家...',
            options=[online_player.name for online_player in self.server.online_players]
        )
        textinput = TextInput(
            label=f'{ColorFormat.RED}红包{ColorFormat.WHITE}金额',
            placeholder='请输入一个正整数，例如：20'
        )
        send_private_money_form = ModalForm(
            title=f'{ColorFormat.BOLD}发送{ColorFormat.LIGHT_PURPLE}专属{ColorFormat.RED}红包{ColorFormat.BLACK}表单',
            controls=[dropdown, textinput],
            submit_button='确认',
            on_close=None
        )
        def on_submit(p, json_str):
            data = json.loads(json_str)
            try:
                target = self.server.online_players[data[0]]
                money_to_send = int(data[1])
            except:
                p.send_message(f'{ColorFormat.RED}发送失败：{ColorFormat.WHITE}表单数据解析错误，请按提示正确填写...')
                return
            if money_to_send < 0:
                p.send_message(f'{ColorFormat.RED}发送失败：{ColorFormat.WHITE}表单数据解析错误，请按提示正确填写...')
                return
            if p.name == target.name:
                p.send_message(f'{ColorFormat.RED}发送失败：{ColorFormat.WHITE}你不能给自己发{ColorFormat.LIGHT_PURPLE}专属{ColorFormat.RED}红包{ColorFormat.WHITE}...')
                return
            if p.is_op == False:
                if self.config_data['economy'] == 'scoreboard':
                    if self.money_objective.get_score(p).value < money_to_send:
                        p.send_message(f'{ColorFormat.RED}发送失败：{ColorFormat.WHITE}余额不足...')
                        return
                    else:
                        self.money_objective.get_score(p).value -= money_to_send
                else:
                    self.load_jsonmoney_data()
                    if self.jsonmoney_data[p.name] < money_to_send:
                        p.send_message(f'{ColorFormat.RED}发送失败：{ColorFormat.WHITE}余额不足...')
                        return
                    else:
                        self.jsonmoney_data[p.name] -= money_to_send
                        self.save_jsonmoney_data()
            if self.config_data['economy'] == 'scoreboard':
                self.money_objective.get_score(target).value += money_to_send
            else:
                self.load_jsonmoney_data()
                self.jsonmoney_data[target.name] += money_to_send
                self.save_jsonmoney_data()
            target.send_message(f'玩家 {p.name} 向你发送了一个{ColorFormat.LIGHT_PURPLE}专属{ColorFormat.RED}红包， {ColorFormat.WHITE}金额：{ColorFormat.GREEN}{money_to_send}')
        send_private_money_form.on_submit = on_submit
        p.send_form(send_private_money_form)

    def send_normal_group_money(self, p: Player):
        textinput1 = TextInput(
            label=f'单个{ColorFormat.RED}红包{ColorFormat.WHITE}金额',
            placeholder='请输入一个正整数，例如：10'
        )
        textinput2 =TextInput(
            label=f'{ColorFormat.RED}红包{ColorFormat.WHITE}个数（<= 当前服务器在线玩家数）',
            placeholder='请输入一个正整数，例如：5'
        )
        textinput3 = TextInput(
            label='有效时间（单位：s）',
            placeholder=f'请输入一个正整数，<={self.config_data['max_time_out']}'
        )
        textinput4 = TextInput(
            label=f'{ColorFormat.RED}红包{ColorFormat.WHITE}口令',
            placeholder='请输入任意字符串，不输入则默认为：抢'
        )
        send_normal_group_money_form = ModalForm(
            title=f'{ColorFormat.BOLD}发送普通{ColorFormat.RED}红包{ColorFormat.BLACK}表单',
            controls=[textinput1, textinput2, textinput3, textinput4],
            submit_button='确认',
            on_close=None
        )
        def on_submit(p, json_str):
            if self.send_group_money_flag == True:
                p.send_message(f'{ColorFormat.RED}发送失败：{ColorFormat.WHITE}当前服务器已经有玩家发送了普通{ColorFormat.RED}红包{ColorFormat.MATERIAL_DIAMOND}/拼手气{ColorFormat.RED}红包{ColorFormat.WHITE}...')
                return
            data = json.loads(json_str)
            try:
                single_money_to_send = int(data[0])
                count = int(data[1])
                time_out = int(data[2])
                if data[3] == '':
                    key = '抢'
                else:
                    key = data[3]
            except:
                p.send_message(f'{ColorFormat.RED}发送失败：{ColorFormat.WHITE}表单数据解析错误，请按提示正确填写...')
                return
            if single_money_to_send < 0  or count < 0 or count > len(self.server.online_players) or time_out < 0 or time_out > self.config_data['max_time_out']:
                p.send_message(f'{ColorFormat.RED}发送失败：{ColorFormat.WHITE}表单数据解析错误，请按提示正确填写...')
                return
            receive_count = 0
            total_money_to_send = single_money_to_send * count
            if p.is_op == False:
                if self.config_data['economy'] == 'scoreboard':
                    if self.money_objective.get_score(p).value < total_money_to_send:
                        p.send_message(f'{ColorFormat.RED}发送失败：{ColorFormat.WHITE}余额不足...')
                        return
                    else:
                        self.money_objective.get_score(p).value -= total_money_to_send
                else:
                    self.load_jsonmoney_data()
                    if self.jsonmoney_data[p.name] < total_money_to_send:
                        p.send_message(f'{ColorFormat.RED}发送失败：{ColorFormat.WHITE}余额不足...')
                        return
                    else:
                        self.jsonmoney_data[p.name] -= total_money_to_send
                        self.save_jsonmoney_data()
            boss_bar = self.server.create_boss_bar(
                title=f'{ColorFormat.BOLD}来自玩家 {p.name} 的普通{ColorFormat.RED}红包， {ColorFormat.WHITE}口令：{ColorFormat.BLUE}{key}， {ColorFormat.WHITE}{receive_count}/{count} 已领取， 剩余金额：{ColorFormat.GREEN}{total_money_to_send} {ColorFormat.WHITE}({time_out}s)',
                color=BarColor.YELLOW,
                style=BarStyle.SEGMENTED_10
            )
            boss_bar.progress = 1.0
            for online_player in self.server.online_players:
                boss_bar.add_player(online_player)
            self.send_group_money_flag = True
            start_time = int(time.time())
            self.on_send_group_money = [p, key, single_money_to_send, total_money_to_send, receive_count, count, time_out, start_time, boss_bar, [], 'normal']
            self.task = self.server.scheduler.run_task(self, self.update_boss_bar, delay=0, period=1)
        send_normal_group_money_form.on_submit = on_submit
        p.send_form(send_normal_group_money_form)

    def send_lucky_group_money(self, p: Player):
            textinput1 = TextInput(
                label=f'{ColorFormat.RED}红包{ColorFormat.WHITE}总金额',
                placeholder='请输入一个正整数，例如：200'
            )
            textinput2 = TextInput(
                label=f'{ColorFormat.RED}红包{ColorFormat.WHITE}个数（<= 当前服务器在线玩家数）',
                placeholder='请输入一个正整数，例如：5'
            )
            textinput3 = TextInput(
                label='有效时间（单位：秒）',
                placeholder=f'请输入一个正整数，<={self.config_data['max_time_out']}'
            )
            textinput4 = TextInput(
                label=f'{ColorFormat.RED}红包{ColorFormat.WHITE}口令',
                placeholder='请输入任意字符串，不输入则默认为：抢'
            )
            send_lucky_group_form = ModalForm(
                title=f'{ColorFormat.BOLD}发送{ColorFormat.MATERIAL_DIAMOND}拼手气{ColorFormat.RED}红包{ColorFormat.BLACK}表单',
                controls=[textinput1, textinput2, textinput3, textinput4],
                submit_button='确认',
                on_close=None
            )
            def on_submit(p, json_str):
                if self.send_group_money_flag == True:
                    p.send_message(f'{ColorFormat.RED}发送失败：{ColorFormat.WHITE}当前服务器已经有玩家发送了普通{ColorFormat.RED}红包{ColorFormat.MATERIAL_DIAMOND}/拼手气{ColorFormat.RED}红包{ColorFormat.WHITE}...')
                    return
                data = json.loads(json_str)
                try:
                    total_money_to_send = int(data[0])
                    count = int(data[1])
                    time_out = int(data[2])
                    if data[3] == '':
                        key = '抢'
                    else:
                        key = data[3]
                except:
                    p.send_message(f'{ColorFormat.RED}发送失败：{ColorFormat.WHITE}表单数据解析错误，请按提示正确填写...')
                    return
                if total_money_to_send < 0 or count < 0 or count > len(self.server.online_players) or time_out < 0 or time_out > self.config_data['max_time_out']:
                    p.send_message(f'{ColorFormat.RED}发送失败：{ColorFormat.WHITE}表单数据解析错误，请按提示正确填写...')
                    return
                receive_count = 0
                if p.is_op == False:
                    if self.config_data['economy'] == 'scoreboard':
                        if self.money_objective.get_score(p).value < total_money_to_send:
                            p.send_message(f'{ColorFormat.RED}发送失败：{ColorFormat.WHITE}余额不足...')
                            return
                        else:
                            self.money_objective.get_score(p).value -= total_money_to_send
                    else:
                        self.load_jsonmoney_data()
                        if self.jsonmoney_data[p.name] < total_money_to_send:
                            p.send_message(f'{ColorFormat.RED}发送失败：{ColorFormat.WHITE}余额不足...')
                            return
                        else:
                            self.jsonmoney_data[p.name] -= total_money_to_send
                            self.save_jsonmoney_data()
                # 生成随机数
                local_time = time.localtime()
                local_year = local_time.tm_year
                local_month = local_time.tm_mon
                local_day = local_time.tm_mday
                local_hour = local_time.tm_hour
                local_min = local_time.tm_min
                local_sec = local_time.tm_sec
                final_local_time = eval(str(local_year) + str(local_month) + str(local_day) + str(local_hour) + str(local_min) + str(local_sec))
                seed = final_local_time + total_money_to_send + count + time_out
                # 根据红包个数和随机种子生成概率列表
                random.seed(seed)
                pre_chance_list = [random.random() for _ in range(count)]
                chance_list = [chance / sum(pre_chance_list) for chance in pre_chance_list]
                random.shuffle(chance_list)
                # 根据概率列表生成当个红包金额列表
                single_money_to_send_list = []
                for chance in chance_list[1:]:
                    money = int(total_money_to_send * chance)
                    single_money_to_send_list.append(money)
                last_money = total_money_to_send - sum(single_money_to_send_list)
                single_money_to_send_list.append(last_money)
                random.shuffle(single_money_to_send_list)
                boss_bar = self.server.create_boss_bar(
                    title=f'{ColorFormat.BOLD}来自玩家 {p.name} 的{ColorFormat.MATERIAL_DIAMOND}拼手气{ColorFormat.RED}红包， {ColorFormat.WHITE}口令：{ColorFormat.BLUE}{key}， {ColorFormat.WHITE}{receive_count}/{count} 已领取， 剩余金额：{ColorFormat.GREEN}{total_money_to_send} {ColorFormat.WHITE}({time_out}s)',
                    color=BarColor.YELLOW,
                    style=BarStyle.SEGMENTED_10
                )
                boss_bar.progress = 1.0
                for online_player in self.server.online_players:
                    boss_bar.add_player(online_player)
                self.send_group_money_flag = True
                start_time = int(time.time())
                self.on_send_group_money = [p, key, single_money_to_send_list, total_money_to_send, receive_count, count, time_out, start_time, boss_bar, [], 'lucky']
                self.task = self.server.scheduler.run_task(self, self.update_boss_bar, delay=0, period=1)
            send_lucky_group_form.on_submit = on_submit
            p.send_form(send_lucky_group_form)

    @event_handler
    def on_player_chat(self, event:PlayerChatEvent):
        if self.send_group_money_flag == True:
            if event.message == self.on_send_group_money[1]:
                if event.player.name in self.on_send_group_money[9]:
                    event.player.send_message(f'{ColorFormat.RED}领取失败：{ColorFormat.WHITE}你已经领过了该红包，不能重复领取...')
                    return
                else:
                    if self.on_send_group_money[10] == 'normal':
                        if self.config_data['economy'] == 'scoreboard':
                            self.money_objective.get_score(event.player).value += self.on_send_group_money[2]
                        else:
                            self.load_jsonmoney_data()
                            self.jsonmoney_data[event.player.name] += self.on_send_group_money[2]
                            self.save_jsonmoney_data()
                        self.on_send_group_money[3] -= self.on_send_group_money[2]
                        self.server.broadcast_message(f'玩家 {event.player.name} 领取了玩家 {self.on_send_group_money[0].name} 的{ColorFormat.RED}红包， {ColorFormat.WHITE}金额：{ColorFormat.GREEN}{self.on_send_group_money[2]}')
                    else:
                        if self.on_send_group_money[2][0] == 0:
                            self.server.broadcast_message(f'笑了，玩家 {event.player.name} 领了个空包...')
                        else:
                            if self.config_data['economy'] == 'scoreboard':
                                self.money_objective.get_score(event.player).value += self.on_send_group_money[2][0]
                            else:
                                self.load_jsonmoney_data()
                                self.jsonmoney_data[event.player.name] += self.on_send_group_money[2][0]
                                self.save_jsonmoney_data()
                            self.on_send_group_money[3] -= self.on_send_group_money[2][0]
                            self.server.broadcast_message(f'玩家 {event.player.name} 领取了玩家 {self.on_send_group_money[0].name} 的{ColorFormat.RED}红包， {ColorFormat.WHITE}金额：{ColorFormat.GREEN}{self.on_send_group_money[2][0]}')
                            self.on_send_group_money[2].pop(0)
                    self.on_send_group_money[4] += 1
                    self.on_send_group_money[9].append(event.player.name)
        else:
            return

    def update_boss_bar(self):
        time_out = self.on_send_group_money[6]
        time_start = self.on_send_group_money[7]
        boss_bar = self.on_send_group_money[8]
        time_elapse = int(time.time()) - time_start
        time_remain = time_out - time_elapse
        progress = time_remain / time_out
        if self.on_send_group_money[10] == 'normal':
            boss_bar.title = f'{ColorFormat.BOLD}来自玩家 {self.on_send_group_money[0].name} 的普通{ColorFormat.RED}红包， {ColorFormat.WHITE}口令：{ColorFormat.BLUE}{self.on_send_group_money[1]}， {ColorFormat.WHITE}{self.on_send_group_money[4]}/{self.on_send_group_money[5]} 已领取， 剩余金额：{ColorFormat.GREEN}{self.on_send_group_money[3]} {ColorFormat.WHITE}({time_remain}s)'
        else:
            boss_bar.title = f'{ColorFormat.BOLD}来自玩家 {self.on_send_group_money[0].name} 的{ColorFormat.MATERIAL_DIAMOND}拼手气{ColorFormat.RED}红包， {ColorFormat.WHITE}口令：{ColorFormat.BLUE}{self.on_send_group_money[1]}， {ColorFormat.WHITE}{self.on_send_group_money[4]}/{self.on_send_group_money[5]} 已领取， 剩余金额：{ColorFormat.GREEN}{self.on_send_group_money[3]} {ColorFormat.WHITE}({time_remain}s)'
        if time_remain > 0:
            boss_bar.progress = progress
            if self.on_send_group_money[3] == 0:
                self.on_send_group_money[0].send_message(f'你的{ColorFormat.RED}红包{ColorFormat.WHITE}已全部被领完...')
                boss_bar.remove_all()
                self.on_send_group_money = []
                self.send_group_money_flag = False
                self.server.scheduler.cancel_task(self.task.task_id)
                return
        else: # time_remain = 0
            boss_bar.progress = 0.0
            if self.on_send_group_money[3] != 0:
                if self.on_send_group_money[0].is_op == False:
                    if self.config_data['economy'] == 'scoreboard':
                        self.money_objective.get_score(self.on_send_group_money[0]).value += self.on_send_group_money[3]
                    else:
                        self.load_jsonmoney_data()
                        self.jsonmoney_data[self.on_send_group_money[0].name] += self.on_send_group_money[3]
                    self.on_send_group_money[0].send_message(f'{self.on_send_group_money[4]}/{self.on_send_group_money[5]} 已领取， 已返还金额：{ColorFormat.GREEN}{self.on_send_group_money[3]}')
                else:
                    self.on_send_group_money[0].send_message(f'{self.on_send_group_money[4]}/{self.on_send_group_money[5]} 已领取， 销毁剩余金额：{ColorFormat.GREEN}{self.on_send_group_money[3]}')
            else:
                self.on_send_group_money[0].send_message(f'你的{ColorFormat.RED}红包{ColorFormat.WHITE}已全部被领完...')
            boss_bar.remove_all()
            self.on_send_group_money = []
            self.send_group_money_flag = False
            self.server.scheduler.cancel_task(self.task.task_id)
            return