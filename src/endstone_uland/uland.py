import json
import datetime
import os
import re
import math
import time
import random
from endstone.level import Location
from endstone import ColorFormat, Player
from endstone.plugin import Plugin
from endstone.command import Command, CommandSender, CommandSenderWrapper
from endstone.form import ActionForm, ModalForm, Dropdown, Toggle, TextInput
from endstone.event import event_handler, PlayerJoinEvent, PlayerQuitEvent, BlockBreakEvent, ActorKnockbackEvent, PlayerInteractEvent, PlayerInteractActorEvent, ActorSpawnEvent

current_dir = os.getcwd()
first_dir = os.path.join(current_dir, 'plugins', 'uland')
zx_ui_dir = os.path.join(current_dir, 'plugins', 'zx_ui')
if not os.path.exists(first_dir):
    os.mkdir(first_dir)
land_data_file_path = os.path.join(first_dir, 'land.json')
config_data_file_path = os.path.join(first_dir, 'config.json')
money_data_file_path = os.path.join(current_dir, 'plugins', 'umoney', 'money.json')

class uland(Plugin):
    api_version = '0.5'

    def on_enable(self):
        # 加载领地数据
        if not os.path.exists(land_data_file_path):
            land_data = {}
            with open(land_data_file_path, 'w', encoding='utf-8') as f:
                json_str = json.dumps(land_data, indent=4, ensure_ascii=False)
                f.write(json_str)
        else:
            with open(land_data_file_path, 'r', encoding='utf-8') as f:
                land_data = json.loads(f.read())
        self.land_data = land_data
        # 加载配置文件
        if not os.path.exists(config_data_file_path):
            config_data = {'land_buy_price': 5,
                           'land_create_timeout': 30,
                           'max_area': 40000,
                           'max_land_per_player': 3,
                           'is_land_sell_rate_on': True,
                           'land_sell_cool_down_timeout': 3}
            with open(config_data_file_path, 'w', encoding='utf-8') as f:
                json_str = json.dumps(config_data, indent=4, ensure_ascii=False)
                f.write(json_str)
        else:
            with open(config_data_file_path, 'r', encoding='utf-8') as f:
                config_data = json.loads(f.read())
        self.config_data = config_data
        # 加载 money 数据
        if not os.path.exists(money_data_file_path):
            self.logger.info(f'{ColorFormat.RED}缺少必要前置 jsonmoney...')
            return
        else:
            with open(money_data_file_path, 'r', encoding='utf-8') as f:
                money_data = json.loads(f.read())
        self.money_data = money_data
        self.record_create_land_event = {}
        self.register_events(self)
        self.server.scheduler.run_task(self, self.check_player_pos, delay=0, period=20)
        self.server.scheduler.run_task(self, self.land_protect_task, delay=0, period=20)
        self.CommandSenderWrapper = CommandSenderWrapper(
            sender=self.server.command_sender,
            on_message=None
        )
        self.logger.info(f'{ColorFormat.YELLOW}ULand 已启用...')

    commands = {
        'ul': {
            'description': '打开领地表单',
            'usages': ['/ul'],
            'permissions': ['uland.command.ul']
        },
        'posa': {
            'description': '选中A点',
            'usages': ['/posa'],
            'permissions': ['uland.command.posa']
        },
        'posb': {
            'description': '选中B点',
            'usages': ['/posb'],
            'permissions': ['uland.command.posb']
        }
    }

    permissions ={
        'uland.command.ul': {
            'description': '打开领地表单',
            'default': True
        },
        'uland.command.posa': {
            'description': '选中A点',
            'default': True
        },
        'uland.command.posb': {
            'description': '选中B点',
            'default': True
        }
    }

    def on_command(self, sender: CommandSender, command: Command, args: list[str]):
        if command.name == 'ul':
            if not isinstance(sender, Player):
                sender.send_message(f'{ColorFormat.RED}该命令只能由玩家执行...')
                return
            player = sender
            land_main_form = ActionForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}领地主表单',
                content=f'{ColorFormat.GREEN}请选择操作...',
            )
            land_main_form.add_button(f'{ColorFormat.YELLOW}开始圈地', icon='textures/ui/icon_new', on_click=self.create_land)
            land_main_form.add_button(f'{ColorFormat.YELLOW}我的领地', icon='textures/ui/icon_recipe_nature', on_click=self.my_land)
            land_main_form.add_button(f'{ColorFormat.YELLOW}查询脚下领地', icon='textures/ui/magnifyingGlass', on_click=self.land_info)
            land_main_form.add_button(f'{ColorFormat.YELLOW}服务器公开领地', icon='textures/ui/mashup_world', on_click=self.server_public_land)
            if player.is_op == True:
                land_main_form.add_button(f'{ColorFormat.YELLOW}领地系统配置', icon='textures/ui/op', on_click=self.land_system_config)
            if os.path.exists(zx_ui_dir) == True:
                land_main_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.back_to_menu)
                land_main_form.on_close = self.back_to_menu
            else:
                land_main_form.on_close = None
            player.send_form(land_main_form)

        # /posa -- 圈地模式下选中A点的指令
        if command.name == 'posa':
            # 检测指令是否由玩家执行，否则返回
            if not isinstance(sender, Player):
                sender.send_message(f'{ColorFormat.RED}该命令只能由玩家执行...')
                return
            player = sender
            # 检测玩家是否已有圈地进程在进行，没有则返回
            if not self.record_create_land_event.get(player.name):
                player.send_message(f'{ColorFormat.RED}你没有正在进行的圈地进程...')
                return
            # 记录玩家选中的A点坐标 x 和 z
            PosA = [math.floor(player.location.x), math.floor(player.location.z), math.floor(player.location.y)]
            # 将玩家选中的A点坐标存储到实时圈地进程记录中
            if self.record_create_land_event[player.name].get('PosA'):
                self.record_create_land_event[player.name]['PosA'] = PosA
                player.send_message(f'{ColorFormat.YELLOW}A点更新成功, 坐标 ({PosA[0]}, ~, {PosA[1]})')
            else:
                self.record_create_land_event[player.name]['PosA'] = PosA
                player.send_message(f'{ColorFormat.YELLOW}A点选中成功, 坐标 ({PosA[0]}, ~, {PosA[1]})')
            # 记录玩家所在的维度名
            dimension = player.location.dimension.name
            # 将玩家所在的维度名存储到实时圈地进程记录中
            self.record_create_land_event[player.name]['dimension'] = dimension

        # /posb -- 圈地模式下选中B点的指令
        if command.name == 'posb':
            # 检测指令是否由玩家执行，否则返回
            if not isinstance(sender, Player):
                sender.send_message(f'{ColorFormat.RED}该命令只能由玩家执行...')
                return
            player = sender
            # 检测玩家是否有圈地进程在进行，没有则返回
            if not self.record_create_land_event.get(player.name):
                player.send_message(f'{ColorFormat.RED}你没有正在进行的圈地进程...')
                return
            # 检测玩家是否已经选中了A点，没有则返回
            if not self.record_create_land_event[player.name].get('PosA'):
                player.send_message(f'{ColorFormat.RED}选点失败： {ColorFormat.WHITE}你还没有选中A点...')
                return
            # 检测玩家选中的B点所在维度是否和记录的A点所在维度相同，不相同则返回
            if self.record_create_land_event[player.name]['dimension'] != player.location.dimension.name:
                player.send_message(f'{ColorFormat.RED}选点失败： {ColorFormat.WHITE}你不能跨纬度选点...')
                return
            # 记录玩家选中的B点坐标 x 和 z
            PosB = [math.floor(player.location.x), math.floor(player.location.z)]
            # 检测玩家选中的B点坐标是否和记录的A点坐标重复，重复了则返回
            PosA = self.record_create_land_event[player.name]['PosA']
            if PosA == PosB:
                player.send_message(f'{ColorFormat.RED}选点失败： {ColorFormat.WHITE}你不能选中和A点重复的点...')
                return
            # 将选中的B点坐标存储到实时圈地进程记录中
            self.record_create_land_event[player.name]['PosB'] = PosB
            player.send_message(f'{ColorFormat.YELLOW}B点选中成功, 坐标 ({PosB[0]}, ~, {PosB[1]})')

    # 开启圈地模式函数
    def create_land(self, player: Player):
        # 检测玩家名下领地数量
        if len(self.land_data[player.name].keys()) >= self.config_data['max_land_per_player']:
            player.send_message(f'{ColorFormat.RED}圈地失败： {ColorFormat.WHITE}你拥有的领地数量已满{self.config_data['max_land_per_player']}个...')
            return
        # 检测玩家是否已经有圈地进程在进行，没有则开始圈地经常
        if not self.record_create_land_event.get(player.name):
            # 为玩家的圈地经常创建一个空字典
            self.record_create_land_event[player.name] = {}
            # 记录玩家开启圈地模式的开始时间
            time_start = round(time.time())
            # 将玩家开启圈地模式的开始时间存储到实时圈地进程记录中
            self.record_create_land_event[player.name]['time_start'] = time_start
            # 为玩家创建一个判断圈地模式耗时的 task
            task = self.server.scheduler.run_task(self, lambda x=player: self.on_create_land(player), delay=0, period=20)
            # 将判断玩家圈地耗时的 task 存储到实时圈地进程记录中
            self.record_create_land_event[player.name]['task'] = task
            player.send_message(f'{ColorFormat.YELLOW}圈地模式已开启, 请在{self.config_data['land_create_timeout']}s内完成圈地...\n'
                                f'输入 /posa 选中A点\n'
                                f'输入 /posb 选中B点\n'
                                f'注意： 不能跨维度选点, 所选A点坐标和B点坐标不能重复！')
        # 检测玩家是否已经有圈地进程在进行，有则返回
        else:
            player.send_message(f'{ColorFormat.RED}圈地失败： {ColorFormat.WHITE}你有一个圈地进程在进行...')
            return

    # 判断玩家圈地耗时 task
    def on_create_land(self, player: Player):
        # 读取玩家实时圈地进程记录的开始时间
        time_start = self.record_create_land_event[player.name]['time_start']
        # 获取玩家开启圈地模式后的当前时间
        time_now = round(time.time())
        # 如果玩家开启圈地模式后的耗时大于30s，并且没有完成圈地模式所需的操作
        # 则取消判断玩家圈地耗时 task，并释放玩家实时圈地进程记录中的数据，并返回
        if time_now - time_start > self.config_data['land_create_timeout'] and len(self.record_create_land_event[player.name]) < 5:
            self.server.scheduler.cancel_task(self.record_create_land_event[player.name]['task'].task_id)
            del self.record_create_land_event[player.name]
            player.send_message(f'{ColorFormat.RED}圈地超时： {ColorFormat.WHITE}数据已释放...')
            # 测试用代码
            '''self.logger.info(f'{self.record_create_land_event}')'''
            return
        # 如果玩家在开启圈地模式后，在规定时间内完成所需的操作，则取消判断判断玩家圈地耗时 task，并调用领地信息完善函数
        if len(self.record_create_land_event[player.name]) == 5:
            self.server.scheduler.cancel_task(self.record_create_land_event[player.name]['task'].task_id)
            self.on_further_create_land(player)
            # 测试用代码
            '''self.logger.info(f'{self.record_create_land_event}')'''

    # 领地信息完善函数
    def on_further_create_land(self, player: Player):
        # 读取玩家实时圈地经进程记录的A点坐标
        PosA = self.record_create_land_event[player.name]['PosA']
        # 读取玩家实时圈地经进程记录的B点坐标
        PosB = self.record_create_land_event[player.name]['PosB']
        # 读取玩家实时圈地进程记录的维度
        dimension = self.record_create_land_event[player.name]['dimension']
        # 检测玩家所选领地是否和已有领地发生重叠
        for key, value in self.land_data.items():
            land = value
            for key, value in land.items():
                land_info = value
                if dimension == land_info['dimension']:
                    range = []
                    it = re.finditer(r'[-+]?\d+(?:\.\d+)?', land_info['range'])
                    for i in it:
                        range.append(int(i.group()))
                    if ((min(range[0], range[2]) <= PosA[0] <= max(range[0], range[2])
                         and min(range[1], range[3]) <= PosA[1] <= max(range[1], range[3]))
                            or (min(range[0], range[2]) <= PosB[0] <= max(range[0], range[2])
                                and min(range[1], range[3]) <= PosB[1] <= max(range[1], range[3]))
                            or (((min(PosA[0], PosB[0]) <= range[0] <= max(PosA[0], PosB[0]))
                                and (min(PosA[1], PosB[1]) <= range[1] <= max(PosA[1], PosB[1])))
                                and ((min(PosA[0], PosB[0]) <= range[2] <= max(PosA[0], PosB[0]))
                                and (min(PosA[1], PosB[1]) <= range[3] <= max(PosA[1], PosB[1]))))):
                        del self.record_create_land_event[player.name]
                        player.send_message(f'{ColorFormat.RED}圈地失败： {ColorFormat.WHITE}你选中的领地和一个存在的领地重叠了, 数据已释放...')
                        return
        # 计算玩家圈中的领地大小，小于4 或 大于配置文件面积，则返回
        width1 = abs(PosA[0] - PosB[0])
        width2 = abs(PosA[1] - PosB[1])
        area = width1 * width2
        if area < 4:
            del self.record_create_land_event[player.name]
            player.send_message(f'{ColorFormat.RED}圈地失败： {ColorFormat.WHITE}你所选中的领地面积太小了, 数据已释放...')
            return
        if area > self.config_data['max_area']:
            del self.record_create_land_event[player.name]
            player.send_message(f'{ColorFormat.RED}圈地失败： {ColorFormat.WHITE}你所选中的领地面积大于{self.config_data['max_area']}, 数据已释放...')
            return
        # 计算玩家圈中的领地所耗费的经济
        land_expense = area * self.config_data['land_buy_price']
        # 判断玩家的经济是否能支付圈中领地所耗费的经济，不能则返回
        self.load_money_data()
        player_money = self.money_data[player.name]
        if player_money < land_expense:
            del self.record_create_land_event[player.name]
            player.send_message(f'{ColorFormat.RED}圈地失败： {ColorFormat.WHITE}你的余额不足以支付圈地费用\n'
                                f'领地价格： {land_expense}\n'
                                f'你的余额： {player_money}')
            return
        # 整合信息，并为玩家发送表单
        textinput1 = TextInput(
            label=f'{ColorFormat.YELLOW}纬度： {ColorFormat.WHITE}{dimension}\n'
                  f'{ColorFormat.YELLOW}A点： {ColorFormat.WHITE}({PosA[0]}, ~, {PosA[1]})\n'
                  f'{ColorFormat.YELLOW}B点： {ColorFormat.WHITE}({PosB[0]}, ~, {PosB[1]})\n'
                  f'{ColorFormat.YELLOW}面积： {ColorFormat.WHITE}{area}\n'
                  f'{ColorFormat.YELLOW}价格： {ColorFormat.WHITE}{land_expense}\n'
                  f'\n'
                  f'{ColorFormat.GREEN}请输入领地名称...',
            placeholder=f'留空则默认为： {player.name}的领地'
        )
        further_create_land_form = ModalForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}圈地表单',
            controls=[textinput1],
            on_close=self.on_cancel_further_create_land
        )
        def on_submit(player: Player, json_str):
            data = json.loads(json_str)
            if len(data[0]) == 0:
                land_name = f'{player.name}的领地'
            else:
                land_name = data[0]
            # 检测玩家所填的 land_name 是否和已有的重复，重复则返回
            if land_name in list(self.land_data[player.name].keys()):
                del self.record_create_land_event[player.name]
                player.send_message(f'{ColorFormat.RED}圈地失败： {ColorFormat.WHITE}你已经有了一个名为： {land_name}的领地了, 请重新命名, 数据已释放...')
                return
            # 记录玩家创建领地的时间
            land_buy_time = str(datetime.datetime.now()).split(' ')[0]
            # 存储玩家领地信息
            self.land_data[player.name][land_name] = {'dimension': dimension,
                                                      'range': f'({PosA[0]}, ~, {PosA[1]}) - ({PosB[0]}, ~, {PosB[1]})',
                                                      'area': area,
                                                      'land_expense': land_expense,
                                                      'land_buy_time': land_buy_time,
                                                      'land_tp': [PosA[0], PosA[2], PosA[1]],
                                                      'permissions': [],
                                                      'public_land': False,
                                                      'fire_protect': True,
                                                      'tnt_explode_protect': True,
                                                      'mob_grief_protect': True,
                                                      'anti_right_click_block': True,
                                                      'anti_break_block': True,
                                                      'anti_right_click_entity': True}
            self.money_data[player.name] -= land_expense
            self.save_money_data()
            del self.record_create_land_event[player.name]
            self.save_land_data()
            player.send_message(f'{ColorFormat.YELLOW}圈地成功...')
        further_create_land_form.on_submit = on_submit
        player.send_form(further_create_land_form)

    # 取消圈地函数
    def on_cancel_further_create_land(self, player: Player):
        del self.record_create_land_event[player.name]
        player.send_message(f'{ColorFormat.RED}圈地取消, {ColorFormat.WHITE}数据已释放...')
        # 测试用代码...
        '''self.logger.info(f'{self.record_create_land_event}')'''

    # 防止玩家在圈地过程中下线造成的崩服
    @event_handler
    def on_player_left(self, event: PlayerQuitEvent):
        if self.record_create_land_event.get(event.player.name):
            self.server.scheduler.cancel_task(self.record_create_land_event[event.player.name]['task'].task_id)
            del self.record_create_land_event[event.player.name]
            # 测试用代码...
            '''self.logger.info(f'{self.record_create_land_event}')'''

    # 查看领地函数
    def my_land(self, player: Player):
        my_land_form =  ActionForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}我的领地',
            content=f'{ColorFormat.GREEN}请选择操作...',
            on_close=self.back_to_main_form
        )
        for key, value in self.land_data.items():
            land_owner = key
            land = value
            for key, value in land.items():
                land_name = key
                land_info = value
                dimension = land_info['dimension']
                range = land_info['range']
                area = land_info['area']
                land_expense = land_info['land_expense']
                land_buy_time = land_info['land_buy_time']
                land_tp = land_info['land_tp']
                permissions = land_info['permissions']
                if player.name == land_owner:
                    my_land_form.add_button(f'{land_name}\n{ColorFormat.YELLOW}[领主] {dimension}', icon='textures/ui/icon_spring', on_click=self.my_land_details(
                                                land_name, dimension, range, area, land_expense, land_buy_time, land_tp, permissions))
                if player.name in permissions:
                    my_land_form.add_button(f'{land_name}\n{ColorFormat.YELLOW}[成员] {dimension}', icon='textures/ui/icon_spring', on_click=self.my_land_member_details(
                                                land_owner, land_name, dimension, range, area, land_expense, land_buy_time, land_tp, permissions))
        my_land_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.back_to_main_form)
        player.send_form(my_land_form)

    # 查看成员领地函数
    def my_land_member_details(self, land_owner, land_name, dimension, range, area, land_expense, land_buy_time, land_tp, permissions):
        def on_click(player: Player):
            my_land_member_details_form =  ActionForm(
                title=land_name,
                content=f'{ColorFormat.YELLOW}领主： {ColorFormat.YELLOW}{land_owner}\n'
                        f'{ColorFormat.YELLOW}维度： {ColorFormat.WHITE}{dimension}\n'
                        f'{ColorFormat.YELLOW}范围： {ColorFormat.WHITE}{range}\n'
                        f'{ColorFormat.YELLOW}面积： {ColorFormat.WHITE}{area}\n'
                        f'{ColorFormat.YELLOW}购入价： {ColorFormat.WHITE}{land_expense}\n'
                        f'{ColorFormat.YELLOW}创建时间： {ColorFormat.WHITE}{land_buy_time}\n'
                        f'{ColorFormat.YELLOW}传送点： {ColorFormat.WHITE}({land_tp[0]}, {land_tp[1]}, {land_tp[2]})\n'
                        f'{ColorFormat.YELLOW}成员： {ColorFormat.WHITE}',
                on_close=self.my_land
            )
            for member in permissions:
                my_land_member_details_form.content += member
                my_land_member_details_form.content += ', '
            my_land_member_details_form.add_button(f'{ColorFormat.YELLOW}传送领地', icon='textures/ui/realmsIcon', on_click=self.tp_to_my_land(land_tp, dimension))
            my_land_member_details_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.my_land)
            player.send_form(my_land_member_details_form)
        return on_click

    # 查看领地详情函数
    def my_land_details(self, land_name, dimension, range, area, land_expense, land_but_time, land_tp, permissions):
        def on_click(player: Player):
            my_land_details_form = ActionForm(
                title=land_name,
                content=f'{ColorFormat.YELLOW}维度： {ColorFormat.WHITE}{dimension}\n'
                        f'{ColorFormat.YELLOW}范围： {ColorFormat.WHITE}{range}\n'
                        f'{ColorFormat.YELLOW}面积： {ColorFormat.WHITE}{area}\n'
                        f'{ColorFormat.YELLOW}购入价： {ColorFormat.WHITE}{land_expense}\n'
                        f'{ColorFormat.YELLOW}创建时间： {ColorFormat.WHITE}{land_but_time}\n'
                        f'{ColorFormat.YELLOW}传送点： {ColorFormat.WHITE}({land_tp[0]}, {land_tp[1]}, {land_tp[2]})\n'
                        f'{ColorFormat.YELLOW}成员： {ColorFormat.WHITE}',
                on_close=self.my_land
            )
            if len(permissions) == 0:
                my_land_details_form.content += '无'
            else:
                for member in permissions:
                    my_land_details_form.content += member
                    my_land_details_form.content += ', '
            my_land_details_form.content += f'\n\n{ColorFormat.GREEN}请选择操作...'
            my_land_details_form.add_button(f'{ColorFormat.YELLOW}传送领地', icon='textures/ui/realmsIcon', on_click=self.tp_to_my_land(land_tp, dimension))
            my_land_details_form.add_button(f'{ColorFormat.YELLOW}设置领地', icon='textures/ui/hammer_l', on_click=self.my_land_setting(land_name))
            my_land_details_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.my_land)
            player.send_form(my_land_details_form)
        return on_click

    # 传送领地函数
    def tp_to_my_land(self, land_tp, dimension):
        def on_click(player: Player):
            if dimension == 'Overworld':
                target_dimension = self.server.level.get_dimension('OVERWORLD')
            elif dimension == 'Nether':
                target_dimension = self.server.level.get_dimension('NETHER')
            else:
                target_dimension = self.server.level.get_dimension('THE_END')
            location = Location(
                target_dimension,
                x=float(land_tp[0]),
                y=float(land_tp[1]),
                z=float(land_tp[2])
            )
            player.teleport(location)
            player.send_message(f'{ColorFormat.YELLOW}传送成功, 欢迎回家...')
        return on_click

    # 设置领地函数
    def my_land_setting(self, land_name):
        def on_click(player: Player):
            my_land_setting_form = ActionForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}设置领地',
                content=f'{ColorFormat.GREEN}正在对 {land_name} {ColorFormat.GREEN}进行操作...\n'
                        f'\n'
                        f'{ColorFormat.GREEN}请选择操作...',
                on_close=self.my_land
            )
            my_land_setting_form.add_button(f'{ColorFormat.YELLOW}添加领地成员', icon='textures/ui/sidebar_icons/profile_screen_icon', on_click=self.my_land_add_member(land_name))
            my_land_setting_form.add_button(f'{ColorFormat.YELLOW}删除领地成员', icon='textures/ui/sidebar_icons/dressing_room_customization', on_click=self.my_land_delete_member(land_name))
            my_land_setting_form.add_button(f'{ColorFormat.YELLOW}重命名领地', icon='textures/ui/icon_book_writable', on_click=self.my_land_rename(land_name))
            my_land_setting_form.add_button(f'{ColorFormat.YELLOW}设置领地安全', icon='textures/ui/recipe_book_icon', on_click=self.my_land_set_security(land_name))
            my_land_setting_form.add_button(f'{ColorFormat.YELLOW}设置领地传送点', icon='textures/ui/realmsIcon', on_click=self.my_land_set_land_tp(land_name))
            my_land_setting_form.add_button(f'{ColorFormat.YELLOW}回收领地', icon='textures/ui/trade_icon', on_click=self.my_land_sell(land_name))
            my_land_setting_form.add_button(f'{ColorFormat.YELLOW}过户领地', icon='textures/ui/switch_accounts', on_click=self.my_land_transfer_ownership(land_name))
            my_land_setting_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.my_land)
            player.send_form(my_land_setting_form)
        return on_click

    # 添加领地成员
    def my_land_add_member(self, land_name):
        def on_click(player: Player):
            player_name_list = [player_name for player_name in self.land_data.keys() if player_name != player.name]
            if len(player_name_list) == 0:
                player.send_message(f'{ColorFormat.RED}添加失败： {ColorFormat.WHITE}服务器除了你没有其他玩家的数据记录...')
                return
            dropdown = Dropdown(
                label=f'{ColorFormat.GREEN}请选择玩家...',
                options=player_name_list
            )
            my_land_add_member_form = ModalForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}添加领地成员',
                controls=[dropdown],
                on_close=self.my_land
            )
            def on_submit(player: Player, json_str):
                data = json.loads(json_str)
                player_to_add_name = player_name_list[data[0]]
                if player_to_add_name in self.land_data[player.name][land_name]['permissions']:
                    player.send_message(f'{ColorFormat.RED}添加失败： {ColorFormat.WHITE}该玩家已经在该领地的成员列表中...')
                    return
                self.land_data[player.name][land_name]['permissions'].append(player_to_add_name)
                self.save_land_data()
                player.send_message(f'{ColorFormat.YELLOW}添加成功...')
            my_land_add_member_form.on_submit = on_submit
            player.send_form(my_land_add_member_form)
        return on_click

    # 删除领地成员函数
    def my_land_delete_member(self, land_name):
        def on_click(player: Player):
            if len(self.land_data[player.name][land_name]['permissions']) == 0:
                player.send_message(f'{ColorFormat.RED}删除失败： {ColorFormat.WHITE}此领地没有任何成员...')
                return
            dropdown =Dropdown(
                label=f'{ColorFormat.GREEN}请选择玩家...',
                options=self.land_data[player.name][land_name]['permissions'],
            )
            my_land_delete_member_form = ModalForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}删除领地成员',
                controls=[dropdown],
                on_close=self.my_land
            )
            def on_submit(player: Player, json_str):
                data = json.loads(json_str)
                player_to_delete = self.land_data[player.name][land_name]['permissions'][data[0]]
                self.land_data[player.name][land_name]['permissions'].remove(player_to_delete)
                self.save_land_data()
                player.send_message(f'{ColorFormat.YELLOW}删除成功...')
            my_land_delete_member_form.on_submit = on_submit
            player.send_form(my_land_delete_member_form)
        return on_click

    # 重命名领地函数
    def my_land_rename(self, land_name):
        def on_click(player: Player):
            textinput = TextInput(
                label=f'{ColorFormat.YELLOW}原领地名： {land_name}\n'
                      f'\n'
                      f'{ColorFormat.GREEN}请输入新的领地名...',
                placeholder=f'留空则默认为： {player.name}的领地'
            )
            my_land_rename_form = ModalForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}重命名领地',
                controls=[textinput],
                on_close=self.my_land
            )
            def on_submit(player: Player, json_str):
                data = json.loads(json_str)
                if len(data[0]) == '':
                    new_land_name = f'{player.name}的领地'
                else:
                    new_land_name = data[0]
                # 检测玩家重命名的领地名是否和名下其他的领地名有重复，有则返回
                if self.land_data[player.name].get(new_land_name):
                    player.send_message(f'{ColorFormat.RED}重命名失败： {ColorFormat.WHITE}你已经有一个名为： {new_land_name} 的领地了, 请重新命名...')
                    return
                self.land_data[player.name][new_land_name] = self.land_data[player.name][land_name]
                self.land_data[player.name].pop(land_name)
                self.save_land_data()
                player.send_message(f'{ColorFormat.YELLOW}重命名成功...')
            my_land_rename_form.on_submit = on_submit
            player.send_form(my_land_rename_form)
        return on_click

    # 设置领地安全函数
    def my_land_set_security(self, land_name):
        def on_click(player: Player):
            toggle1 = Toggle(
                label=f'{ColorFormat.YELLOW}开启防火 （同时禁用：闪电）'
            )
            if self.land_data[player.name][land_name]['fire_protect'] == True:
                toggle1.default_value = True
            else:
                toggle1.default_value = False
            toggle2 = Toggle(
                label=f'{ColorFormat.YELLOW}开启TNT防爆 （同时禁用：水晶生成）'
            )
            if self.land_data[player.name][land_name]['tnt_explode_protect'] == True:
                toggle2.default_value = True
            else:
                toggle2.default_value = False
            toggle3 = Toggle(
                label=f'{ColorFormat.YELLOW}开启危险生物防护 （苦力怕, 凋零）'
            )
            if self.land_data[player.name][land_name]['mob_grief_protect'] == True:
                toggle3.default_value = True
            else:
                toggle3.default_value = False
            toggle4 = Toggle(
                label=f'{ColorFormat.YELLOW}阻止一切右键交互方块'
            )
            if self.land_data[player.name][land_name]['anti_right_click_block'] == True:
                toggle4.default_value = True
            else:
                toggle4.default_value = False
            toggle5 = Toggle(
                label=f'{ColorFormat.YELLOW}阻止一切方块破坏'
            )
            if self.land_data[player.name][land_name]['anti_break_block'] == True:
                toggle5.default_value = True
            else:
                toggle5.default_value = False
            toggle6 = Toggle(
                label=f'{ColorFormat.YELLOW}阻止一切右键交互实体'
            )
            if self.land_data[player.name][land_name]['anti_right_click_entity'] == True:
                toggle6.default_value = True
            else:
                toggle6.default_value = False
            toggle7 = Toggle(
                label=f'{ColorFormat.YELLOW}公开领地传送点'
            )
            if self.land_data[player.name][land_name]['public_land'] == True:
                toggle7.default_value = True
            else:
                toggle7.default_value = False
            my_land_set_security_form = ModalForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}设置领地安全',
                controls=[toggle1, toggle2, toggle3, toggle4, toggle5, toggle6, toggle7],
                on_close=self.my_land
            )
            def on_submit(player: Player, json_str):
                data = json.loads(json_str)
                if data[0] == True:
                    self.land_data[player.name][land_name]['fire_protect'] = True
                else:
                    self.land_data[player.name][land_name]['fire_protect'] = False
                if data[1] == True:
                    self.land_data[player.name][land_name]['tnt_explode_protect'] = True
                else:
                    self.land_data[player.name][land_name]['tnt_explode_protect'] = False
                if data[2] == True:
                    self.land_data[player.name][land_name]['mob_grief_protect'] = True
                else:
                    self.land_data[player.name][land_name]['mob_grief_protect'] = False
                if data[3] == True:
                    self.land_data[player.name][land_name]['anti_right_click_block'] = True
                else:
                    self.land_data[player.name][land_name]['anti_right_click_block'] = False
                if data[4] == True:
                    self.land_data[player.name][land_name]['anti_break_block'] = True
                else:
                    self.land_data[player.name][land_name]['anti_break_block'] = False
                if data[5] == True:
                    self.land_data[player.name][land_name]['anti_right_click_entity'] = True
                else:
                    self.land_data[player.name][land_name]['anti_right_click_entity'] = False
                if data[6] == True:
                    self.land_data[player.name][land_name]['public_land'] = True
                else:
                    self.land_data[player.name][land_name]['public_land'] = False
                player.send_message(f'{ColorFormat.YELLOW}领地安全设置已更新...')
                self.save_land_data()
            my_land_set_security_form.on_submit = on_submit
            player.send_form(my_land_set_security_form)
        return on_click

    # 设置领地传送点函数
    def my_land_set_land_tp(self, land_name):
        def on_click(player: Player):
            new_land_tp = [math.floor(player.location.x), math.floor(player.location.y), math.floor(player.location.z)]
            confirm_form = ActionForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}设置领地传送点',
                content=f'{ColorFormat.GREEN}你确定将领地传送点设置为'
                        f'{ColorFormat.WHITE}({new_land_tp[0]}, {new_land_tp[1]}, {new_land_tp[2]})'
                        f'{ColorFormat.GREEN}吗？',
                on_close=self.my_land
            )
            confirm_form.add_button(f'{ColorFormat.YELLOW}确认', icon='textures/ui/realms_slot_check', on_click=self.my_land_set_land_tp_confirm(land_name, new_land_tp))
            confirm_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.my_land)
            player.send_form(confirm_form)
        return on_click

    def my_land_set_land_tp_confirm(self, land_name, new_land_tp):
        def on_click(player: Player):
            self.land_data[player.name][land_name]['land_tp'] = new_land_tp
            self.save_land_data()
            player.send_message(f'{ColorFormat.YELLOW}设置领地传送点成功...')
        return on_click

    # 回收领地函数
    def my_land_sell(self, land_name):
        def on_click(player: Player):
            confirm_form = ActionForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}回收领地',
                content=f'{ColorFormat.GREEN}你确定要回收此领地 {ColorFormat.WHITE}{land_name}吗？\n'
                        f'\n',
                on_close=self.my_land
            )
            land_expense = self.land_data[player.name][land_name]['land_expense']
            land_buy_time = self.land_data[player.name][land_name]['land_buy_time']
            if self.config_data['is_land_sell_rate_on'] == False:
                land_sell_money = land_expense
                confirm_form.content += (f'{ColorFormat.YELLOW}创建时间： {ColorFormat.WHITE}{land_buy_time}\n'
                                         f'{ColorFormat.YELLOW}购入价： {ColorFormat.WHITE}{land_expense}\n'
                                         f'{ColorFormat.YELLOW}回收价： {ColorFormat.WHITE}{land_sell_money}\n'
                                         f'\n'
                                         f'{ColorFormat.AQUA}领地回收价浮动未开启')
                confirm_form.add_button(f'{ColorFormat.YELLOW}回收', icon='textures/ui/realms_slot_check', on_click=self.my_land_sell_confirm(land_name, land_sell_money))
            else:
                current_time = datetime.datetime.now()
                # 将当天的日期作为随机种子
                random.seed(str(current_time).split(' ')[0])
                land_sell_rate = round(random.uniform(0, 2), 2)
                land_sell_money = round(land_expense * land_sell_rate)
                pre_land_buy_time = land_buy_time.split('-')
                if ((current_time - datetime.datetime(int(pre_land_buy_time[0]), int(pre_land_buy_time[1]), int(pre_land_buy_time[2]))).days
                    >= self.config_data['land_sell_cool_down_timeout']):
                    confirm_form.content += (f'{ColorFormat.YELLOW}创建时间： {ColorFormat.WHITE}{land_buy_time}\n'
                                             f'{ColorFormat.YELLOW}购入价： {ColorFormat.WHITE}{land_expense}\n'
                                             f'{ColorFormat.YELLOW}当日回收价率： {ColorFormat.WHITE}{land_sell_rate}\n'
                                             f'{ColorFormat.YELLOW}回收价： {ColorFormat.WHITE}{land_sell_money}\n'
                                             f'\n'
                                             f'{ColorFormat.AQUA}领地回收价浮动已开启\n'
                                             f'{ColorFormat.YELLOW}今天离你创建领地已满{self.config_data['land_sell_cool_down_timeout']}天\n'
                                             f'{ColorFormat.GREEN}可回收')
                    confirm_form.add_button(f'{ColorFormat.YELLOW}回收', icon='textures/ui/realms_slot_check', on_click=self.my_land_sell_confirm(land_name, land_sell_money))
                else:
                    confirm_form.content += (f'{ColorFormat.YELLOW}创建时间： {ColorFormat.WHITE}{land_buy_time}\n'
                                             f'{ColorFormat.YELLOW}购入价： {ColorFormat.WHITE}{land_expense}\n'
                                             f'{ColorFormat.YELLOW}当日回收价率： {ColorFormat.WHITE}{land_sell_rate}\n'
                                             f'\n'
                                             f'{ColorFormat.AQUA}领地回收价浮动已开启\n'
                                             f'{ColorFormat.YELLOW}今天离你创建领地不足{self.config_data['land_sell_cool_down_timeout']}天\n'
                                             f'{ColorFormat.RED}不可回收')
            confirm_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.my_land)
            player.send_form(confirm_form)
        return on_click

    # 领地过户函数
    def my_land_transfer_ownership(self, land_name):
        def on_click(player: Player):
            player_name_list = [player_name for player_name in self.land_data.keys() if player_name != player.name]
            if len(player_name_list) == 0:
                player.send_message(f'{ColorFormat.RED}过户失败： {ColorFormat.WHITE}服务器除了你没有其他玩家的数据记录...')
                return
            dropdown = Dropdown(
                label=f'{ColorFormat.GREEN}请选择玩家...',
                options=player_name_list
            )
            my_land_transfer_ownership_form = ModalForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}过户领地',
                controls=[dropdown],
                on_close=self.my_land
            )
            def on_submit(player: Player, json_str):
                data = json.loads(json_str)
                player_to_transfer_ownership_name = player_name_list[data[0]]
                # 复制领地数据给过户的玩家
                self.land_data[player_to_transfer_ownership_name][land_name] = self.land_data[player.name][land_name]
                # 重置领地设置
                self.land_data[player_to_transfer_ownership_name][land_name]['permissions'] = []
                self.land_data[player_to_transfer_ownership_name][land_name]['public_land'] = False
                self.land_data[player_to_transfer_ownership_name][land_name]['fire_protect'] = True
                self.land_data[player_to_transfer_ownership_name][land_name]['tnt_explode_protect'] = True
                self.land_data[player_to_transfer_ownership_name][land_name]['mob_grief_protect'] = True
                self.land_data[player_to_transfer_ownership_name][land_name]['anti_right_click_block'] = True
                self.land_data[player_to_transfer_ownership_name][land_name]['anti_break_block'] = True
                self.land_data[player_to_transfer_ownership_name][land_name]['anti_right_click_entity'] = True
                self.land_data[player.name].pop(land_name)
                self.save_land_data()
                player.send_message(f'{ColorFormat.YELLOW}过户成功...')
            my_land_transfer_ownership_form.on_submit = on_submit
            player.send_form(my_land_transfer_ownership_form)
        return on_click

    def my_land_sell_confirm(self, land_name, land_sell_money):
        def on_click(player: Player):
            self.land_data[player.name].pop(land_name)
            self.load_money_data()
            self.money_data[player.name] += land_sell_money
            self.save_land_data()
            self.save_money_data()
            player.send_message(f'{ColorFormat.YELLOW}领地回收成功...')
        return on_click

    # 查询脚下领地信息函数
    def land_info(self, player: Player):
        player_pos = [math.floor(player.location.x), math.floor(player.location.z)]
        player_dimension = player.dimension.name
        land_info_form = ActionForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}脚下领地信息',
            content='',
            on_close=self.back_to_main_form
        )
        land_info_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.back_to_main_form)
        flag = True
        for key, value in self.land_data.items():
            if flag == False:
                break
            land_owner = key
            land = value
            for key, value in land.items():
                if flag == False:
                    break
                land_name = key
                land_info = value
                range = []
                it = re.finditer(r'[-+]?\d+(?:\.\d+)?', land_info['range'])
                for i in it:
                    range.append(int(i.group()))
                if (min(range[0], range[2]) <= player_pos[0] <= max(range[0], range[2])
                        and min(range[1], range[3]) <= player_pos[1] <= max(range[1], range[3])
                        and player_dimension == land_info['dimension']):
                    land_member = ''
                    for member in land_info['permissions']:
                        land_member += member
                        land_member += ' '
                    land_info_form.content += (f'{ColorFormat.YELLOW}领主： {ColorFormat.WHITE}{land_owner}\n'
                                               f'{ColorFormat.YELLOW}领地名： {ColorFormat.WHITE}{land_name}\n'
                                               f'{ColorFormat.YELLOW}维度： {ColorFormat.WHITE}{land_info['dimension']}\n'
                                               f'{ColorFormat.YELLOW}范围： {ColorFormat.WHITE}{land_info['range']}\n'
                                               f'{ColorFormat.YELLOW}面积： {ColorFormat.WHITE}{land_info['area']}\n'
                                               f'{ColorFormat.YELLOW}购入价： {ColorFormat.WHITE}{land_info['land_expense']}\n'
                                               f'{ColorFormat.YELLOW}创建时间： {ColorFormat.WHITE}{land_info['land_buy_time']}\n'
                                               f'{ColorFormat.YELLOW}传送点： {ColorFormat.WHITE}({land_info['land_tp'][0]}, {land_info['land_tp'][1]}, {land_info['land_tp'][2]})\n'
                                               f'{ColorFormat.YELLOW}成员： {ColorFormat.WHITE}{land_member}')
                    player.send_form(land_info_form)
                    flag = False
                    break
        else:
            player.send_message(f'{ColorFormat.RED}查询失败： {ColorFormat.WHITE}你的脚下没有任何领地...')

    # 查看服务器公开领地函数
    def server_public_land(self, player: Player):
        server_public_land_form = ActionForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}服务器公开领地',
            content=f'{ColorFormat.GREEN}请选择操作...',
            on_close=self.back_to_main_form
        )
        for key, value in self.land_data.items():
            land_owner = key
            land = value
            for key, value in land.items():
                land_name = key
                land_info = value
                range = []
                it = re.finditer(r'[-+]?\d+(?:\.\d+)?', land_info['range'])
                for i in it:
                    range.append(int(i.group()))
                if land_info['public_land'] == True:
                    server_public_land_form.add_button(f'{land_name}\n{ColorFormat.YELLOW}[领主] {land_owner} {land_info['dimension']}', icon='textures/ui/icon_spring',
                                                       on_click=self.server_public_land_details(land_owner, land_name, land_info['dimension'], land_info['range'],
                                                                                                land_info['area'], land_info['land_tp'], land_info['permissions']))
        server_public_land_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.back_to_main_form)
        player.send_form(server_public_land_form)

    # 查看服务器公开领地详情函数
    def server_public_land_details(self, land_owner, land_name, land_dimension, land_range, land_area, land_tp, land_permissions):
        def on_click(player: Player):
            server_public_land_details_form = ActionForm(
                title=land_name,
                content=f'{ColorFormat.YELLOW}领主： {ColorFormat.WHITE}{land_owner}\n'
                        f'{ColorFormat.YELLOW}维度： {ColorFormat.WHITE}{land_dimension}\n'
                        f'{ColorFormat.YELLOW}范围： {ColorFormat.WHITE}{land_range}\n'
                        f'{ColorFormat.YELLOW}面积： {ColorFormat.WHITE}{land_area}\n'
                        f'{ColorFormat.YELLOW}传送点： {ColorFormat.WHITE}({land_tp[0]}, {land_tp[1]}, {land_tp[2]})\n'
                        f'{ColorFormat.YELLOW}成员： {ColorFormat.WHITE}'
            )
            for member in land_permissions:
                server_public_land_details_form.content += member
            server_public_land_details_form.add_button(f'{ColorFormat.YELLOW}传送领地', icon='textures/ui/realmsIcon', on_click=self.tp_to_my_land(land_tp, land_dimension))
            server_public_land_details_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.server_public_land)
            player.send_form(server_public_land_details_form)
        return on_click

    # 保存领地数据函数
    def save_land_data(self):
        with open(land_data_file_path, 'w+', encoding='utf-8') as f:
            json_str = json.dumps(self.land_data, indent=4, ensure_ascii=False)
            f.write(json_str)

    # 领地系统配置函数
    def land_system_config(self, player: Player):
        land_system_config_form = ActionForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}领地系统配置',
            content=f'{ColorFormat.GREEN}请选择操作...',
            on_close=self.back_to_main_form
        )
        land_system_config_form.add_button(f'{ColorFormat.YELLOW}重载配置文件', icon='textures/ui/settings_glyph_color_2x', on_click=self.reload_config_data)
        land_system_config_form.add_button(f'{ColorFormat.YELLOW}重载领地数据', icon='textures/ui/settings_glyph_color_2x', on_click=self.reload_land_data)
        land_system_config_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.back_to_main_form)
        player.send_form(land_system_config_form)

    # 重載配置文件函数
    def reload_config_data(self, player :Player):
        textinput1 = TextInput(
            label=f'{ColorFormat.YELLOW}当前领地单价： {ColorFormat.WHITE}{self.config_data['land_buy_price']}',
            placeholder='请输入一个正整数, 例如：5'
        )
        textinput2 = TextInput(
            label=f'{ColorFormat.YELLOW}当前圈地最大耗时： {ColorFormat.WHITE}{self.config_data['land_create_timeout']}',
            placeholder='请输入一个不小于30的正整数, 例如: 30'
        )
        textinput3 = TextInput(
            label=f'{ColorFormat.YELLOW}当前允许的最大领地面积： {ColorFormat.WHITE}{self.config_data['max_area']}',
            placeholder='请输入一个不小于4的正整数, 例如：40000'
        )
        textinput4 = TextInput(
            label=f'{ColorFormat.YELLOW}当前允许玩家拥有的最大领地数量： {ColorFormat.WHITE}{self.config_data['max_land_per_player']}',
            placeholder='请输入一个正整数, 例如：3'
        )
        toggle = Toggle(
            label=f'{ColorFormat.YELLOW}开启领地回收价浮动'
        )
        if self.config_data['is_land_sell_rate_on'] == True:
            toggle.default_value = True
        else:
            toggle.default_value = False
        textinput5 = TextInput(
            label=f'{ColorFormat.YELLOW}当前领地回收冷却天数： {ColorFormat.WHITE}{self.config_data['land_sell_cool_down_timeout']}',
            placeholder='请输入一个不小于1的整数, 例如：3'
        )
        reload_config_data_form = ModalForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}重载配置文件表单',
            controls=[textinput1, textinput2, textinput3, textinput4, toggle, textinput5],
            on_close=self.back_to_main_form
        )
        def on_submit(player: Player, json_str):
            data = json.loads(json_str)
            try:
                if data[0] == '':
                    new_land_sell_price = self.config_data['land_buy_price']
                else:
                    new_land_sell_price = int(data[0])
                if data[1] == '':
                    new_land_create_timeout = self.config_data['land_create_timeout']
                else:
                    new_land_create_timeout = int(data[1])
                if data[2] == '':
                    new_max_area = self.config_data['max_area']
                else:
                    new_max_area = int(data[2])
                if data[3] == '':
                    new_max_land_per_player = self.config_data['max_land_per_player']
                else:
                    new_max_land_per_player = int(data[3])
                if data[5] == '':
                    new_land_sell_cool_down_timeout = self.config_data['land_sell_cool_down_timeout']
                else:
                    new_land_sell_cool_down_timeout = int(data[3])
            except:
                player.send_message(f'{ColorFormat.RED}表单解析错误, 请按提示正确填写...')
                return
            if (new_land_sell_price <= 0 or new_land_create_timeout < 30 or new_land_sell_cool_down_timeout < 1
                    or new_max_area < 4 or new_max_land_per_player <= 0):
                player.send_message(f'{ColorFormat.RED}表单解析错误, 请按提示正确填写...')
                return
            self.config_data['land_buy_price'] = new_land_sell_price
            self.config_data['land_create_timeout'] = new_land_create_timeout
            self.config_data['max_area'] = new_max_area
            self.config_data['max_land_per_player'] = new_max_land_per_player
            if data[4] == True:
                self.config_data['is_land_sell_rate_on'] = True
            else:
                self.config_data['is_land_sell_rate_on'] = False
            self.config_data['land_sell_cool_down_timeout'] = new_land_sell_cool_down_timeout
            with open(config_data_file_path, 'w+', encoding='utf-8') as f:
                json_str = json.dumps(self.config_data, indent=4, ensure_ascii=False)
                f.write(json_str)
            player.send_message(f'{ColorFormat.YELLOW}重载配置文件成功...')
        reload_config_data_form.on_submit = on_submit
        player.send_form(reload_config_data_form)

    # 重载领地数据函数
    def reload_land_data(self, player: Player):
        with open(land_data_file_path, 'r', encoding='utf-8') as f:
            self.land_data = json.loads(f.read())
        player.send_message(f'{ColorFormat.YELLOW}重载领地数据成功...')

    # 加载经济数据函数
    def load_money_data(self):
        with open(money_data_file_path, 'r', encoding='utf-8') as f:
            self.money_data = json.loads(f.read())

    # 保存经济数据函数
    def save_money_data(self):
        with open(money_data_file_path, 'w+', encoding='utf-8') as f:
            json_str = json.dumps(self.money_data, indent=4, ensure_ascii=False)
            f.write(json_str)

    # 监听玩家位置函数
    def check_player_pos(self):
        if len(self.server.online_players) == 0:
            return
        for online_player in self.server.online_players:
            player_pos = [math.floor(online_player.location.x), math.floor(online_player.location.z)]
            player_dimension = online_player.dimension.name
            flag = True
            for key, value in self.land_data.items():
                if flag ==  False:
                    break
                land_owner = key
                land = value
                for key, value in land.items():
                    land_name = key
                    land_info = value
                    range = []
                    it = re.finditer(r'[-+]?\d+(?:\.\d+)?', land_info['range'])
                    for i in it:
                        range.append(int(i.group()))
                    if (min(range[0], range[2]) <= player_pos[0] <= max(range[0], range[2])
                            and min(range[1], range[3]) <= player_pos[1] <= max(range[1], range[3])
                            and player_dimension == land_info['dimension']):
                        online_player.send_tip(f'你现在位于 {ColorFormat.YELLOW}{land_owner} {ColorFormat.WHITE}的领地 {land_name}')
                        flag = False
                        break

            '''player_pos = [int(online_player.location.x), int(online_player.location.z)]
            for land in self.land_list:
                land_owner = land[0]
                land_name = land[1]
                range = land[3]
                if (min(range[0], range[2]) <= player_pos[0] <= max(range[0], range[2])
                        and min(range[1], range[3]) <= player_pos[1] <= max(range[1], range[3])):
                    online_player.send_tip(f'你现在位于 {ColorFormat.YELLOW}{land_owner} {ColorFormat.WHITE}的领地 {land_name}')
                    break'''

    def back_to_main_form(self, player: Player):
        player.perform_command('ul')

    def back_to_menu(self, player: Player):
        player.perform_command('cd')

    @event_handler
    def on_player_join(self, event: PlayerJoinEvent):
        if not self.land_data.get(event.player.name):
            self.land_data[event.player.name] = {}
            self.save_land_data()

    # 监听方块破坏函数
    @event_handler
    def on_block_break(self, event: BlockBreakEvent):
        block_pos = [math.floor(event.block.location.x), math.floor(event.block.location.z)]
        block_dimension = event.block.dimension.name
        source_player = event.player
        for key, value in self.land_data.items():
            land_owner = key
            land = value
            for key, value in land.items():
                land_info = value
                range = []
                it = re.finditer(r'[-+]?\d+(?:\.\d+)?', land_info['range'])
                for i in it:
                    range.append(int(i.group()))
                if (min(range[0], range[2]) <= block_pos[0] <= max(range[0], range[2])
                        and min(range[1], range[3]) <= block_pos[1] <= max(range[1], range[3])
                        and block_dimension == land_info['dimension']
                        and land_info['anti_break_block'] == True
                        and (source_player.name != land_owner and source_player.name not in land_info['permissions'])):
                    event.player.send_message(f'{ColorFormat.RED}你无权在此领地破坏方块...')
                    event.cancelled = True

    # 监听特定生物生成函数，例如水晶引起的爆炸 和 闪电引起的着火
    @event_handler
    def on_mob_spawn(self, event: ActorSpawnEvent):
        # 测试用代码...
        '''self.logger.info(event.actor.name)'''
        if event.actor.name == 'Ender Crystal' or event.actor.name == 'Lightning Bolt':
            actor_pos =[math.floor(event.actor.location.x), math.floor(event.actor.location.z)]
            actor_dimension = event.actor.dimension.name
            for value in self.land_data.values():
                land = value
                for value in land.values():
                    land_info = value
                    range =[]
                    it = re.finditer(r'[-+]?\d+(?:\.\d+)?', land_info['range'])
                    for i in it:
                        range.append(int(i.group()))
                    land_len_x = round(abs(range[0] - range[2]) / 2)
                    land_len_z = round(abs(range[1] - range[3]) / 2)
                    land_center_x = min(range[0], range[2]) + land_len_x
                    land_center_z = min(range[1], range[3]) + land_len_z
                    if land_info['fire_protect'] == True and event.actor.name == 'Lightning Bolt':
                        prevent_l_bolt_dx = land_len_x + 3
                        prevent_l_bolt_dz = land_len_z + 3
                        prevent_l_bolt_posa = [land_center_x + prevent_l_bolt_dx, land_center_z + prevent_l_bolt_dz]
                        prevent_l_bolt_posb = [land_center_x - prevent_l_bolt_dx, land_center_z - prevent_l_bolt_dz]
                        if (min(prevent_l_bolt_posa[0], prevent_l_bolt_posb[0]) <= actor_pos[0] <= max(prevent_l_bolt_posa[0], prevent_l_bolt_posb[0])
                                and min(prevent_l_bolt_posa[1], prevent_l_bolt_posb[1]) <= actor_pos[1] <= max(prevent_l_bolt_posa[1], prevent_l_bolt_posb[1])
                                and actor_dimension == land_info['dimension']):
                            event.cancelled = True
                    if land_info['tnt_explode_protect'] == True and event.actor.name == 'Ender Crystal':
                        prevent_crystal_dx = land_len_x + 14
                        prevent_crystal_dz = land_len_x + 14
                        prevent_crystal_posa = [land_center_x + prevent_crystal_dx, land_center_z + prevent_crystal_dz]
                        prevent_crystal_posb = [land_center_x - prevent_crystal_dx, land_center_z - prevent_crystal_dz]
                        if (min(prevent_crystal_posa[0], prevent_crystal_posb[0]) <= actor_pos[0] <= max(prevent_crystal_posa[0], prevent_crystal_posb[0])
                                and min(prevent_crystal_posa[1], prevent_crystal_posb[1]) <= actor_pos[1] <= max(prevent_crystal_posa[1], prevent_crystal_posb[1])
                                and actor_dimension == land_info['dimension']):
                            event.cancelled = True
        else:
            return

    # 监听玩家攻击函数
    # 待 API 完善继续写
    def on_player_attack(self, event: ActorKnockbackEvent):
        mob_under_attack_pos = [math.floor(event.actor.location.x), math.floor(event.actor.location.z)]
        mob_under_attack_dimension = event.actor.dimension.name
        source_mob = event.source
        if source_mob != Player:
            return
        source_player = source_mob
        for key, value in self.land_data.items():
            land_owner = key
            land = value
            for key, value in land.items():
                land_info = value
                range = []
                it = re.finditer(r'[-+]?\d+(?:\.\d+)?', land_info['range'])
                for i in it:
                    range.append(int(i.group()))
                if (min(range[0], range[2]) <= mob_under_attack_pos[0] <= max(range[0], range[2])
                        and min(range[1], range[3]) <= mob_under_attack_pos[1] <= max(range[1], range[3])
                        and mob_under_attack_dimension == land_info['dimension']
                        and (source_player.name != land_owner and source_player.name not in land_info['permissions'])):
                    event.source.send_message(f'{ColorFormat.RED}你无权在此领地攻击生物...')
                    event.cancelled = True

    # 监听玩家右键方块函数
    @event_handler
    def on_player_right_click_block(self, event: PlayerInteractEvent):
        block_pos = [math.floor(event.block.location.x),math.floor(event.block.location.z)]
        block_dimension = event.block.dimension.name
        source_player = event.player
        for key, value in self.land_data.items():
            land_owner = key
            land = value
            for key, value in land.items():
                land_info = value
                range = []
                it = re.finditer(r'[-+]?\d+(?:\.\d+)?', land_info['range'])
                for i in it:
                    range.append(int(i.group()))
                if (min(range[0], range[2]) <= block_pos[0] <= max(range[0], range[2])
                        and min(range[1], range[3]) <= block_pos[1] <= max(range[1], range[3])
                        and block_dimension == land_info['dimension']
                        and land_info['anti_right_click_block'] == True
                        and (source_player.name != land_owner and source_player.name not in land_info['permissions'])):
                    source_player.send_message(f'{ColorFormat.RED}你无权在此领地右键交互方块...')
                    event.cancelled = True

    # 监听玩家右键 Mob 函数
    @event_handler
    def on_player_right_click_entity(self, event: PlayerInteractActorEvent):
        actor_pos = [math.floor(event.actor.location.x), math.floor(event.actor.location.z)]
        actor_dimension = event.actor.dimension.name
        source_player = event.player
        for key, value in self.land_data.items():
            land_owner = key
            land = value
            for key, value in land.items():
                land_info = value
                range = []
                it = re.finditer(r'[-+]?\d+(?:\.\d+)?', land_info['range'])
                for i in it:
                    range.append(int(i.group()))
                if (min(range[0], range[2]) <= actor_pos[0] <= max(range[0], range[2])
                        and min(range[1], range[3]) <= actor_pos[1] <= max(range[1], range[3])
                        and actor_dimension == land_info['dimension']
                        and land_info['anti_right_click_entity'] == True
                        and (source_player.name != land_owner and source_player.name not in land_info['permissions'])):
                    source_player.send_message(f'{ColorFormat.RED}你无权在此领地右键交互生物...')
                    event.cancelled = True

    # 领地 TNT 防爆, 防 Creeper, wither, fireball 周期任务函数
    def land_protect_task(self):
        if len(self.server.online_players) == 0:
            return
        for value in self.land_data.values():
            land = value
            for value in land.values():
                land_info = value
                range = []
                it = re.finditer(r'[-+]?\d+(?:\.\d+)?', land_info['range'])
                for i in it:
                    range.append(int(i.group()))
                land_dimension = land_info['dimension']
                if land_dimension == 'Overworld':
                    execute_dimension = 'overworld'
                elif land_dimension == 'Nether':
                    execute_dimension = 'nether'
                else:
                    execute_dimension = 'the_end'
                land_len_x = round(abs(range[0] - range[2]) / 2)
                land_len_z = round(abs(range[1] - range[3]) / 2)
                land_center_x = min(range[0], range[2]) + land_len_x
                land_center_z = min(range[1], range[3]) + land_len_z
                if land_info['fire_protect'] == True:
                    fire_ball_protect_dx = land_len_x + 5
                    fire_ball_protect_dz = land_len_z + 5
                    fire_ball_protect_posa = [land_center_x + fire_ball_protect_dx, land_center_z + fire_ball_protect_dz]
                    self.server.dispatch_command(self.CommandSenderWrapper, f'execute in {execute_dimension} run '
                                                                            f'kill @e[type=small_fireball, x={fire_ball_protect_posa[0]}, y=320, z={fire_ball_protect_posa[1]}, '
                                                                            f'dx={-fire_ball_protect_dx*2}, dy=-384, dz={-fire_ball_protect_dz*2}]')
                    self.server.dispatch_command(self.CommandSenderWrapper, f'execute in {execute_dimension} run '
                                                                            f'kill @e[type=fireball, x={fire_ball_protect_posa[0]}, y=320, z={fire_ball_protect_posa[1]}, '
                                                                            f'dx={-fire_ball_protect_dx * 2}, dy=-384, dz={-fire_ball_protect_dz * 2}]')
                if land_info['tnt_explode_protect'] == True:
                    tnt_protect_dx = land_len_x + 7
                    tnt_protect_dz = land_len_z + 7
                    tnt_protect_posa = [land_center_x + tnt_protect_dx, land_center_z + tnt_protect_dz]
                    self.server.dispatch_command(self.CommandSenderWrapper, f'execute in {execute_dimension} run '
                                                                            f'kill @e[type=tnt, x={tnt_protect_posa[0]}, y=320, z={tnt_protect_posa[1]}, '
                                                                            f'dx={-tnt_protect_dx*2}, dy=-384, dz={-tnt_protect_dz*2}]')
                if land_info['mob_grief_protect'] == True:
                    creeper_protect_dx = land_len_x + 5
                    creeper_protect_dz = land_len_z + 5
                    creeper_protect_posa = [land_center_x + creeper_protect_dx, land_center_z + creeper_protect_dz]
                    wither_protect_dx = land_len_x + 20
                    wither_protect_dz = land_len_z + 20
                    wither_protect_posa = [land_center_x + wither_protect_dx, land_center_z + wither_protect_dz]
                    self.server.dispatch_command(self.CommandSenderWrapper, f'execute in {execute_dimension} run '
                                                                            f'tp @e[type=creeper, x={creeper_protect_posa[0]}, y=320, z={creeper_protect_posa[1]}, '
                                                                            f'dx={-creeper_protect_dx*2}, dy=-384, dz={-creeper_protect_dz*2}] 0 -100 0')
                    self.server.dispatch_command(self.CommandSenderWrapper, f'execute in {execute_dimension} run '
                                                                            f'tp @e[type=wither, x={wither_protect_posa[0]}, y=320, z={wither_protect_posa[1]}, '
                                                                            f'dx={-wither_protect_dx*2}, dy=-384, dz={-wither_protect_dz*2}] 0 -100 0')
                    self.server.dispatch_command(self.CommandSenderWrapper, f'execute in {execute_dimension} run '
                                                                            f'kill @e[type=wither, x=0, y=-100, z=0, r=20]')