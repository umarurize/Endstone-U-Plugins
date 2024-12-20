import datetime
import json
import os
from endstone import ColorFormat, Player
from endstone.plugin import Plugin
from endstone.command import CommandSender, Command, CommandSenderWrapper
from endstone.event import event_handler, PlayerJoinEvent, PlayerInteractEvent
from endstone.form import ActionForm, Dropdown, TextInput, ModalForm

current_dir = os.getcwd()
first_dir = os.path.join(current_dir, 'plugins', 'uban')
if not os.path.exists(first_dir):
    os.mkdir(first_dir)
player_list_file_path = os.path.join(first_dir, 'player.json')
banlist_file_path = os.path.join(first_dir, 'banlist.json')
report_list_file_path = os.path.join(first_dir, 'report.json')
banitem_file_path = os.path.join(first_dir, 'banitem.json')
config_file_path = os.path.join(first_dir, 'config.json')

class uban(Plugin):
    api_version = '0.5'

    def on_enable(self):
        # 加载玩家列表数据
        if not os.path.exists(player_list_file_path):
            player_list_data = {}
            with open(player_list_file_path, 'w', encoding='utf-8') as f:
                json_str = json.dumps(player_list_data, indent=4, ensure_ascii=False)
                f.write(json_str)
        else:
            with open(player_list_file_path, 'r', encoding='utf-8') as f:
                player_list_data = json.loads(f.read())
        self.player_list = player_list_data
        # 加载封禁玩家列表数据
        if not os.path.exists(banlist_file_path):
            banlist_data = {}
            with open(banlist_file_path, 'w', encoding='utf-8') as f:
                json_str = json.dumps(banlist_data, indent=4, ensure_ascii=False)
                f.write(json_str)
        else:
            with open(banlist_file_path, 'r', encoding='utf-8') as f:
                banlist_data = json.loads(f.read())
        self.banlist = banlist_data
        # 加载举报内容数据
        if not os.path.exists(report_list_file_path):
            report_list_data = []
            with open(report_list_file_path, 'w', encoding='utf-8') as f:
                json_str = json.dumps(report_list_data, indent=4, ensure_ascii=False)
                f.write(json_str)
        else:
            with open(report_list_file_path, 'r', encoding='utf-8') as f:
                report_list_data = json.loads(f.read())
        self.report_list = report_list_data
        # 加载封禁物品数据
        if not os.path.exists(banitem_file_path):
            banitem_data = {}
            with open(banitem_file_path, 'w', encoding='utf-8') as f:
                json_str = json.dumps(banitem_data, indent=4, ensure_ascii=False)
                f.write(json_str)
        else:
            with open(banitem_file_path, 'r', encoding='utf-8') as f:
                banitem_data = json.loads(f.read())
        self.banitem_data = banitem_data
        # 加载配置文件数据
        if not os.path.exists(config_file_path):
            config_data = {'report_interval': 10, 'report_title_len': 10, 'report_content_len': 30}
            with open(config_file_path, 'w', encoding='utf-8') as f:
                json_str = json.dumps(config_data, indent=4, ensure_ascii=False)
                f.write(json_str)
        else:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config_data = json.loads(f.read())
        self.config_data = config_data
        self.player_with_ban_item_mode_on_list = []
        # 命令转换
        self.CommandSenderWrapper = CommandSenderWrapper(
            self.server.command_sender,
            on_message=None
        )
        self.server.scheduler.run_task(self, self.clear_banned_item, delay=0, period=20)
        self.register_events(self)
        self.logger.info(f'{ColorFormat.YELLOW}UBan 已启用...')

    commands = {
        'uban': {
            'description': '打开封禁功能主表单',
            'usages': ['/uban'],
            'permissions': ['uban.command.uban']
        }
    }

    permissions = {
        'uban.command.uban': {
            'description': '打开封禁功能主表单',
            'default': True
        }
    }

    def on_command(self, sender: CommandSender, command: Command, args: list[str]):
        if command.name == 'uban':
            if not isinstance(sender, Player):
                sender.send_message(f'{ColorFormat.YELLOW}该命令只能由玩家执行...')
                return
            player = sender
            if player.is_op == True:
                main_form_op = ActionForm(
                    title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}封禁玩家主表单-管理版',
                    content=f'{ColorFormat.GREEN}请选择操作...'
                )
                main_form_op.add_button(f'{ColorFormat.YELLOW}查看玩家举报', icon='textures/ui/mail_icon', on_click=self.list_report_info)
                main_form_op.add_button(f'{ColorFormat.YELLOW}封禁在线玩家', icon='textures/ui/dressing_room_customization', on_click=self.ban_online_player)
                main_form_op.add_button(f'{ColorFormat.YELLOW}封禁离线玩家', icon='textures/ui/friend_glyph_desaturated', on_click=self.ban_offline_player)
                main_form_op.add_button(f'{ColorFormat.YELLOW}查看玩家封禁列表', icon='textures/ui/lock_color', on_click=self.list_banlist)
                main_form_op.add_button(f'{ColorFormat.YELLOW}查看物品封禁列表', icon='textures/ui/lock_color', on_click=self.banned_item_list)
                main_form_op.add_button(f'{ColorFormat.YELLOW}开启/关闭物品封禁模式', icon='textures/ui/toggle_on', on_click=self.switch_ban_item_mode)
                main_form_op.add_button(f'{ColorFormat.YELLOW}重载配置文件', icon='textures/ui/icon_setting', on_click=self.reload_config_data)
                main_form_op.add_button(f'{ColorFormat.YELLOW}关闭表单', icon='textures/ui/cancel', on_click=None)
                player.send_form(main_form_op)
            else:
                mian_form_player = ActionForm(
                    title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}封禁玩家主表单-玩家版',
                    content=f'{ColorFormat.GREEN}请选择操作...'
                )
                mian_form_player.add_button(f'{ColorFormat.YELLOW}我的举报', icon='textures/ui/mail_icon', on_click=self.personal_report)
                mian_form_player.add_button(f'{ColorFormat.YELLOW}查看玩家封禁列表', icon='textures/ui/lock_color', on_click=self.list_banlist)
                mian_form_player.add_button(f'{ColorFormat.YELLOW}查看物品封禁列表', icon='textures/ui/lock_color', on_click=self.banned_item_list)
                mian_form_player.add_button(f'{ColorFormat.YELLOW}关闭表单', icon='textures/ui/cancel', on_click=None)
                player.send_form(mian_form_player)

    # 封禁在线玩家
    def ban_online_player(self, p: Player):
        online_player_list = [online_player.name for online_player in self.server.online_players if online_player.name != p.name]
        if len(online_player_list) == 0:
            p.send_message(f'{ColorFormat.RED}封禁失败： {ColorFormat.WHITE}当前服务器除了你, 没有别的玩家在线...')
            return
        dropdown = Dropdown(
            label=f'{ColorFormat.GREEN}请选择玩家...',
            options= online_player_list
        )
        textinput =TextInput(
            label=f'{ColorFormat.GREEN}封禁原因',
            placeholder='请输入任意字符串（选填）'
        )
        ban_online_player_form = ModalForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}封禁在线玩家表单',
            controls=[dropdown, textinput],
            submit_button=f'{ColorFormat.YELLOW}确认',
            on_close=self.back_to_main_form
        )
        def on_submit(p: Player, json_str):
            data = json.loads(json_str)
            target_player = self.server.get_player(online_player_list[data[0]])
            if data[1] == '':
                ban_reason = '无'
            else:
                ban_reason = data[1]
            if target_player.is_op == True:
                p.send_message(f'{ColorFormat.RED}封禁失败： {ColorFormat.WHITE}你不能直接封禁一名管理员，请先取消他的管理员身份...')
                return
            # 执行封禁
            ban_name = target_player.name
            ban_xuid = target_player.xuid
            ban_uuid = str(target_player.unique_id)
            ban_ip = target_player.address.hostname
            ban_source = p.name
            pre_datetime = str(datetime.datetime.now()).split(' ')
            date = pre_datetime[0]
            time = pre_datetime[1].split('.')[0]
            ban_time = date + '-' + time
            self.banlist[ban_name] = {
                'ban_xuid': ban_xuid,
                'ban_uuid': ban_uuid,
                'ban_ip': ban_ip,
                'ban_source': ban_source,
                'ban_reason': ban_reason,
                'ban_time': ban_time
            }
            self.server.broadcast_message(f'{ColorFormat.RED}玩家 {ColorFormat.WHITE}{ban_name} '
                                          f'{ColorFormat.RED}已被封禁，原因： {ColorFormat.WHITE}{ban_reason}')
            target_player.kick(f'你（ip：{ban_ip}）已被服务器封禁，原因：{ban_reason}')
            self.save_banlist_data()
            # 踢出在线的小号
            for online_player in self.server.online_players:
                if online_player.address.hostname == ban_ip:
                    online_player.kick(f'你（ip：{ban_ip}）已被服务器封禁，原因：{ban_reason}')
        ban_online_player_form.on_submit = on_submit
        p.send_form(ban_online_player_form)

    # 封禁离线玩家
    def ban_offline_player(self, p: Player):
        online_player_list = [online_player.name for online_player in self.server.online_players]
        banned_player_list = [banned_player for banned_player in self.banlist.keys()]
        offline_player_list = [player_name for player_name in self.player_list.keys() if (player_name not in online_player_list and
                                                                                 player_name not in banned_player_list)]
        if len(offline_player_list) == 0:
            p.send_message(f'{ColorFormat.RED}封禁失败： {ColorFormat.WHITE}服务器除了你没有出现过别的玩家...')
            return
        dropdown = Dropdown(
            label=f'{ColorFormat.GREEN}已排除在线玩家和被封禁的玩家...\n\n'
                  f'{ColorFormat.GREEN}请选择玩家...',
            options=offline_player_list
        )
        textinput = TextInput(
            label=f'{ColorFormat.GREEN}封禁原因',
            placeholder='请输入任意字符串（选填）'
        )
        ban_offline_player_form = ModalForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}封禁离线玩家表单',
            controls=[dropdown, textinput],
            submit_button=f'{ColorFormat.YELLOW}确认',
            on_close=self.back_to_main_form
        )
        def on_submit(p: Player, json_str):
            data = json.loads(json_str)
            target_player_name = offline_player_list[data[0]]
            if data[1] == '':
                ban_reason = '无'
            else:
                ban_reason = data[1]
            if self.player_list[target_player_name]['is_op'] == True:
                p.send_message(f'{ColorFormat.RED}封禁失败： {ColorFormat.WHITE}你不能直接封禁一名管理员，请先取消他的管理员身份...')
                return
            ban_name = target_player_name
            ban_xuid = self.player_list[target_player_name]['xuid']
            ban_uuid = self.player_list[target_player_name]['uuid']
            ban_ip = self.player_list[target_player_name]['ip']
            ban_source = p.name
            pre_datetime = str(datetime.datetime.now()).split(' ')
            date = pre_datetime[0]
            time = pre_datetime[1].split('.')[0]
            ban_time = date + '-' + time
            self.banlist[ban_name] = {
                'ban_xuid': ban_xuid,
                'ban_uuid': ban_uuid,
                'ban_ip': ban_ip,
                'ban_source': ban_source,
                'ban_reason': ban_reason,
                'ban_time': ban_time
            }
            self.server.broadcast_message(f'{ColorFormat.RED}玩家 {ColorFormat.WHITE}{ban_name} '
                                          f'{ColorFormat.RED}已被封禁，原因： {ColorFormat.WHITE}{ban_reason}')
            self.save_banlist_data()
            for online_player in self.server.online_players:
                if online_player.address.hostname == ban_ip:
                    online_player.kick(f'你（ip：{ban_ip}）已被服务器封禁，原因：{ban_reason}')
        ban_offline_player_form.on_submit = on_submit
        p.send_form(ban_offline_player_form)

    # 查看封禁列表
    def list_banlist(self, p: Player):
        banlist_form = ActionForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}黑名单',
            content=f'{ColorFormat.GREEN}请选择操作...',
            on_close=self.back_to_main_form
        )
        for key, value in self.banlist.items():
            ban_name = key
            ban_info = value
            ban_xuid = ban_info['ban_xuid']
            ban_uuid = ban_info['ban_uuid']
            ban_ip = ban_info['ban_ip']
            ban_source = ban_info['ban_source']
            ban_reason = ban_info['ban_reason']
            ban_time = ban_info['ban_time']
            banlist_form.add_button(f'{ColorFormat.YELLOW}{ban_name}', on_click=self.banned_player_info(
                ban_name, ban_xuid, ban_uuid, ban_ip, ban_source, ban_reason, ban_time
            ))
        banlist_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.back_to_main_form)
        p.send_form(banlist_form)

    # 查看封禁玩家信息和解封玩家按钮
    def banned_player_info(self, ban_name, ban_xuid, ban_uuid, ban_ip, ban_source, ban_reason, ban_time):
        def on_click(p: Player):
            banned_player_info_form = ActionForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}{ban_name}',
                content=f'{ColorFormat.YELLOW}游戏名： {ColorFormat.WHITE}{ban_name}\n'
                        f'{ColorFormat.YELLOW}xuid： {ColorFormat.WHITE}{ban_xuid}\n'
                        f'{ColorFormat.YELLOW}uuid： {ColorFormat.WHITE}{ban_uuid}\n'
                        f'{ColorFormat.YELLOW}ip地址： {ColorFormat.WHITE}{ban_ip}\n'
                        f'{ColorFormat.YELLOW}执行者： {ColorFormat.WHITE}{ban_source}\n'
                        f'{ColorFormat.YELLOW}封禁原因： {ColorFormat.WHITE}{ban_reason}\n'
                        f'{ColorFormat.YELLOW}封禁时间： {ColorFormat.WHITE}{ban_time}',
                on_close=self.list_banlist
            )
            if p.is_op == True:
                banned_player_info_form.add_button(f'{ColorFormat.YELLOW}解封', icon='textures/ui/icon_unlocked', on_click=self.unban_player(ban_name))
                banned_player_info_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.list_banlist)
            p.send_form(banned_player_info_form)
        return on_click

    # 解封玩家
    def unban_player(self, ban_name):
        def on_click(p: Player):
            unban_player_form = ActionForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}解封玩家表单',
                content=f'{ColorFormat.GREEN}你确定要解封玩家 {ColorFormat.WHITE}{ban_name} {ColorFormat.GREEN}吗？',
                on_close=self.list_banlist
            )
            unban_player_form.add_button(f'{ColorFormat.YELLOW}确认', icon='textures/ui/realms_green_check', on_click=self.on_confirm(ban_name))
            unban_player_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.list_banlist)
            p.send_form(unban_player_form)
        return on_click

    def on_confirm(self, ban_name):
        def on_click(p: Player):
            self.banlist.pop(ban_name)
            self.save_banlist_data()
            p.send_message(f'{ColorFormat.YELLOW}玩家 {ColorFormat.WHITE}{ban_name} {ColorFormat.YELLOW}解封成功...')
        return on_click

    # 查看个人举报内容列表
    def personal_report(self, p: Player):
        self.check_time()
        personal_report_form = ActionForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}我的举报',
            content=f'{ColorFormat.GREEN}仅显示 {ColorFormat.WHITE}{self.config_data['report_interval']} '
                    f'{ColorFormat.GREEN}天的内容...',
            on_close=self.back_to_main_form
        )
        for report_info in self.report_list:
            reporter_name = report_info['reporter_name']
            if reporter_name == p.name:
                report_title = report_info['report_title']
                report_content = report_info['report_content']
                report_time = report_info['report_time']
                report_reply = report_info['report_reply']
                if len(report_reply) == 0:
                    report_status = f'{ColorFormat.RED}[未受理]'
                else:
                    report_status = f'{ColorFormat.GREEN}[已受理]'
                personal_report_form.add_button(f'{report_title} {report_status}\n{ColorFormat.GREEN}{report_time}', on_click=(
                    self.personal_report_details(report_title, report_content, report_time, report_reply)
                ))
        personal_report_form.add_button(f'{ColorFormat.YELLOW}创建新举报', icon='textures/ui/color_plus', on_click=self.create_new_report)
        personal_report_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.back_to_main_form)
        p.send_form(personal_report_form)

    # 查看个人举报内容详细内容
    def personal_report_details(self, report_title, report_content, report_time, report_reply):
        def on_click(p: Player):
            personal_report_details_form = ActionForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}举报详情',
                content=f'{ColorFormat.YELLOW}举报标题： {ColorFormat.WHITE}{report_title}\n'
                        f'{ColorFormat.YELLOW}举报内容： {ColorFormat.WHITE}{report_content}\n'
                        f'{ColorFormat.YELLOW}举报时间： {ColorFormat.WHITE}{report_time}\n'
                        f'{ColorFormat.YELLOW}收到回复： {ColorFormat.WHITE}',
                on_close=self.personal_report
            )
            if len(report_reply) == 0:
                personal_report_details_form.content += '无'
                personal_report_details_form.add_button(f'{ColorFormat.YELLOW}撤销举报', icon='textures/ui/refresh_light', on_click=self.cancel_personal_report(
                    report_title, report_content, report_time, report_reply
                ))
            else:
                personal_report_details_form.content += report_reply
            personal_report_details_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.personal_report)
            p.send_form(personal_report_details_form)
        return on_click

    # 玩家创建新的举报
    def create_new_report(self, p: Player):
        textinput1 = TextInput(
            label=f'{ColorFormat.GREEN}举报标题',
            placeholder=f'举报内容不能为空，但不要超过{self.config_data['report_title_len']}个字'
        )
        textinput2 = TextInput(
            label=f'{ColorFormat.GREEN}举报内容',
            placeholder=f'举报内容不能为空，但不要超过{self.config_data['report_content_len']}个字'
        )
        create_new_report_form = ModalForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}创建新举报',
            controls=[textinput1, textinput2],
            submit_button=f'{ColorFormat.YELLOW}发送',
            on_close=self.personal_report
        )
        def on_submit(p: Player, json_str):
            data = json.loads(json_str)
            if (len(data[0]) == 0 or len(data[0]) > self.config_data['report_title_len']
                    or len(data[1]) == 0 or len(data[1]) > self.config_data['report_content_len']):
                p.send_message(f'{ColorFormat.RED}举报失败： {ColorFormat.YELLOW}请按提示正确填写...')
                return
            reporter_name = p.name
            report_title = data[0]
            report_content = data[1]
            report_time = str(datetime.datetime.now()).split(' ')[0]
            report_reply = ''
            self.report_list.append(
                {
                    'reporter_name': reporter_name,
                    'report_title': report_title,
                    'report_content': report_content,
                    'report_time': report_time,
                    'report_reply': report_reply
                }
            )
            self.save_report_data()
            p.send_message(f'{ColorFormat.YELLOW}举报成功...')
        create_new_report_form.on_submit = on_submit
        p.send_form(create_new_report_form)

    # 玩家撤销举报
    def cancel_personal_report(self, report_title, report_content, report_time, report_reply):
        def on_click(p: Player):
            for report_info in self.report_list:
                if (report_info['reporter_name'] == p.name and report_info['report_title'] == report_title
                        and report_info['report_content'] == report_content and report_info['report_time'] == report_time
                        and report_info['report_reply'] == report_reply):
                    self.report_list.remove(report_info)
                    self.save_report_data()
                    p.send_message(f'{ColorFormat.YELLOW}举报撤销成功...')
                    break
        return on_click

    # 列出所有未受理的玩家举报
    def list_report_info(self, p: Player):
        self.check_time()
        list_report_info_form = ActionForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}待处理的玩家举报',
            content=f'{ColorFormat.GREEN}仅显示 {ColorFormat.WHITE}{self.config_data['report_interval']} '
                    f'{ColorFormat.GREEN}天的内容...',
            on_close=self.back_to_main_form
        )
        for report_info in self.report_list:
            report_reply = report_info['report_reply']
            if len(report_reply) == 0:
                reporter_name = report_info['reporter_name']
                report_title = report_info['report_title']
                report_content = report_info['report_content']
                report_time = report_info['report_time']
                list_report_info_form.add_button(f'{reporter_name} - {report_title}\n{ColorFormat.GREEN}{report_time}', on_click=self.list_report_info_details(
                    reporter_name, report_title, report_content, report_time
                ))
        list_report_info_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.back_to_main_form)
        p.send_form(list_report_info_form)

    # 列出玩家举报详情
    def list_report_info_details(self, reporter_name, report_title, report_content, report_time):
        def on_click(p: Player):
            list_report_info_details_form = ActionForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}玩家 {reporter_name} 的举报',
                content=f'{ColorFormat.YELLOW}举报标题： {ColorFormat.WHITE}{report_title}\n'
                        f'{ColorFormat.YELLOW}举报内容： {ColorFormat.WHITE}{report_content}\n'
                        f'{ColorFormat.YELLOW}举报时间： {ColorFormat.WHITE}{report_time}\n',
                on_close=self.list_report_info
            )
            list_report_info_details_form.add_button(f'{ColorFormat.YELLOW}受理', icon='textures/ui/realms_green_check', on_click=self.reply_report(
                reporter_name, report_title, report_content, report_time
            ))
            list_report_info_details_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.list_report_info)
            p.send_form(list_report_info_details_form)
        return on_click

    # 管理员受理玩家举报
    def reply_report(self, reporter_name, report_title, report_content, report_time):
        def on_click(p: Player):
            textinput = TextInput(
                label=f'{ColorFormat.GREEN}回复内容',
                placeholder=f'举报内容不能为空，但不要超过{self.config_data['report_content_len']}个字'
            )
            reply_report_form = ModalForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}受理玩家举报',
                controls=[textinput],
                submit_button=f'{ColorFormat.YELLOW}确认',
                on_close=self.list_report_info
            )
            def on_submit(p: Player, json_str):
                data = json.loads(json_str)
                if len(data[0]) == 0 or len(data[0]) > self.config_data['report_content_len']:
                    p.send_message(f'{ColorFormat.RED}回复失败： {ColorFormat.YELLOW}请按提示正确填写...')
                    return
                for report_info in self.report_list:
                    if (report_info['reporter_name'] == reporter_name and report_info['report_title'] == report_title
                            and report_info['report_content'] == report_content and report_info['report_time'] == report_time
                            and len(report_info['report_reply']) == 0):
                        report_info['report_reply'] = data[0]
                        self.save_report_data()
                        p.send_message(f'{ColorFormat.YELLOW}受理玩家举报成功...')
                        break
            reply_report_form.on_submit = on_submit
            p.send_form(reply_report_form)
        return on_click

    # 保存玩家信息
    def save_player_list_data(self):
        with open(player_list_file_path, 'w+', encoding='utf-8') as f:
            json_str = json.dumps(self.player_list, indent=4, ensure_ascii=False)
            f.write(json_str)

    # 保存封禁玩家信息
    def save_banlist_data(self):
        with open(banlist_file_path, 'w+', encoding='utf-8') as f:
            json_str = json.dumps(self.banlist, indent=4, ensure_ascii=False)
            f.write(json_str)

    # 重载配置文件
    def reload_config_data(self, p: Player):
        textinput1 = TextInput(
            label=f'{ColorFormat.YELLOW}当前允许举报内容显示的最大天数： {ColorFormat.WHITE}{self.config_data['report_interval']}',
            placeholder=f'请输入一个正整数, 例如：10'
        )
        textinput2 = TextInput(
            label=f'{ColorFormat.YELLOW}当前允许举报标题的最大字数： {ColorFormat.WHITE}{self.config_data['report_title_len']}',
            placeholder=f'请输入一个正整数, 例如：10'
        )
        textinput3 = TextInput(
            label=f'{ColorFormat.YELLOW}当前允许举报/回复内容的最大字数： {ColorFormat.WHITE}{self.config_data['report_content_len']}',
            placeholder=f'请输入一个正整数, 例如：30'
        )
        reload_config_data_form = ModalForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}重载配置文件',
            controls=[textinput1, textinput2, textinput3],
            submit_button=f'{ColorFormat.YELLOW}确认',
            on_close=self.back_to_main_form
        )
        def on_submit(p: Player, json_str):
            data = json.loads(json_str)
            try:
                if len(data[0]) == 0:
                    new_report_interval = self.config_data['report_interval']
                else:
                    new_report_interval = int(data[0])
                if len(data[1]) == 0:
                    new_report_title_len = self.config_data['report_title_len']
                else:
                    new_report_title_len = int(data[1])
                if len(data[2]) == 0:
                    new_report_content_len = self.config_data['report_content_len']
                else:
                    new_report_content_len = int(data[2])
            except:
                p.send_message(f'{ColorFormat.RED}表单解析错误, 请按提示正确填写....')
                return
            if (new_report_interval <=0 or new_report_title_len <= 0 or new_report_content_len <=0):
                p.send_message(f'{ColorFormat.RED}表单解析错误, 请按提示正确填写....')
                return
            self.config_data['report_interval'] = new_report_interval
            self.config_data['report_title_len'] = new_report_title_len
            self.config_data['report_content_len'] = new_report_content_len
            with open(config_file_path, 'w+', encoding='utf-8') as f:
                new_json_str = json.dumps(self.config_data, indent=4, ensure_ascii=False)
                f.write(new_json_str)
            p.send_message(f'{ColorFormat.YELLOW}配置文件重载成功...')
        reload_config_data_form.on_submit = on_submit
        p.send_form(reload_config_data_form)

    # 检测举报内容时效性
    def check_time(self):
        pre_current_time = str(datetime.datetime.now()).split(' ')[0].split('-')
        current_time = datetime.datetime(int(pre_current_time[0]), int(pre_current_time[1]), int(pre_current_time[2]))
        for report_info in self.report_list:
            pre_report_time = report_info['report_time'].split('-')
            report_time = datetime.datetime(int(pre_report_time[0]), int(pre_report_time[1]), int(pre_report_time[2]))
            if (current_time - report_time).days > self.config_data['report_interval']:
                self.report_list.remove(report_info)
        self.save_report_data()

    # 保存举报内容
    def save_report_data(self):
        with open(report_list_file_path, 'w+', encoding='utf-8') as f:
            json_str = json.dumps(self.report_list, indent=4, ensure_ascii=False)
            f.write(json_str)

    # 保存物品黑名单数据
    def save_banitem_data(self):
        with open(banitem_file_path, 'w+', encoding='utf-8') as f:
            json_str = json.dumps(self.banitem_data, indent=4, ensure_ascii=False)
            f.write(json_str)

    # 返回主表单
    def back_to_main_form(self, p: Player):
        p.perform_command('uban')

    # 监听玩家加入服务器
    @event_handler
    def on_player_join(self, event: PlayerJoinEvent):
        # 检测进服玩家的 ip 地址，如在封禁列表中，踢出
        for value in self.banlist.values():
            ban_info = value
            if event.player.address.hostname == ban_info['ban_ip']:
                ban_ip = ban_info['ban_ip']
                ban_reason = ban_info['ban_reason']
                event.player.kick(f'你（ip：{ban_ip}）已被服务器封禁，原因：{ban_reason}')
                return
        if event.player.name not in [player_name for player_name in self.player_list.keys()]:
            player_name = event.player.name
            player_xuid = event.player.xuid
            player_uuid = str(event.player.unique_id)
            player_ip = event.player.address.hostname
            player_is_op = True if event.player.is_op == True else False
            self.player_list[player_name] = {
                'xuid': player_xuid,
                'uuid': player_uuid,
                'ip': player_ip,
                'is_op': player_is_op
            }
            self.save_player_list_data()
        else:
            if event.player.xuid != self.player_list[event.player.name]['xuid']:
                event.player.kick(f'服务器中已经存在过一个名为 {event.player.name} 的玩家了...')

    def switch_ban_item_mode(self, player: Player):
        if player.name in self.player_with_ban_item_mode_on_list:
            self.player_with_ban_item_mode_on_list.remove(player.name)
            player.send_message(f'{ColorFormat.YELLOW}已为你关闭封禁物品模式...')
        else:
            self.player_with_ban_item_mode_on_list.append(player.name)
            player.send_message(f'{ColorFormat.YELLOW}已为你开启封禁物品模式...')

    # 封禁物品模式
    @event_handler
    def ban_item(self, event: PlayerInteractEvent):
        if event.player.name in self.player_with_ban_item_mode_on_list:
            target_ban_item = event.item.type
            textinput = TextInput(
                label=f'{ColorFormat.GREEN}你确定要将物品 {ColorFormat.WHITE}{target_ban_item} '
                      f'{ColorFormat.GREEN}加入黑名单吗？\n'
                      f'\n'
                      f'请输入封禁原因...',
                placeholder='请输入任意字符串（选填）'
            )
            ban_item_form = ModalForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}封禁物品表单',
                controls=[textinput],
                submit_button=f'{ColorFormat.YELLOW}确认',
                on_close=None
            )
            def on_submit(player: event.player, json_str):
                data = json.loads(json_str)
                if len(data[0]) == 0:
                    item_ban_reason = '无'
                else:
                    item_ban_reason = data[0]
                if target_ban_item in [key for key in self.banitem_data.keys()]:
                    player.send_message(f'{ColorFormat.RED}封禁物品失败： {ColorFormat.WHITE}'
                                        f'{target_ban_item} 已在物品黑名单当中...')
                    return
                else:
                    self.banitem_data[target_ban_item] = item_ban_reason
                    self.save_banitem_data()
                    player.send_message(f'{ColorFormat.YELLOW}封禁物品成功...')
                    self.server.broadcast_message(f'{ColorFormat.RED}物品 {ColorFormat.WHITE}{target_ban_item} '
                                          f'{ColorFormat.RED}已被封禁，原因： {ColorFormat.WHITE}{item_ban_reason}')
            ban_item_form.on_submit = on_submit
            event.player.send_form(ban_item_form)
            event.cancelled = True

    # 查看封禁物品列表
    def banned_item_list(self, player: Player):
        banned_item_list_form = ActionForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}物品封禁列表',
            content='',
            on_close=self.back_to_main_form
        )
        for key, value in self.banitem_data.items():
            banned_item_list_form.content += f'{ColorFormat.YELLOW}[{key}] {ColorFormat.WHITE}{value}\n'
        if player.is_op == True:
            banned_item_list_form.add_button(f'{ColorFormat.YELLOW}解封物品', icon='textures/ui/', on_click=self.unban_item)
        banned_item_list_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.back_to_main_form)
        player.send_form(banned_item_list_form)

    def unban_item(self, player: Player):
        banitem_list = [key for key in self.banitem_data.keys()]
        dropdown = Dropdown(
            label=f'{ColorFormat.GREEN}请选择目标解封的物品...',
            options=banitem_list
        )
        unban_item_form = ModalForm(
            title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}解封物品表单',
            controls=[dropdown],
            submit_button=f'{ColorFormat.YELLOW}解封',
            on_close=self.banned_item_list
        )
        def on_submit(player: Player, json_str):
            data = json.loads(json_str)
            target_unban_item = banitem_list[data[0]]
            confirm_form = ActionForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}解封物品表单',
                content=f'{ColorFormat.GREEN}你确定要解封物品 {ColorFormat.WHITE}{target_unban_item}'
                        f' {ColorFormat.GREEN}吗？',
                on_close=self.banned_item_list
            )
            confirm_form.add_button(f'{ColorFormat.YELLOW}确认', icon='textures/ui/realms_green_check', on_click=self.on_another_confirm(target_unban_item))
            confirm_form.add_button(f'{ColorFormat.YELLOW}返回', icon='textures/ui/refresh_light', on_click=self.banned_item_list)
            player.send_form(confirm_form)
        unban_item_form.on_submit = on_submit
        player.send_form(unban_item_form)

    def on_another_confirm(self, target_unban_item):
        def on_click(player: Player):
            self.banitem_data.pop(target_unban_item)
            self.save_banitem_data()
            player.send_message(f'{ColorFormat.YELLOW}物品 {ColorFormat.WHITE}{target_unban_item} {ColorFormat.YELLOW}解封成功...')
        return on_click

    # 清除玩家违禁品任务
    def clear_banned_item(self):
        banned_item_list = [key for key in self.banitem_data.keys()]
        if len(self.server.online_players) == 0:
            return
        for online_player in self.server.online_players:
            if online_player.is_op == False:
                if online_player.name.find(' ') != -1:
                    online_player_name = f'"{online_player.name}"'
                else:
                    online_player_name = online_player.name
                for banned_item in banned_item_list:
                    self.server.dispatch_command(self.CommandSenderWrapper,
                                                 f'clear {online_player_name} {banned_item}')