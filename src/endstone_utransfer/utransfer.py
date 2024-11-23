import json
import os
import requests
import threading
from endstone import ColorFormat, Player
from endstone.event import event_handler, PlayerQuitEvent
from endstone.command import Command, CommandSender
from endstone.plugin import Plugin
from endstone.form import ActionForm


# 获取插件当前目录
current_dir = os.getcwd()
first_dir = os.path.join(current_dir, 'plugins', 'utransfer')
server_file_path = os.path.join(first_dir, 'server.json')
config_file_path = os.path.join(first_dir, 'config.json')
# 建立 utransfer 文件夹，用来存放 server.json 和 config.json
try:
    os.mkdir(first_dir)
except:
    pass

class utransfer(Plugin):
    api_version = '0.5'

    # on_load 函数会在服务器加载时自动调用
    def on_enable(self):
        # 尝试加载服务器列表配置文件，否则建立默认服务器列表配置文件
        try:
            with open(server_file_path, 'r', encoding='utf-8') as f:
                server_list = json.loads(f.read())
        except:
            default_server_list = [
                {
                'name': 'Misaki',
                'ip': 'play.misaki.host',
                'port': 25601
                },
                {
                'name': 'mcfun',
                'image': 'textures/items/apple',
                'ip': 's3.mcvps.vip',
                'port': 12345
                }
            ]
            with open(server_file_path, 'w', encoding='utf-8') as f:
                json_str = json.dumps(default_server_list, indent=4, ensure_ascii=False)
                f.write(json_str)
            server_list = default_server_list
            self.logger.info(f'{ColorFormat.YELLOW}默认服务器列表配置文件已生成，位置：{server_file_path}')
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config_data= json.loads(f.read())
        except:
            default_config_data = {
                'server_form_title': '跨服传送表单',
                'server_form_content': '请选择操作...',
                'confirm_form_title': '确认表单',
                'confirm_form_content': '请选择操作...',
                'notice': '玩家 {0} 正在前往服务器 {1}...',
                'notice_sound': 'note.bell'
            }
            with open(config_file_path, 'w', encoding='utf-8') as f:
                json_str = json.dumps(default_config_data, indent=4, ensure_ascii=False)
                f.write(json_str)
            config_data = default_config_data
            self.logger.info(f'{ColorFormat.YELLOW}默认配置文件已生成，位置：{config_file_path}')
        self.config_data = config_data
        self.server_list = server_list
        self.server_status_dict = {} # 缓存服务器状态数据
        self.on_transfer_flag = False # 跨服标识
        self.on_transfer_info = [] # 缓存正在跨服的玩家数据
        self.task = self.server.scheduler.run_task(self, self.update_server_status, delay=0, period=200)
        self.register_events(self)
        self.logger.info(f'{ColorFormat.YELLOW}utransfer 已加载...')

    commands = {
        'tr': {
            'description': '打开跨服传送表单',
            'usages': ['/tr'],
            'permissions': ['utransfer.command.tr']
        }
    }

    permissions = {
        'utransfer.command.tr': {
            'description': '打开跨服传送表单',
            'default': True
        }
    }

    def on_command(self, sender: CommandSender, command: Command, args: list[str]):
        if not isinstance(sender, Player):
            sender.send_message(f'{ColorFormat.YELLOW}该命令只能由玩家执行...')
            return
        player = sender
        if command.name == 'tr':
            server_list_form = ActionForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}{self.config_data['server_form_title']}',
                content=f'{ColorFormat.GREEN}{self.config_data['server_form_content']}'
            )
            for server in self.server_list:
                server_name = server['name']
                server_ip = server['ip']
                server_port = server['port']
                temple_dict = self.server_status_dict[server_name]
                try:
                    server_image = server['image']
                    server_list_form.add_button(f'{server_name}\n{temple_dict['server_is_online']} {temple_dict['server_online_status']}-{temple_dict['server_version']}', icon=server_image, on_click=self.on_confirm(server_name, server_ip, server_port))
                except:
                    server_list_form.add_button(f'{server_name}\n{temple_dict['server_is_online']} {temple_dict['server_online_status']}-{temple_dict['server_version']}', on_click=self.on_confirm(server_name, server_ip, server_port))
            if player.is_op == True:
                server_list_form.add_button('重载配置文件', icon='textures/ui/icon_setting', on_click=self.reload_config_data)
            server_list_form.add_button('关闭表单', icon='textures/ui/cancel', on_click=None)
            player.send_form(server_list_form)

    def on_confirm(self, server_name, server_ip, server_port):
        def on_click(player: Player):
            confirm_form = ActionForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}{self.config_data['confirm_form_title']}',
                content=f'{ColorFormat.GREEN}{self.config_data['confirm_form_content']}'
            )
            confirm_form.add_button('确认', icon='textures/ui/check', on_click=self.on_transfer(server_name, server_ip, server_port))
            confirm_form.add_button('取消', icon='textures/ui/cancel', on_click=None)
            self.server.get_player(player.name).send_form(confirm_form)
        return on_click

    def on_transfer(self, server_name, server_ip, server_port):
        def on_click(player: Player):
            self.server.get_player(player.name).transfer(server_ip, server_port)
            self.on_transfer_info = [player.name, server_name]
            self.on_transfer_flag = True
        return on_click

    def reload_config_data(self, player: Player):
        with open(server_file_path, 'r', encoding='utf-8') as f:
            self.server_list = json.loads(f.read())
        with open(config_file_path, 'r', encoding='utf-8') as f:
            self.config_data = json.loads(f.read())
        player.send_message('所有配置文件已重载...')

    def update_server_status(self):
        threading.Thread(target=self.update_server_status_thread).start()

    def update_server_status_thread(self):
        for server in self.server_list:
            server_version = f'{ColorFormat.RED}版本：**'
            server_online_status = f'{ColorFormat.RED}**'
            server_is_online = f'{ColorFormat.RED}离线'
            try:
                api_url = f'https://api.mcstatus.io/v2/status/bedrock/{server['ip']}:{server['port']}'
                response = requests.get(api_url)
                if response.status_code == 200:
                    response_content = response.json()
                    server_online_player_num = response_content['players']['online']
                    server_max_player_num = response_content['players']['max']
                    server_version = f'{ColorFormat.BLUE}版本：{response_content['version']['name']}'
                    server_online_status = f'{ColorFormat.YELLOW}{str(server_online_player_num)}/{str(server_max_player_num)}'
                    server_is_online = f'{ColorFormat.GREEN}在线'
                    response.close()
            except:
                pass
            self.server_status_dict[server['name']] = {'server_is_online': server_is_online, 'server_online_status': server_online_status, 'server_version': server_version}

    @event_handler
    def on_player_left(self, event: PlayerQuitEvent):
        if self.on_transfer_flag == False:
            return
        else:
            event.quit_message = self.config_data['notice'].format(self.on_transfer_info[0], self.on_transfer_info[1])
            self.server.dispatch_command(self.server.command_sender, f'playsound {self.config_data['notice_sound']} @a')
            self.on_transfer_info = []
            self.on_transfer_flag = False