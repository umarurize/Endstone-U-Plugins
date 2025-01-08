import json
import os
import math
from endstone import Player, ColorFormat
from endstone.plugin import Plugin
from endstone.level import Location
from endstone.command import Command, CommandSender
from endstone.form import ActionForm, ModalForm, TextInput, Toggle

current_dir = os.getcwd()
first_dir = os.path.join(current_dir, 'plugins', 'u-worldboarder')
if not os.path.exists(first_dir):
    os.mkdir(first_dir)
config_data_file_path = os.path.join(first_dir, 'config.json')

class u_worldboarder(Plugin):
    api_version = '0.5'

    def on_enable(self):
        if not os.path.exists(config_data_file_path):
            config_data = {
                'Overworld': {
                    'center': [0, 0],
                    'radius': 10000,
                    'is_on': True
                },
                'Nether': {
                    'center': [0, 0],
                    'radius': 10000,
                    'is_on': False
                },
                'TheEnd': {
                    'center': [0, 0],
                    'radius': 10000,
                    'is_on': False
                }
            }
            with open(config_data_file_path, 'w', encoding='utf-8') as f:
                json_str = json.dumps(config_data, indent=4, ensure_ascii=False)
                f.write(json_str)
        else:
            with open(config_data_file_path, 'r', encoding='utf-8') as f:
                config_data = json.loads(f.read())
        self.config_data = config_data
        self.server.scheduler.run_task(self, self.check_player_pos, delay=0, period=20)
        self.logger.info(f'{ColorFormat.YELLOW}U-Worldboarder 启用成功...')

    commands = {
        'ubd': {
            'description': '打开世界边界表单',
            'usages': ['/ubd'],
            'permissions': ['u_worldboarder.command.ubd']
        }
    }

    permissions = {
        'u_worldboarder.command.ubd': {
            'description': '打开世界边界表单',
            'default': True
        }
    }

    def on_command(self, sender: CommandSender, command: Command, args: list[str]):
        if not isinstance(sender, Player):
            sender.send_message(f'{ColorFormat.RED}该命令只能由玩家执行...')
            return
        player = sender
        if command.name == 'ubd':
            main_form = ActionForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}世界边界主表单',
                content=f'{ColorFormat.GREEN}请选择操作...',
                on_close=None
            )
            main_form.add_button(f'{ColorFormat.YELLOW}查询世界边界信息', icon='textures/ui/world_glyph_color', on_click=self.worldboarder_info)
            if player.is_op == True:
                main_form.add_button(f'{ColorFormat.YELLOW}将脚下坐标设置为世界中心', icon='textures/ui/icon_new_item', on_click=self.set_world_center)
                main_form.add_button(f'{ColorFormat.YELLOW}配置世界边界', icon='textures/ui/hammer_l', on_click=self.configure_worldboarder)
            main_form.add_button(f'{ColorFormat.YELLOW}关闭', icon='textures/ui/realms_red_x', on_click=None)
            player.send_form(main_form)

    # 查询世界边界信息函数
    def worldboarder_info(self, player: Player):
        worldboarder_info_form = ActionForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}世界边界信息',
            content=f'{ColorFormat.YELLOW}[主世界]\n'
                    f'{ColorFormat.YELLOW}世界中心： '
                    f'{ColorFormat.WHITE}({self.config_data['Overworld']['center'][0]}, ~, {self.config_data['Overworld']['center'][1]})\n'
                    f'{ColorFormat.YELLOW}最大活动半径： '
                    f'{ColorFormat.WHITE}{self.config_data['Overworld']['radius']}\n'
                    f'{ColorFormat.YELLOW}状态： '
                    f'{ColorFormat.WHITE}{'开启' if self.config_data['Overworld']['is_on'] == True else '关闭'}\n\n'
                    f'{ColorFormat.YELLOW}[地狱]\n'
                    f'{ColorFormat.YELLOW}世界中心： '
                    f'{ColorFormat.WHITE}({self.config_data['Nether']['center'][0]}, ~, {self.config_data['Nether']['center'][1]})\n'
                    f'{ColorFormat.YELLOW}最大活动半径： '
                    f'{ColorFormat.WHITE}{self.config_data['Nether']['radius']}\n'
                    f'{ColorFormat.YELLOW}状态： '
                    f'{ColorFormat.WHITE}{'开启' if self.config_data['Nether']['is_on'] == True else '关闭'}\n\n'
                    f'{ColorFormat.YELLOW}[末地]\n'
                    f'{ColorFormat.YELLOW}世界中心： '
                    f'{ColorFormat.WHITE}({self.config_data['TheEnd']['center'][0]}, ~, {self.config_data['TheEnd']['center'][1]})\n'
                    f'{ColorFormat.YELLOW}最大活动半径： '
                    f'{ColorFormat.WHITE}{self.config_data['TheEnd']['radius']}\n'
                    f'{ColorFormat.YELLOW}状态： '
                    f'{ColorFormat.WHITE}{'开启' if self.config_data['TheEnd']['is_on'] == True else '关闭'}',
            on_close=self.back_to_main_form
        )
        worldboarder_info_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.back_to_main_form)
        player.send_form(worldboarder_info_form)

    # 将脚下坐标设置为世界中心函数
    def set_world_center(self, player: Player):
        player_dimension = player.dimension.name
        player_pos = [math.floor(player.location.x), math.floor(player.location.z)]
        set_world_center_form = ActionForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}设置世界中心点',
            on_close=self.back_to_main_form
        )
        if player_dimension == 'Overworld':
            set_world_center_form.content = (f'{ColorFormat.GREEN}你确定要将主世界的世界中心设置为： '
                                             f'{ColorFormat.WHITE}({player_pos[0]}, ~, {player_pos[1]})')
        elif player_dimension == 'Nether':
            set_world_center_form.content = (f'{ColorFormat.GREEN}你确定要将地狱的世界中心设置为： '
                                             f'{ColorFormat.WHITE}({player_pos[0]}, ~, {player_pos[1]})')
        else:
            set_world_center_form.content = (f'{ColorFormat.GREEN}你确定要将末地的世界中心设置为： '
                                             f'{ColorFormat.WHITE}({player_pos[0]}, ~, {player_pos[1]})')
        set_world_center_form.add_button(f'{ColorFormat.YELLOW}确认', icon='textures/ui/realms_green_check',
                                         on_click=self.on_confirm(player_dimension, player_pos))
        set_world_center_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.back_to_main_form)
        player.send_form(set_world_center_form)

    def on_confirm(self, dimension, pos):
        def on_click(player: Player):
            if dimension == 'Overworld':
                self.config_data['Overworld']['center'] = pos
            elif dimension == 'Nether':
                self.config_data['Nether']['center'] = pos
            else:
                self.config_data['TheEnd']['center'] = pos
            self.save_config_data()
            player.send_message(f'{ColorFormat.YELLOW}世界中心设置成功...')
        return on_click

    # 配置世界边界函数
    def configure_worldboarder(self, player: Player):
        # 主世界
        textinput1 = TextInput(
            label=f'{ColorFormat.YELLOW}当前主世界世界中心： '
                  f'{ColorFormat.WHITE}({self.config_data['Overworld']['center'][0]}, ~, {self.config_data['Overworld']['center'][1]})\n'
                  f'{ColorFormat.YELLOW}当前主世界允许最大活动半径为： '
                  f'{ColorFormat.WHITE}{self.config_data['Overworld']['radius']}',
            placeholder=f'请输入一个正整数, 例如：10000'
        )
        toggle1 = Toggle(
            label=f'{ColorFormat.YELLOW}开启主世界世界边界'
        )
        if self.config_data['Overworld']['is_on'] == True:
            toggle1.default_value = True
        else:
            toggle1.default_value = False
        # 地狱
        textinput2 = TextInput(
            label=f'\n{ColorFormat.YELLOW}当前地狱世界中心： '
                  f'{ColorFormat.WHITE}({self.config_data['Nether']['center'][0]}, ~, {self.config_data['Nether']['center'][1]})\n'
                  f'{ColorFormat.YELLOW}当前地狱允许最大活动半径为： '
                  f'{ColorFormat.WHITE}{self.config_data['Nether']['radius']}',
            placeholder=f'请输入一个正整数, 例如：10000'
        )
        toggle2 = Toggle(
            label=f'{ColorFormat.YELLOW}开启地狱世界边界'
        )
        if self.config_data['Nether']['is_on'] == True:
            toggle2.default_value = True
        else:
            toggle2.default_value = False
        # 末地
        textinput3 = TextInput(
            label=f'\n{ColorFormat.YELLOW}当前末地世界中心： '
                  f'{ColorFormat.WHITE}({self.config_data['TheEnd']['center'][0]}, ~, {self.config_data['TheEnd']['center'][1]})\n'
                  f'{ColorFormat.YELLOW}当前末地允许最大活动半径为： '
                  f'{ColorFormat.WHITE}{self.config_data['TheEnd']['radius']}',
            placeholder=f'请输入一个正整数, 例如：10000'
        )
        toggle3 = Toggle(
            label=f'{ColorFormat.YELLOW}开启末地世界边界'
        )
        if self.config_data['TheEnd']['is_on'] == True:
            toggle3.default_value = True
        else:
            toggle3.default_value = False
        configure_worldboarder_form = ModalForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}世界边界配置表单',
            controls=[textinput1, toggle1, textinput2, toggle2, textinput3, toggle3],
            on_close=self.back_to_main_form
        )
        def on_submit(player: Player, json_str):
            data = json.loads(json_str)
            try:
                if data[0] == '':
                    new_overworld_radius = self.config_data['Overworld']['radius']
                else:
                    new_overworld_radius = int(data[0])
                if data[2] == '':
                    new_nether_radius = self.config_data['Nether']['radius']
                else:
                    new_nether_radius = int(data[2])
                if data[4] == '':
                    new_the_end_radius = self.config_data['TheEnd']['radius']
                else:
                    new_the_end_radius = int(data[4])
            except:
                player.send_message(f'{ColorFormat.RED}表单解析错误, 请按提示正确填写...')
                return
            if (new_overworld_radius < 0
                    or new_nether_radius < 0
                    or new_the_end_radius < 0):
                player.send_message(f'{ColorFormat.RED}表单解析错误, 请按提示正确填写...')
                return
            self.config_data['Overworld']['radius'] = new_overworld_radius
            self.config_data['Nether']['radius'] = new_nether_radius
            self.config_data['TheEnd']['radius'] = new_the_end_radius
            if data[1] == True:
                self.config_data['Overworld']['is_on'] = True
            else:
                self.config_data['Overworld']['is_on'] = False
            if data[3] == True:
                self.config_data['Nether']['is_on'] = True
            else:
                self.config_data['Nether']['is_on'] = False
            if data[5] == True:
                self.config_data['TheEnd']['is_on'] = True
            else:
                self.config_data['TheEnd']['is_on'] = False
            self.save_config_data()
            player.send_message(f'{ColorFormat.YELLOW}配置成功...')
        configure_worldboarder_form.on_submit = on_submit
        player.send_form(configure_worldboarder_form)

    # 检查玩家位置函数
    def check_player_pos(self):
        if len(self.server.online_players) == 0:
            return
        for online_player in self.server.online_players:
            online_player_dimension = online_player.dimension.name
            online_player_pos = [math.floor(online_player.location.x), math.floor(online_player.location.z), math.floor(online_player.location.y)]
            online_player_radius = ((online_player_pos[0] - self.config_data[online_player_dimension]['center'][0])**2 +
                                    (online_player_pos[1] - self.config_data[online_player_dimension]['center'][1])**2)**0.5
            if (online_player_radius > self.config_data[online_player_dimension]['radius']
                    and self.config_data[online_player_dimension]['is_on'] == True):
                # 计算超出半径长度
                over_radius = online_player_radius - self.config_data[online_player_dimension]['radius']
                # 根据相似三角形计算退格长度
                ratio = over_radius / online_player_radius
                back_len_x = int(abs(online_player_pos[0] - self.config_data[online_player_dimension]['center'][0]) * ratio) + 1
                back_len_y = int(abs(online_player_pos[1] - self.config_data[online_player_dimension]['center'][1]) * ratio) + 1
                if online_player_pos[0] < self.config_data[online_player_dimension]['center'][0]:
                    tp_pos_x = online_player_pos[0] + back_len_x
                elif online_player_pos[0] > self.config_data[online_player_dimension]['center'][0]:
                    tp_pos_x = online_player_pos[0] - back_len_x
                else:
                    tp_pos_x = online_player_pos[0]
                if online_player_pos[1] < self.config_data[online_player_dimension]['center'][1]:
                    tp_pos_z = online_player_pos[1] + back_len_y
                elif online_player_pos[1] > self.config_data[online_player_dimension]['center'][1]:
                    tp_pos_z = online_player_pos[1] - back_len_y
                else:
                    tp_pos_z = online_player_pos[1]
                tp_pos_y = online_player_pos[2]
                self.back_tp(online_player, online_player_dimension, tp_pos_x, tp_pos_z, tp_pos_y)

    # 玩家退格 tp 函数
    def back_tp(self, online_player, online_player_dimension, tp_pos_x, tp_pos_z, tp_pos_y):
        if online_player.is_op == True:
            return
        if online_player_dimension == 'Overworld':
            tp_dimension = self.server.level.get_dimension('OVERWORLD')
        elif online_player_dimension == 'Nether':
            tp_dimension = self.server.level.get_dimension('NETHER')
        else:
            tp_dimension = self.server.level.get_dimension('THE_END')
        location = Location(
            tp_dimension,
            x=tp_pos_x,
            y=tp_pos_y,
            z=tp_pos_z
        )
        online_player.teleport(location)
        online_player.send_message(f'{ColorFormat.RED}你不能越过边界...')
        online_player.send_message(f'{ColorFormat.RED}你已被拉回： {ColorFormat.WHITE}({tp_pos_x}, {tp_pos_y}, {tp_pos_z})')

    # 保存配置文件数据函数
    def save_config_data(self):
        with open(config_data_file_path, 'w+', encoding='utf-8') as f:
            json_str = json.dumps(self.config_data, indent=4, ensure_ascii=False)
            f.write(json_str)

    # 返回主表单函数
    def back_to_main_form(self, player: Player):
        player.perform_command('ubd')