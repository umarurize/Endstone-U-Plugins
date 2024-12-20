import json
import os
from endstone import ColorFormat, Player
from endstone.plugin import Plugin
from endstone.command import Command, CommandSender, CommandSenderWrapper
from endstone.form import ActionForm, ModalForm, TextInput, Dropdown
from endstone.event import event_handler, PlayerChatEvent, PlayerJoinEvent, PlayerQuitEvent

current_dir = os.getcwd()
first_dir = os.path.join(current_dir, 'plugins', 'ubc')
if not os.path.exists(first_dir):
    os.mkdir(first_dir)
config_data_file_path = os.path.join(first_dir, 'config.json')
nick_name_data_file_path = os.path.join(first_dir, 'nickname.json')
bad_words_data_file_path = os.path.join(first_dir, 'badwords.json')
online_time_data_file_path = os.path.join(first_dir, 'online_time.json')
money_data_file_path = os.path.join(current_dir, 'plugins', 'money', 'money.json')

class u_beautiful_chat(Plugin):
    api_version = '0.5'

    def on_enable(self):
        # 加载配置文件
        if not os.path.exists(config_data_file_path):
            config_data = {
                'variable_order': 'dim++health++money++time++ping++device',
                'nick_name_len': 6,
                'update_nick_name_cost': 10,
                'player_join_notice_sound': 'note.bell'
            }
            with open(config_data_file_path, 'w', encoding='utf-8') as f:
                json_str = json.dumps(config_data, indent=4, ensure_ascii=False)
                f.write(json_str)
        else:
            with open(config_data_file_path, 'r', encoding='utf-8') as f:
                config_data = json.loads(f.read())
        self.config_data = config_data
        # 加载不文明用语数据文件
        if not os.path.exists(bad_words_data_file_path):
            bad_words_data = []
            with open(bad_words_data_file_path, 'w', encoding='utf-8') as f:
                json_str = json.dumps(bad_words_data, indent=4, ensure_ascii=False)
                f.write(json_str)
        else:
            with open(bad_words_data_file_path, 'r', encoding='utf-8') as f:
                bad_words_data = json.loads(f.read())
        self.bad_words_data = bad_words_data
        # 加载玩家称号数据文件
        if not os.path.exists(nick_name_data_file_path):
            nick_name_data = {}
            with open(nick_name_data_file_path, 'w', encoding='utf-8') as f:
                json_str = json.dumps(nick_name_data, indent=4, ensure_ascii=False)
                f.write(json_str)
        else:
            with open(nick_name_data_file_path, 'r', encoding='utf-8') as f:
                nick_name_data = json.loads(f.read())
        self.nick_name_data = nick_name_data
        # 加载玩家在线时间数据文件
        if not os.path.exists(online_time_data_file_path):
            online_time_data = {}
            with open(online_time_data_file_path, 'w', encoding='utf-8') as f:
                json_str = json.dumps(online_time_data, indent=4, ensure_ascii=False)
                f.write(json_str)
        else:
            with open(online_time_data_file_path, 'r', encoding='utf-8') as f:
                online_time_data = json.loads(f.read())
        self.online_time_data = online_time_data
        self.server.scheduler.run_task(self, self.online_time_task, delay=0, period=1200)
        # 加载玩家经济数据文件
        if not os.path.exists(money_data_file_path):
            self.logger.info(f'{ColorFormat.RED}缺少必备前置 jsonmoney...')
        else:
            with open(money_data_file_path, 'r', encoding='utf-8') as f:
                money_data = json.loads(f.read())
        self.money_data = money_data
        self.CommandSenderWrapper = CommandSenderWrapper(
            self.server.command_sender,
            on_message=None
        )
        self.register_events(self)
        self.logger.info(f'{ColorFormat.YELLOW}U-Beautiful-Chat 已启用...')

    commands = {
        'ubc': {
            'description': '打开 UBC 主表单',
            'usages': ['/ubc'],
            'permissions': ['u_beautiful_chat.command.ubc']
        }
    }

    permissions = {
        'u_beautiful_chat.command.ubc': {
            'description': '打开 UBC 主表单',
            'default': True
        }
    }

    def on_command(self, sender: CommandSender, command: Command, args: list[str]):
        if command.name == 'ubc':
            if not isinstance(sender, Player):
                sender.send_message(f'{ColorFormat.YELLOW}该命令只能由玩家执行...')
                return
            player = sender
            ubc_main_form = ActionForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}UBC 主表单',
                content=f'{ColorFormat.GREEN}请选择操作...',
                on_close=None
            )
            ubc_main_form.add_button(f'{ColorFormat.YELLOW}设置称号', icon='textures/ui/filledStarFocus', on_click=self.set_nick_name)
            if player.is_op == True:
                ubc_main_form.add_button(f'{ColorFormat.YELLOW}设置专属称号', icon='textures/ui/filledStar', on_click=self.set_unique_nick_name)
                ubc_main_form.add_button(f'{ColorFormat.YELLOW}屏蔽不文明用语', icon='textures/ui/comment', on_click=self.block_shit_words)
                ubc_main_form.add_button(f'{ColorFormat.YELLOW}重载配置文件', icon='textures/ui/icon_setting', on_click=self.set_config_data)
            ubc_main_form.add_button(f'{ColorFormat.YELLOW}关闭表单', icon='textures/ui/realms_red_x', on_click=None)
            player.send_form(ubc_main_form)

    # 设置个人称号
    def set_nick_name(self, player: Player):
        player_nick_name = self.get_player_nick_name(player)
        update_nick_name_cost = self.config_data['update_nick_name_cost']
        textinput = TextInput(
            label=f'{ColorFormat.GREEN}当前称号： {ColorFormat.WHITE}{player_nick_name}\n'
                  f'{ColorFormat.GREEN}更新称号耗费： {ColorFormat.WHITE}{update_nick_name_cost}',
            placeholder=f'请输入任意字符串, 但不要超过{self.config_data['nick_name_len']}个字, 留空则清空'
        )
        set_nick_name_form = ModalForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}设置称号',
            controls=[textinput],
            submit_button=f'{ColorFormat.YELLOW}更新',
            on_submit=self.back_to_main_form
        )
        def on_submit(player: Player, json_str):
            self.load_money_data()
            if not self.money_data.get(player.name):
                player.send_message(f'{ColorFormat.RED}称号设置失败： {ColorFormat.WHITE}余额不足...')
                return
            if self.money_data[player.name] < update_nick_name_cost:
                player.send_message(f'{ColorFormat.RED}称号设置失败： {ColorFormat.WHITE}余额不足...')
                return
            data = json.loads(json_str)
            if len(data[0]) > self.config_data['nick_name_len']:
                player.send_message(f'{ColorFormat.RED}称号设置失败： {ColorFormat.WHITE}称号长度超过{self.config_data['nick_name_len']}个字符...')
                return
            if data[0] in self.bad_words_data:
                player.send_message(f'{ColorFormat.RED}称号设置失败： {ColorFormat.WHITE}{data[0]} 是不文明用语...')
                return
            if len(data[0]) == 0:
                player.send_message(f'{ColorFormat.YELLOW}称号设置成功： {ColorFormat.WHITE}称号已清空...')
            else:
                player.send_message(f'{ColorFormat.YELLOW}称号设置成功...')
            self.nick_name_data[player.name]['nick_name'] = data[0]
            self.money_data[player.name] -= update_nick_name_cost
            self.save_nick_name_data()
            self.save_money_data()
        set_nick_name_form.on_submit = on_submit
        player.send_form(set_nick_name_form)

    # 管理员为玩家设置专属称号
    def set_unique_nick_name(self, player: Player):
        player_name_list = [player_name for player_name in self.nick_name_data.keys()]
        dropdown = Dropdown(
            label=f'{ColorFormat.GREEN}请选择玩家...',
            options=player_name_list
        )
        set_unique_nick_name_form = ModalForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}设置专属称号',
            controls=[dropdown],
            submit_button=f'{ColorFormat.YELLOW}确认',
            on_close=self.back_to_main_form
        )
        def on_submit(player: Player, json_str):
            data = json.loads(json_str)
            target_player_name = player_name_list[data[0]]
            self.set_unique_nick_name_details(player, target_player_name)
        set_unique_nick_name_form.on_submit = on_submit
        player.send_form(set_unique_nick_name_form)

    # 管理员详细设置玩家专属称号
    def set_unique_nick_name_details(self, player: Player, target_player_name):
        player_unique_nick_name = self.nick_name_data[target_player_name]['unique_nick_name']
        if len(player_unique_nick_name) == 0:
            player_unique_nick_name = '无'
        textinput = TextInput(
            label=f'{ColorFormat.GREEN}当前该玩家的专属称号： {ColorFormat.WHITE}{player_unique_nick_name}',
            placeholder=f'请输入任意字符串, 但不要超过{self.config_data['nick_name_len']}个字, 留空则清空'
        )
        set_unique_nick_name_details_form = ModalForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}设置玩家 {target_player_name} 的专属称号',
            controls=[textinput],
            submit_button=f'{ColorFormat.YELLOW}更新',
            on_close=self.set_unique_nick_name
        )
        def on_submit(player: Player, json_str):
            data = json.loads(json_str)
            if len(data[0]) > self.config_data['nick_name_len']:
                player.send_message(
                    f'{ColorFormat.RED}专属称号设置失败： {ColorFormat.WHITE}称号长度超过{self.config_data['nick_name_len']}个字符...')
                return
            if len(data[0]) == 0:
                player.send_message(f'{ColorFormat.YELLOW}专属称号设置成功： {ColorFormat.WHITE}专属称号已清空...')
            else:
                player.send_message(f'{ColorFormat.YELLOW}专属称号设置成功...')
            self.nick_name_data[target_player_name]['unique_nick_name'] = data[0]
            self.save_nick_name_data()
        set_unique_nick_name_details_form.on_submit = on_submit
        player.send_form(set_unique_nick_name_details_form)

    # 屏蔽不文明用语
    def block_shit_words(self, player: Player):
        block_shit_words_form = ActionForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}屏蔽不文明用语',
            content=f'{ColorFormat.GREEN}请选择操作...',
            on_close=self.back_to_main_form
        )
        block_shit_words_form.add_button(f'{ColorFormat.YELLOW}添加不文明用语', icon='textures/ui/color_plus', on_click=self.add_shit_words)
        block_shit_words_form.add_button(f'{ColorFormat.YELLOW}删除不文明用语', icon='textures/ui/realms_red_x', on_click=self.delete_shit_words)
        block_shit_words_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.back_to_main_form)
        player.send_form(block_shit_words_form)

    # 添加不文明用语
    def add_shit_words(self, player: Player):
        textinput = TextInput(
            label=f'{ColorFormat.GREEN}请输入目标屏蔽词, 不能为空...',
            placeholder='请输入任意字符串...'
        )
        add_shit_words_form = ModalForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}添加不文明用语',
            controls=[textinput],
            submit_button=f'{ColorFormat.YELLOW}添加',
            on_close=self.block_shit_words
        )
        def on_submit(player: Player, json_str):
            data = json.loads(json_str)
            if len(data[0]) == 0:
                player.send_message(f'{ColorFormat.RED}表单解析错误, 请按提示正确填写...')
                return
            shit_word_to_add = data[0]
            if shit_word_to_add in self.bad_words_data:
                player.send_message(f'{ColorFormat.RED}添加失败： {ColorFormat.WHITE}{shit_word_to_add}已存在, 不能重复添加...')
                return
            self.bad_words_data.append(shit_word_to_add)
            self.save_bad_words_data()
            player.send_message(f'{ColorFormat.RED}屏蔽词 {ColorFormat.WHITE}{shit_word_to_add} {ColorFormat.RED}已添加...')
        add_shit_words_form.on_submit = on_submit
        player.send_form(add_shit_words_form)

    # 删除不文明用语
    def delete_shit_words(self, player: Player):
        dropdown = Dropdown(
            label=f'{ColorFormat.GREEN}请选择目标屏蔽词...',
            options=self.bad_words_data
        )
        delete_shit_words_form = ModalForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}删除不文明用语...',
            controls=[dropdown],
            submit_button=f'{ColorFormat.YELLOW}删除',
            on_close=self.block_shit_words
        )
        def on_submit(player: Player, json_str):
            data = json.loads(json_str)
            shit_word_to_delete = self.bad_words_data[data[0]]
            self.bad_words_data.remove(shit_word_to_delete)
            self.save_bad_words_data()
            player.send_message(f'{ColorFormat.RED}屏蔽词 {ColorFormat.WHITE}{shit_word_to_delete} {ColorFormat.RED}已删除...')
        delete_shit_words_form.on_submit = on_submit
        player.send_form(delete_shit_words_form)

    # 管理员配置全局设置
    def set_config_data(self, player: Player):
        current_variable_order = self.config_data['variable_order']
        if len(current_variable_order) == 0:
            current_variable_order = '已禁用'
        textinput1 = TextInput(
            label=f'{ColorFormat.GREEN}当前变量显示设置：\n'
                  f'{ColorFormat.WHITE}{current_variable_order}\n'
                  f'\n'
                  f'{ColorFormat.GREEN}当前支持的变量： \n'
                  f'{ColorFormat.WHITE}[维度]dim [生命]health [金币]money\n'
                  f'[延迟]ping [设备]device [在线时长]time\n'
                  f'\n'
                  f'{ColorFormat.GREEN}可只填单个变量, 也可自由组合多个变量\n'
                  f'{ColorFormat.GREEN}如使用多个变量，请用 {ColorFormat.WHITE}++ {ColorFormat.GREEN}连接\n'
                  f'{ColorFormat.GREEN}填 {ColorFormat.WHITE}clear {ColorFormat.GREEN}禁用变量显示',
            placeholder='例如： money 或 money++health++ping 或 clear'
        )
        textinput2 = TextInput(
            label=f'\n\n'
                  f'{ColorFormat.GREEN}当前允许称号的最大字数： {ColorFormat.WHITE}{self.config_data['nick_name_len']}',
            placeholder='请输入一个正整数, 例如：6'
        )
        textinput3 = TextInput(
            label=f'\n\n'
                  f'{ColorFormat.GREEN}当前玩家更新称号耗费： {ColorFormat.WHITE}{self.config_data['update_nick_name_cost']}',
            placeholder='请输入一个正整数或0, 例如：10 或 0'
        )
        textinput4 = TextInput(
            label=f'\n\n'
                  f'{ColorFormat.GREEN}当前玩家进服音效： {ColorFormat.WHITE}{self.config_data['player_join_notice_sound']}',
            placeholder='请输入音效代码'
        )
        set_config_data_form = ModalForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}重载配置文件',
            controls=[textinput1, textinput2, textinput3, textinput4],
            submit_button=f'{ColorFormat.YELLOW}重载',
            on_close=self.back_to_main_form
        )
        def on_submit(player: Player, json_str):
            data = json.loads(json_str)
            try:
                if data[0] == 'clear':
                    new_variable_order = ''
                elif len(data[0]) == 0:
                    new_variable_order = self.config_data['variable_order']
                else:
                    new_variable_order = data[0]
                if len(data[1]) == 0:
                    new_nick_name_len = self.config_data['nick_name_len']
                else:
                    new_nick_name_len = int(data[1])
                if len(data[2]) == 0:
                    new_update_nick_name_cost = self.config_data['update_nick_name_cost']
                else:
                    new_update_nick_name_cost = int(data[2])
                if len(data[3]) == 0:
                    new_player_join_notice_sound = self.config_data['player_join_notice_sound']
                else:
                    new_player_join_notice_sound = data[3]
            except:
                player.send_message(f'{ColorFormat.RED}表单解析错误, 请按提示正确填写...')
                return
            if new_nick_name_len <= 0 or new_update_nick_name_cost < 0:
                player.send_message(f'{ColorFormat.RED}表单解析错误, 请按提示正确填写...')
                return
            self.config_data['variable_order'] = new_variable_order
            self.config_data['nick_name_len'] = new_nick_name_len
            self.config_data['update_nick_name_cost'] = new_update_nick_name_cost
            self.config_data['player_join_notice_sound'] = new_player_join_notice_sound
            self.save_config_data()
            player.send_message(f'{ColorFormat.YELLOW}重载配置文件成功...')
        set_config_data_form.on_submit = on_submit
        player.send_form(set_config_data_form)

    # 记录玩家在线时间
    def online_time_task(self):
        if len(self.server.online_players) == 0:
            return
        for online_player in self.server.online_players:
            self.online_time_data[online_player.name] += 1
        self.save_online_time_data()

    # 获取玩家维度
    def get_player_dimension(self, player: Player):
        player_dimension_name = player.dimension.name
        if player_dimension_name == 'Overworld':
            dimension_to_show = f'{ColorFormat.GREEN}主世界'
        elif player_dimension_name == 'Nether':
            dimension_to_show = f'{ColorFormat.RED}地狱'
        else:
            dimension_to_show = f'{ColorFormat.LIGHT_PURPLE}末地'
        return dimension_to_show

    # 获取玩家生命
    def get_player_health(self, player: Player):
        player_health = player.health
        player_health_to_show = f'{ColorFormat.RED}生命：{player_health}'
        return player_health_to_show

    # 获取玩家在线时间
    def get_player_online_time(self, player: Player):
        player_online_time = self.online_time_data[player.name]
        player_online_time_to_show = f'{ColorFormat.AQUA}在线时长：{player_online_time}'
        return player_online_time_to_show

    # 获取玩家经济
    def get_player_money(self, player: Player):
        self.load_money_data()
        if not self.money_data.get(player.name):
            player_money_to_show = f'{ColorFormat.YELLOW}金币：None'
        else:
            player_money = self.money_data[player.name]
            player_money_to_show = f'{ColorFormat.YELLOW}金币：{player_money}'
        return player_money_to_show

    # 获取玩家延迟
    def get_player_ping(self, player: Player):
        player_ping = player.ping
        player_ping_to_show = f'{ColorFormat.GREEN}延迟：{player_ping}'
        return player_ping_to_show

    # 获取玩家操作系统
    def get_player_device_os(self, player: Player):
        player_device_os = player.device_os
        player_device_os_to_show = f'{ColorFormat.MATERIAL_DIAMOND}设备：{player_device_os}'
        return player_device_os_to_show

    # 获取玩家称号
    def get_player_nick_name(self, player: Player):
        player_nick_name = self.nick_name_data[player.name]['nick_name']
        if len(player_nick_name) == 0:
            player_nick_name_to_show = '无'
        else:
            player_nick_name_to_show = player_nick_name
        return player_nick_name_to_show

    # 获取玩家专属称号
    def get_player_unique_nick_name(self, player: Player):
        player_unique_nick_name = self.nick_name_data[player.name]['unique_nick_name']
        if len(player_unique_nick_name) == 0:
            player_unique_nick_name_to_show = '无'
        else:
            player_unique_nick_name_to_show = player_unique_nick_name
        return player_unique_nick_name_to_show

    # 监听玩家聊天
    @event_handler
    def on_player_chat(self, event: PlayerChatEvent):
        player_name = event.player.name
        player_message = event.message
        for bad_word in self.bad_words_data:
            if bad_word in player_message:
                player_message = player_message.replace(bad_word, '#'*len(bad_word))
        if len(self.config_data['variable_order']) == 0:
            variable_to_show_string = ''
        else:
            variable_order_list = self.config_data['variable_order'].split('++')
            variable_to_show_string = '['
            for variable in variable_order_list:
                if variable == 'dim':
                    variable_to_add = self.get_player_dimension(event.player)
                elif variable == 'health':
                    variable_to_add = self.get_player_health(event.player)
                elif variable == 'time':
                    variable_to_add = self.get_player_online_time(event.player)
                elif variable == 'money':
                    variable_to_add = self.get_player_money(event.player)
                elif variable == 'ping':
                    variable_to_add = self.get_player_ping(event.player)
                else:
                    variable_to_add = self.get_player_device_os(event.player)
                variable_to_show_string += variable_to_add
                if variable_order_list.index(variable) != len(variable_order_list) - 1:
                    variable_to_show_string += f'{ColorFormat.RESET} | '
                else:
                    variable_to_show_string += f'{ColorFormat.RESET}]'
        player_nick_name = self.get_player_nick_name(event.player)
        player_unique_nick_name = self.get_player_unique_nick_name(event.player)
        if player_unique_nick_name != '无':
            variable_to_show_string += f'{ColorFormat.RESET} @{player_unique_nick_name}{ColorFormat.RESET}'
        if player_nick_name != '无':
            variable_to_show_string += f'{ColorFormat.RESET} [{player_nick_name}{ColorFormat.RESET}]'
        event.cancelled = True
        self.server.broadcast_message(f'{variable_to_show_string} {player_name} >> {player_message}')

    def save_online_time_data(self):
        with open(online_time_data_file_path, 'w+', encoding='utf-8') as f:
            json_str = json.dumps(self.online_time_data, indent=4, ensure_ascii=False)
            f.write(json_str)

    def save_nick_name_data(self):
        with open(nick_name_data_file_path, 'w+', encoding='utf-8') as f:
            json_str = json.dumps(self.nick_name_data, indent=4, ensure_ascii=False)
            f.write(json_str)

    def save_bad_words_data(self):
        with open(bad_words_data_file_path, 'w+', encoding='utf-8') as f:
            json_str = json.dumps(self.bad_words_data, indent=4, ensure_ascii=False)
            f.write(json_str)

    def save_config_data(self):
        with open(config_data_file_path, 'w+', encoding='utf-8') as f:
            json_str = json.dumps(self.config_data, indent=4, ensure_ascii=False)
            f.write(json_str)

    def load_money_data(self):
        if not os.path.exists(money_data_file_path):
            self.logger.info(f'{ColorFormat.RED}缺少必备前置 jsonmoney...')
        else:
            with open(money_data_file_path, 'r', encoding='utf-8') as f:
                money_data = json.loads(f.read())
        self.money_data = money_data

    def save_money_data(self):
        with open(money_data_file_path, 'w+', encoding='utf-8') as f:
            json_str = json.dumps(self.money_data, indent=4, ensure_ascii=False)
            f.write(json_str)

    # 返回主表单
    def back_to_main_form(self, player: Player):
        player.perform_command('ubc')

    # 监听玩家加入游戏和退出游戏
    @event_handler
    def on_player_join(self, event: PlayerJoinEvent):
        # 初始化玩家在线时间
        if not self.online_time_data.get(event.player.name):
            self.online_time_data[event.player.name] = 0
        self.save_online_time_data()
        # 初始玩家称号数据
        if not self.nick_name_data.get(event.player.name):
            self.nick_name_data[event.player.name] = {
                'nick_name': '',
                'unique_nick_name': ''
            }
        self.save_nick_name_data()
        event.join_message = (f'{ColorFormat.BOLD}{ColorFormat.GREEN}[+] {ColorFormat.RESET}{ColorFormat.WHITE}{event.player.name} 加入了游戏...')
        self.server.dispatch_command(self.CommandSenderWrapper, f'playsound {self.config_data['player_join_notice_sound']} @a')

    @event_handler
    def on_player_left(self, event: PlayerQuitEvent):
        event.quit_message = f'{ColorFormat.BOLD}{ColorFormat.RED}[-] {ColorFormat.RESET}{ColorFormat.WHITE}{event.player.name} 暂时离开了...'
