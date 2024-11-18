import os
import zipfile
import json
import time
import datetime
import threading
from endstone.plugin import Plugin
from endstone.command import CommandSender
from endstone.form import ActionForm
from endstone import ColorFormat, Player

current_dir = os.getcwd()
backup_dir = os.path.join(current_dir, 'backups')
first_dir = os.path.join(current_dir, 'plugins', 'ubackup')
try:
    os.mkdir(first_dir)
    os.mkdir(backup_dir)
except:
    pass
config_file_path = os.path.join(first_dir, 'config.json')

class ubackup(Plugin):
    api_version = '0.5'

    def on_enable(self):
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config = json.loads(f.read())
        except:
            with open(config_file_path, 'w', encoding='utf-8') as f:
                config = {'backup_time': ['00:00:00', '6:00:00', '12:00:00', '18:00:00'], 'max_backup_num': 3}
                json_str = json.dumps(config, indent=4)
                f.write(json_str)
            self.logger.info(f'{ColorFormat.YELLOW}已生成默认配置文件，位置：{config_file_path}')
        self.config_data = config
        self.on_backup_info = []
        self.task = self.server.scheduler.run_task(self, self.on_check_time, delay=0, period=20)
        self.logger.info(f'{ColorFormat.YELLOW}UBackup 已启用...')

    commands = {
        'ub': {
            'description': '重载热备份配置文件...',
            'usages': ['/ub'],
            'permissions': ['ubackup.command.ub']
        }
    }

    permissions = {
        'ubackup.command.ub': {
            'description': '重载热备份配置文件...',
            'default': 'op'
        }
    }

    def on_command(self, sender: CommandSender, command: Player, args: list[str]):
        if not isinstance(sender, Player):
            self.logger.info(f'{ColorFormat.YELLOW}该命令只能由玩家执行...')
        player = sender
        if command.name == 'ub':
            backup_form = ActionForm(
                title=f'{ColorFormat.BOLD}{ColorFormat.LIGHT_PURPLE}备份主表单',
                content=f'{ColorFormat.GREEN}请选择操作...'
            )
            backup_form.add_button('手动备份', icon='textures/ui/download_backup', on_click=self.on_manual_backup)
            backup_form.add_button('重载配置文件', icon='textures/ui/icon_setting', on_click=self.reload_config_data)
            player.send_form(backup_form)

    def on_check_time(self):
        threading.Thread(target=self.on_check_time_thread).start()

    def on_check_time_thread(self):
        current_date_and_time = datetime.datetime.now()
        current_time = datetime.time(current_date_and_time.hour, current_date_and_time.minute, current_date_and_time.second)
        for pre_schedule_time in self.config_data['backup_time']:
            pre_schedule_time = pre_schedule_time.split(':')
            schedule_time = datetime.time(int(pre_schedule_time[0]), int(pre_schedule_time[1]), int(pre_schedule_time[2]))
            if schedule_time == current_time:
                for player in self.server.online_players:
                    if player.is_op == True:
                        player.send_message(f'{ColorFormat.GREEN}[{pre_schedule_time[0]}:{pre_schedule_time[1]}]'
                                            f'{ColorFormat.YELLOW}备份计划已开始...')
                start_time = time.time()
                self.on_backup_info = [current_date_and_time, start_time]
                self.on_backup(current_date_and_time)

    def on_backup(self, schedule_time):
        self.check_backup_num(schedule_time)
        zip_file_name = (str(self.on_backup_info[0].year) + '-' + str(self.on_backup_info[0].month) + '-' + str(self.on_backup_info[0].day) +
                         '-' + str(self.on_backup_info[0].hour) + '-' + str(self.on_backup_info[0].minute) + '-' + str(self.on_backup_info[0].second) + '.zip')
        zip_file_path = backup_dir + '\\' + zip_file_name
        source_dir = os.path.join(current_dir, 'worlds')
        with zipfile.ZipFile(zip_file_path, 'w') as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, source_dir))
        end_time = time.time()
        time_cost = round(end_time - self.on_backup_info[1], 4)
        pre_zip_file_size = round(os.path.getsize(zip_file_path) / (2**20), 2)
        if pre_zip_file_size > 1024:
            pre_zip_file_size = round(pre_zip_file_size / 1024, 2)
            zip_file_size = str(pre_zip_file_size) + 'GB'
        else:
            zip_file_size = str(pre_zip_file_size) + 'MB'
        for player in self.server.online_players:
            if player.is_op == True:
                player.send_message(f'{ColorFormat.YELLOW}备份已完成， {ColorFormat.AQUA}文件大小：{zip_file_size}, {ColorFormat.GREEN}耗时：{time_cost}s')
                self.on_backup_info = []

    def on_manual_backup(self, player: Player):
        current_date_and_time = datetime.datetime.now()
        player.send_message(f'{ColorFormat.YELLOW}手动备份已开始...')
        start_time = time.time()
        self.on_backup_info = [current_date_and_time, start_time]
        self.on_backup(current_date_and_time)

    def check_backup_num(self, schedule_time):
        backup_list = os.listdir(backup_dir)
        time_len_list = []
        if len(backup_list) >= self.config_data['max_backup_num']:
            for zip_file_name in backup_list:
                pre_zip_file_time = zip_file_name.strip('.zip').split('-')
                zip_file_time = datetime.datetime(int(pre_zip_file_time[0]), int(pre_zip_file_time[1]), int(pre_zip_file_time[2]),
                                              int(pre_zip_file_time[3]), int(pre_zip_file_time[4]), int(pre_zip_file_time[5]))
                time_len = schedule_time - zip_file_time
                time_len_list.append([zip_file_name, time_len])
            time_len_list.sort(key=lambda x:x[1], reverse=True)
            zip_file_to_delete = backup_dir + '\\' + time_len_list[0][0]
            os.remove(zip_file_to_delete)
        else:
            return

    def reload_config_data(self, player: Player):
        with open(config_file_path, 'r', encoding='utf-8') as f:
            self.config_data = json.loads(f.read())
        player.send_message(f'{ColorFormat.YELLOW}配置文件已重载...')