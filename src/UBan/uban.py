import datetime
import json
import os
from endstone import ColorFormat, Player
from endstone.plugin import Plugin
from endstone.command import CommandSender, Command
from endstone.event import event_handler, PlayerJoinEvent, PlayerChatEvent
from endstone.form import ActionForm, Dropdown, TextInput, ModalForm

current_dir = os.getcwd()
first_dir = os.path.join(current_dir, 'plugins', 'uban')
player_list_file_path = os.path.join(first_dir, 'player.json')
banlist_file_path = os.path.join(first_dir, 'banlist.data')
badwords_list_file_path = os.path.join(first_dir, 'badwords.json')
report_list_file_path = os.path.join(first_dir, 'report-list.json')
config_file_path = os.path.join(first_dir, 'config.json')
try:
    os.mkdir(first_dir)
except:
    pass

class uban(Plugin):
    api_version = '0.5'

    def on_enable(self):
        report_list_data =[]
        player_list_data = []
        banlist_data = []
        badwords_list_data = []
        try:
            f = open(player_list_file_path, 'r', encoding='utf-8')
            player_list_data = json.loads(f.read())
            f.close()
        except:
            f = open(player_list_file_path, 'w', encoding='utf-8')
            f.close()
        try:
            f1 = open(banlist_file_path, 'r', encoding='utf-8')
            banlist_data = json.loads(f1.read())
            f1.close()
        except:
            f1 = open(banlist_file_path, 'w', encoding='utf-8')
            f1.close()
        try:
            f2 = open(badwords_list_file_path, 'r', encoding='utf-8')
            badwords_list_data = json.loads(f2.read())
            f2.close()
        except:
            f2 = open(badwords_list_file_path, 'w', encoding='utf-8')
            f2.close()
        try:
            f3 = open(report_list_file_path, 'r', encoding='utf-8')
            report_list_data = json.loads(f3.read())
            f3.close()
        except:
            f3 = open(report_list_file_path, 'w', encoding='utf-8')
            f3.close()
        try:
            f4 = open(config_file_path, 'r', encoding='utf-8')
            config = json.loads(f4.read())
            f4.close()
            self.logger.info(f'配置文件加载成功...')
        except:
            f4 = open(config_file_path, 'w', encoding='utf-8')
            default_config = {'interval': 10, 'title_len': 10, 'content_len': 30}
            config = default_config
            json_str = json.dumps(default_config, indent=4)
            f4.write(json_str)
            f4.close()
            self.logger.info(f'已生成默认配置文件，位置：{config_file_path}')
        self.player_list = player_list_data
        self.banlist = banlist_data
        self.badwords_list = badwords_list_data
        self.report_list = report_list_data
        self.config_data = config
        self.register_events(self)
        self.logger.info(f'{ColorFormat.YELLOW}uban 已启用...')

    commands = {
        'ban': {
            'description': '打开封禁功能主表单',
            'usages': ['/ban'],
            'permissions': ['uban.command.ban']
        }
    }

    permissions = {
        'uban.command.ban': {
            'description': '打开封禁功能主表单',
            'default': True
        }
    }

    def on_command(self, sender: CommandSender, command: Command, args: list[str]):
        if command.name == 'ban':
            if not isinstance(sender, Player):
                sender.send_message(f'{ColorFormat.YELLOW}该命令只能由玩家执行...')
                return
            player = sender
            if player.is_op == True:
                main_form_op = ActionForm(
                    title='封禁玩家主表单-管理版',
                    content='请选择操作...'
                )
                main_form_op.add_button('查看玩家举报', icon='textures/ui/mail_icon', on_click=self.list_report_info)
                main_form_op.add_button('封禁在线玩家', icon='textures/ui/dressing_room_customization', on_click=self.ban_online_player)
                main_form_op.add_button('封禁离线玩家', icon='textures/ui/friend_glyph_desaturated',on_click=self.ban_offline_player)
                main_form_op.add_button('查看封禁列表', icon='textures/ui/lock_color', on_click=self.list_banlist)
                main_form_op.add_button('屏蔽不文明用语', icon='textures/ui/comment', on_click=self.ban_badwords)
                main_form_op.add_button('重载配置文件', icon='textures/ui/icon_setting', on_click=self.reload_config_data)
                main_form_op.add_button('关闭表单', icon='textures/ui/cancel', on_click=None)
                player.send_form(main_form_op)
            else:
                mian_form_player = ActionForm(
                    title='封禁玩家主表单-玩家版',
                    content='请选择操作...'
                )
                mian_form_player.add_button('我的举报', icon='textures/ui/mail_icon', on_click=self.personal_report)
                mian_form_player.add_button('查看封禁列表', icon='textures/ui/lock_color', on_click=self.list_banlist)
                mian_form_player.add_button('关闭表单', icon='textures/ui/cancel', on_click=None)
                player.send_form(mian_form_player)

    # 封禁在线玩家表单
    def ban_online_player(self, p: Player):
        dropdown = Dropdown(
            label='请选择玩家...',
            options= [online_player.name for online_player in self.server.online_players]
        )
        textinput =TextInput(
            label='封禁原因',
            placeholder='请输入任意字符串（选填）'
        )
        ban_online_player_form = ModalForm(
            title='封禁在线玩家表单',
            controls=[dropdown, textinput],
            submit_button='确认',
            on_close=None
        )
        def on_submit(p, json_str):
            data = json.loads(json_str)
            target_player = self.server.online_players[data[0]]
            if data[1] == '':
                ban_reason = '无'
            else:
                ban_reason = data[1]
            if p.name == target_player.name:
                p.send_message(f'{ColorFormat.RED}封禁失败：你不能封禁你自己...')
                return
            if target_player.is_op == True:
                p.send_message(f'{ColorFormat.RED}封禁失败：你不能直接封禁一名管理员，请先取消他的管理员身份...')
                return
            self.on_ban_online_player(p, target_player, ban_reason)
        ban_online_player_form.on_submit = on_submit
        p.send_form(ban_online_player_form)

    # 执行封禁在线玩家
    def on_ban_online_player(self, p: Player, target_player: Player, ban_reason):
        ban_name = target_player.name
        ban_xuid = target_player.xuid
        ban_uuid = str(target_player.unique_id)
        ban_ip = target_player.address.hostname
        ban_requester = p.name
        self.banlist.append([ban_name, ban_reason, ban_xuid, ban_uuid, ban_ip, ban_requester])
        self.server.broadcast_message(f'{ColorFormat.RED}玩家 {ban_name} 已被封禁，原因：{ban_reason}')
        target_player.kick(f'你已被服务器封禁，原因：{ban_reason}')
        self.save_banlist_data()

    # 封禁离线玩家表单
    def ban_offline_player(self, p: Player):
        textinput1 =TextInput(
            label='目标封禁玩家',
            placeholder='请输入玩家游戏名...'
        )
        textinput2 = TextInput(
            label='封禁原因',
            placeholder='请输入任意字符串（选填）'
        )
        ban_offline_player_form = ModalForm(
            title='封禁离线玩家表单',
            controls=[textinput1, textinput2],
            submit_button='确认',
            on_close=None
        )
        def on_submit(p, json_str):
            data = json.loads(json_str)
            target_player_name = data[0]
            if len(data[1]) == 0:
                ban_reason = '无'
            else:
                ban_reason = data[1]
            if p.name == target_player_name:
                return
            for player in self.player_list:
                if player[0] == target_player_name:
                    if player[4] == 'op':
                        p.send_message(f'{ColorFormat.RED}封禁失败：你不能直接封禁一名管理员，请先取消他的管理员身份...')
                        return
                    else:
                        break
            else:
                p.send_message(f'{ColorFormat.RED}封禁失败：该玩家从未出现在你的服务器，请检查目标封禁玩家名是否正确...')
                return
            self.on_ban_offline_player(p, target_player_name, ban_reason)
        ban_offline_player_form.on_submit = on_submit
        p.send_form(ban_offline_player_form)

    # 执行封禁离线玩家
    def on_ban_offline_player(self, p: Player, target_player_name, ban_reason):
        for banned_player in self.banlist:
            if banned_player[0] == target_player_name:
                p.send_message(f'{ColorFormat.RED}该玩家已经在封禁列表中，无法重复封禁...')
                return
        for player in self.player_list:
            if player[0] == target_player_name:
                ban_xuid = player[1]
                ban_uuid = player[2]
                ban_ip = player[3]
                break
        ban_name = target_player_name
        ban_requester = p.name
        self.banlist.append([ban_name, ban_reason, ban_xuid, ban_uuid, ban_ip, ban_requester])
        self.server.broadcast_message(f'{ColorFormat.RED}玩家 {ban_name} 已被封禁，原因：{ban_reason}')
        try:
            self.server.get_player(target_player_name).kick(f'你已被服务器封禁，原因：{ban_reason}')
        except:
            pass
        self.save_banlist_data()

    # 查看封禁列表
    def list_banlist(self, p: Player):
        banlist_form = ActionForm(
            title='黑名单',
            content='请选择操作...'
        )
        for banned_player in self.banlist:
            banlist_form.add_button(f'{banned_player[0]}', on_click=self.banned_player_info(banned_player[0], banned_player[1], banned_player[2], banned_player[3], banned_player[4], banned_player[5]))
        banlist_form.add_button('关闭表单',icon='textures/ui/cancel', on_click=None)
        p.send_form(banlist_form)

    # 查看封禁玩家信息和解封玩家按钮
    def banned_player_info(self, ban_name, ban_reason, ban_xuid, ban_uuid, ban_ip, ban_requester):
        def on_click(p: Player):
            banned_player_info_form = ActionForm(
                title=f'{ban_name}',
                content=f'游戏名：{ban_name}\n'
                        f'封禁原因：{ban_reason}\n'
                        f'xuid：{ban_xuid}\n'
                        f'uuid：{ban_uuid}\n'
                        f'ip地址：{ban_ip}\n'
                        f'执行者：{ban_requester}'
            )
            if p.is_op == True:
                banned_player_info_form.add_button('解封', icon='textures/ui/icon_unlocked', on_click=self.on_unban(ban_name))
                banned_player_info_form.add_button('关闭表单', icon='textures/ui/cancel', on_click=None)
            p.send_form(banned_player_info_form)
        return on_click

    # 执行解封玩家
    def on_unban(self, ban_name):
        def on_click(p: Player):
            for banned_player in self.banlist:
                if banned_player[0] == ban_name:
                    self.banlist.remove(banned_player)
                    self.save_banlist_data()
                    p.send_message(f'{ColorFormat.YELLOW}玩家 {ban_name} 已解封...')
        return on_click

    # 添加不文明用语表单
    def ban_badwords(self, p: Player):
        textinput = TextInput(
            label='目标屏蔽词汇',
            placeholder='请输入任意字符串...'
        )
        ban_badwords_form = ModalForm(
            title='添加不文明用语表单',
            controls=[textinput],
            submit_button='确认',
            on_close=None
        )
        def on_submit(p, json_str):
            data = json.loads(json_str)
            if len(data[0]) == 0:
                p.send_message(f'{ColorFormat.RED}屏蔽词不能是空字符串...')
                return
            if data[0] in self.badwords_list:
                p.send_message(f'{ColorFormat.RED}该词语已经在屏蔽词列表中，无法重复添加...')
                return
            self.badwords_list.append(data[0])
            p.send_message(f'{ColorFormat.RED}屏蔽词 {data[0]} 已添加...')
            self.save_badwords_list_data()
        ban_badwords_form.on_submit = on_submit
        p.send_form(ban_badwords_form)

    # 查看个人举报内容列表
    def personal_report(self, p: Player):
        self.check_time()
        personal_report_form = ActionForm(
            title='我的举报',
            content=f'仅显示{self.config_data['interval']}天内的内容'
        )
        for report_info in self.report_list:
            if report_info[0] == p.name:
                personal_report_form.add_button(f'{report_info[1]}{ColorFormat.RED}[{report_info[6]}]\n{ColorFormat.GREEN}{report_info[3]}/{report_info[4]}/{report_info[5]}', on_click=self.cancel_personal_report(report_info[1], report_info[2], report_info[3], report_info[4], report_info[5], report_info[6]))
        personal_report_form.add_button('创建新举报', icon='textures/ui/color_plus', on_click=self.create_new_report)
        personal_report_form.add_button('关闭表单', icon='textures/ui/cancel', on_click=None)
        p.send_form(personal_report_form)

    # 玩家创建新的举报请求
    def create_new_report(self, p: Player):
        textinput1 = TextInput(
            label='举报标题',
            placeholder=f'举报内容不能为空，但不要超过{self.config_data['title_len']}个字'
        )
        textinput2 = TextInput(
            label='举报内容',
            placeholder=f'举报内容不能为空，但不要超过{self.config_data['content_len']}个字'
        )
        create_new_report_form = ModalForm(
            title='创建新举报',
            controls=[textinput1, textinput2],
            submit_button='发送',
            on_close=None
        )
        def on_submit(p, json_str):
            data = json.loads(json_str)
            if len(data[0]) == 0 or len(data[0]) > self.config_data['title_len'] or len(data[1]) == 0 or len(data[1]) > self.config_data['content_len']:
                p.send_message(f'{ColorFormat.RED}创建举报失败：请按照提示正确填写...')
                return
            current_time = str(datetime.datetime.now()).split(' ')[0].split('-')
            self.report_list.append([p.name, data[0], data[1], int(current_time[0]), int(current_time[1]), int(current_time[2]), '未受理'])
            self.save_report_data()
            p.send_message(f'{ColorFormat.YELLOW}举报成功...')
        create_new_report_form.on_submit = on_submit
        p.send_form(create_new_report_form)

    # 向玩家展示自己举报的详细内容，并在未受理的情况下，添加撤销举报按钮，允许撤销
    def cancel_personal_report(self, title, content, year, month, day, status):
        def on_click(p: Player):
            cancel_personal_report_form = ActionForm(
                title='举报详情',
                content=f'举报标题：{title}\n'
                        f'举报内容：{content}\n'
                        f'举报时间：{year}/{month}/{day}\n'
                        f'举报状态:{status}'
            )
            if status == '未受理':
                cancel_personal_report_form.add_button('撤销举报', icon='textures/ui/refresh_light', on_click=self.on_cancel_personal_report(title))
            cancel_personal_report_form.add_button('关闭表单', icon='textures/ui/cancel', on_click=None)
            p.send_form(cancel_personal_report_form)
        return on_click

    # 玩家撤销举报
    def on_cancel_personal_report(self, title):
        def on_click(p: Player):
            for report_info in self.report_list:
                if report_info[1] == title:
                    self.report_list.remove(report_info)
                    self.save_report_data()
                    p.send_message(f'{ColorFormat.YELLOW}撤销成功...')
                    break
        return on_click

    # 列出所有玩家举报并处理
    def list_report_info(self, p: Player):
        self.check_time()
        list_report_info_form = ActionForm(
            title='来自玩家的举报',
            content=f'仅显示{self.config_data['interval']}天内的内容',
        )
        for report_info in self.report_list:
            if report_info[6] == '未受理':
                list_report_info_form.add_button(f'{report_info[0]}-{ColorFormat.GREEN}{report_info[3]}/{report_info[4]}/{report_info[5]}\n{ColorFormat.BLACK}{report_info[1]}', on_click=self.send_process_report_form(report_info[0], report_info[1], report_info[2]))
        list_report_info_form.add_button('关闭表单', icon='textures/ui/cancel', on_click=None)
        p.send_form(list_report_info_form)

    # 向管理员发送处理举报表单
    def send_process_report_form(self, reporter_name, title, content):
        def on_click(p: Player):
            process_report_form = ActionForm(
                title=f'来自玩家 {reporter_name} 的举报',
                content=f'举报标题：{title}\n举报内容：{content}'
            )
            process_report_form.add_button('确认受理', icon='textures/ui/confirm', on_click=self.on_process_report(title))
            process_report_form.add_button('暂不受理', icon='textures/ui/cancel', on_click=None)
            p.send_form(process_report_form)
        return on_click

    # 处理举报
    def on_process_report(self, title):
        def on_click(p: Player):
            for report_info in self.report_list:
                if report_info[1] == title:
                    report_info[6] = '已受理'
                    self.save_report_data()
                    p.send_message(f'{ColorFormat.YELLOW}受理成功...')
                    break
        return on_click

    # 保存玩家信息
    def save_player_list_data(self):
        f = open(player_list_file_path, 'w+', encoding='utf-8')
        json_str = json.dumps(self.player_list, indent=4, ensure_ascii=False)
        f.write(json_str)
        f.close()

    # 保存不文明词汇信息
    def save_badwords_list_data(self):
        f = open(badwords_list_file_path, 'w+', encoding='utf-8')
        json_str = json.dumps(self.badwords_list, indent=4, ensure_ascii=False)
        f.write(json_str)
        f.close()

    # 保存封禁玩家信息
    def save_banlist_data(self):
        f = open(banlist_file_path, 'w+', encoding='utf-8')
        json_str = json.dumps(self.banlist, indent=4, ensure_ascii=False)
        f.write(json_str)
        f.close()

    # 重载配置文件
    def reload_config_data(self, p: Player):
        f = open(config_file_path, 'r', encoding='utf-8')
        config = json.loads(f.read())
        self.config_data = config
        f.close()
        p.send_message(f'{ColorFormat.YELLOW}配置文件重载成功...')

    # 检测举报内容时效性
    def check_time(self):
        pre_current_time = str(datetime.datetime.now()).split(' ')[0].split('-')
        current_time = datetime.datetime(int(pre_current_time[0]), int(pre_current_time[1]), int(pre_current_time[2]))
        for report_info in self.report_list:
            record_time = datetime.datetime(report_info[3], report_info[4], report_info[5])
            interval = current_time - record_time
            if interval.days > self.config_data['interval']:
                self.report_list.remove(report_info)
        self.save_report_data()

    # 保存举报内容
    def save_report_data(self):
        f = open(report_list_file_path, 'w+', encoding='utf-8')
        json_str = json.dumps(self.report_list, indent=4, ensure_ascii=False)
        f.write(json_str)
        f.close()

    @event_handler
    def on_player_join(self, event: PlayerJoinEvent):
        if event.player.name not in [player[0] for player in self.player_list]:
            if event.player.is_op:
                self.player_list.append([event.player.name, event.player.xuid, str(event.player.unique_id), event.player.address.hostname, 'op'])
            else:
                self.player_list.append([event.player.name, event.player.xuid, str(event.player.unique_id), event.player.address.hostname, 'member'])
            self.save_player_list_data()
        for banned_player in self.banlist:
            if event.player.xuid == banned_player[2]:
                event.player.kick(f'你已被服务器封禁, 原因：{banned_player[1]}')

    @event_handler
    def on_player_chat(self, event: PlayerChatEvent):
        for badwords in self.badwords_list:
            if badwords in event.message:
                event.message = event.message.replace(badwords, '*'*len(badwords))
                break
        else:
            pass