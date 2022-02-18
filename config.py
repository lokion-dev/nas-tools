import logging
import os
import threading

import qbittorrentapi
import yaml
import log

# 菜单对应关系，配置WeChat应用中配置的菜单ID与执行命令的对应关系，需要手工修改
# 菜单序号在https://work.weixin.qq.com/wework_admin/frame#apps 应用自定义菜单中维护，然后看日志输出的菜单序号是啥（按顺利能猜到的）....
# 命令对应关系：/qbt qBittorrent转移；/qbr qBittorrent删种；/hotm 热门预告；/pts PT签到；/mrt 预告片下载；/rst ResilioSync同步；/rss RSS下载
WECHAT_MENU = {'_0_0': '/qbt', '_0_1': '/qbr', '_0_2': '/rss', '_0_3': '/hotm', '_0_4': '/mrt', '_1_0': '/rst',
               '_2_0': '/pts'}
# 电影类型，目前不能修改
RMT_MOVIETYPE = ['华语电影', '外语电影', '精选']
# 收藏了的媒体的目录名，名字可以改，在Emby中点击红星则会自动将电影转移到此分类下，需要在Emby Webhook中配置用户行为通知
RMT_FAVTYPE = '精选'
# 剧集类型，目前不能修改，会自动在连续剧下按以下分类目录存放媒体，可以分开建立Emby媒体库
RMT_TVTYPE = ['国产剧', '欧美剧', '日韩剧', '动漫', '纪录片', '综艺', '儿童']
# 支持的媒体文件后缀格式
RMT_MEDIAEXT = ['.mp4', '.mkv', '.ts', '.iso']
# 支持的字幕文件后缀格式
RMT_SUBEXT = ['.srt', '.ass']
# 欧美国家的简称列表，会将这类剧集移到欧美剧目录
RMT_COUNTRY_EA = ['US', 'FR', 'GB', 'DE', 'ES', 'IT', 'NL', 'PT', 'RU', 'UK']
# 亚洲国家的简称列表，会将这类剧集移到日韩剧目录
RMT_COUNTRY_AS = ['JP', 'KP', 'KR', 'TH', 'IN', 'SG']
# 剩余多少磁盘空间时不再转移，单位GB
RMT_DISKFREESIZE = 10

# 从Youtube下载预告片的命令配置，不用改它
YOUTUBE_DL_CMD = 'youtube-dl -o "$PATH" "https://www.youtube.com/watch?v=$KEY"'

# PT删除检查时间间隔，默认10分钟
AUTO_REMOVE_TORRENTS_INTERVAL = 600
# 最橷预告片更新检查时间间隔，默认24小时
HOT_TRAILER_INTERVAL = 86400
# 单次检查多少个预告片数据
HOT_TRAILER_INTERVAL_TOTAL = 100
# qBittorrent转移文件检查时间间隔，默认5分钟
QBITTORRENT_TRANSFER_INTERVAL = 300

# 日志级别
LOG_LEVEL = logging.INFO

lock = threading.Lock()


class Config(object):
    __config = {}
    __instance = None

    def __init__(self):
        self.load_config()

    @staticmethod
    def get_instance():
        if Config.__instance:
            return Config.__instance
        try:
            lock.acquire()
            if not Config.__instance:
                Config.__instance = Config()
        finally:
            lock.release()
        return Config.__instance

    def load_config(self):
        try:
            with open(os.environ['NASTOOL_CONFIG'], mode='r', encoding='utf-8') as f:
                self.__config = yaml.load(f, yaml.Loader)
        except yaml.YAMLError as err:
            print("读取配置文件错误：" + str(err))
            return False

    def get_config(self):
        return self.__config


# 得到配置信息
def get_config():
    return Config.get_instance().get_config()


# 得到配置路径
def get_config_path():
    return os.environ['NASTOOL_CONFIG']


# 装载配置
def load_config():
    return Config.get_instance().load_config()


# 保存配置
def save_config(new_cfg):
    with open(os.environ['NASTOOL_CONFIG'], mode='w', encoding='utf-8') as f:
        return yaml.dump(new_cfg, f, allow_unicode=True)


# 检查配置信息
def check_config(config):
    # 剑查日志输出
    logtype = config['app']['logtype']
    log.info("【RUN】日志输出类型为：" + logtype)
    if logtype == "SERVER":
        logserver = config['app']['logserver']
        if not logserver:
            log.error("【RUN】logserver未配置，无法正常输出日志！")
        else:
            log.info("【RUN】日志将上送到服务器：" + logserver)
    elif logtype == "FILE":
        logpath = config['app']['logpath']
        if not logpath:
            log.error("【RUN】logpath未配置，无法正常输出日志！")
        else:
            log.info("【RUN】日志将写入文件：" + logpath)
    else:
        log.info("【RUN】日志将在终端输出")

    # 检查WEB端口
    web_port = config['app']['web_port']
    if not web_port:
        log.error("【RUN】web_port未设置，程序无法启动！")
        return False
    else:
        log.info("【RUN】WEB管瑞页面监听端口：" + str(web_port))
    # 检查登录用户和密码
    login_user = config['app']['login_user']
    login_password = config['app']['login_password']
    if not login_user or not login_password:
        log.error("【RUN】login_user或login_password未设置，程序无法启动！")
        return False
    else:
        log.info("【RUN】WEB管瑞页面用户：" + str(web_port))
    # 检查HTTPS
    ssl_cert = config['app']['ssl_cert']
    ssl_key = config['app']['ssl_key']
    if not ssl_cert or not ssl_key:
        log.info("【RUN】未启用https，请使用 http://IP:" + str(web_port) + " 访问管理页面")
    else:
        log.info("【RUN】已启用https，请使用 https://IP:" + str(web_port) + " 访问管理页面")

    # 检查媒体库目录路径
    movie_path = config['media']['movie_path']
    if not movie_path:
        log.error("【RUN】未配置movie_path，程序无法启动！")
        return False
    elif not os.path.exists(movie_path):
        log.error("【RUN】movie_path目录不存在，程序无法启动：" + movie_path)
        return False
    tv_path = config['media']['tv_path']
    if not tv_path:
        log.error("【RUN】未配置tv_path，程序无法启动！")
        return False
    elif not os.path.exists(tv_path):
        log.error("【RUN】tv_path目录不存在，程序无法启动：" + tv_path)
        return False
    hottrailer_path = config['media']['hottrailer_path']
    if not hottrailer_path:
        log.warn("【RUN】未配置hottrailer_path，最新预告下载功能将禁用！")
    elif not os.path.exists(hottrailer_path):
        log.warn("【RUN】hottrailer_path目录不存，最新预告下载功能将禁用：" + hottrailer_path)
    resiliosync_paths = config['media']['resiliosync_path']
    for resiliosync_path in resiliosync_paths:
        if not resiliosync_path:
            log.warn("【RUN】未配置resiliosync_path，ResilioSync资源同步功能将禁用！")
        elif not os.path.exists(resiliosync_path):
            log.warn("【RUN】resiliosync_path目录不存，ResilioSync资源同步功能将禁用：" + resiliosync_path)

    # 检查qbittorrent配置并测试连通性
    qbhost = config['qbittorrent']['qbhost']
    qbport = config['qbittorrent']['qbport']
    qbusername = config['qbittorrent']['qbusername']
    qbpassword = config['qbittorrent']['qbpassword']
    try:
        qbt = qbittorrentapi.Client(host=qbhost,
                                    port=qbport,
                                    username=qbusername,
                                    password=qbpassword,
                                    VERIFY_WEBUI_CERTIFICATE=False)
        qbt.auth_log_in()
    except Exception as err:
        log.error("【RUN】qBittorrent无法连接，请检查配置：" + str(err))
        return False
    save_path = config['qbittorrent']['save_path']
    if not save_path:
        log.error("【RUN】qbittorrent save_path未设置，程序无法启动：" + save_path)
        return False
    elif not os.path.exists(save_path):
        log.error("【RUN】qbittorrent save_path目录不存在，程序无法启动：" + save_path)
        return False
    save_containerpath = config['qbittorrent']['save_containerpath']
    if not save_containerpath:
        log.warn("【RUN】qbittorrent save_containerpath未设置，如果是Docker容器使用则必须配置该项，否则无法正常转移文件！")

    # 检查消息配置
    msg_channel = config['message']['msg_channel']
    if not msg_channel:
        log.warn("【RUN】msg_channel未配置，将无法接收到通知消息！")
    elif msg_channel == "wechat":
        corpid = config['message']['wechat']['corpid']
        corpsecret = config['message']['wechat']['corpsecret']
        agentid = config['message']['wechat']['agentid']
        if not corpid or not corpsecret or not agentid:
            log.warn("【RUN】wechat配置不完整，将无法接收到通知消息！")
        Token = config['message']['wechat']['Token']
        EncodingAESKey = config['message']['wechat']['EncodingAESKey']
        if not Token or not EncodingAESKey:
            log.warn("【RUN】wechat配置不完整，微信控制功能将无法使用！")
    elif msg_channel == "serverchan":
        sckey = config['message']['serverchan']['sckey']
        if not sckey:
            log.warn("【RUN】serverchan配置不完整，将无法接收到通知消息！")
    elif msg_channel == "telegram":
        telegram_token = config['message']['telegram']['telegram_token']
        telegram_chat_id = config['message']['telegram']['telegram_chat_id']
        if not telegram_token or not telegram_chat_id:
            log.warn("【RUN】telegram配置不完整，将无法接收到通知消息！")
    # 检查PT配置
    rmt_mode = config['pt']['rmt_mode']
    if rmt_mode == "LINK":
        log.info("【RUN】文件转移模式为：硬链接")
    else:
        log.info("【RUN】文件转移模式为：复制")

    rmt_tmdbkey = config['pt']['rmt_tmdbkey']
    if not rmt_tmdbkey:
        log.error("【RUN】rmt_tmdbkey未配置，程序无法启动！")
        return False
    rss_chinese = config['pt']['rmt_tmdbkey']
    if rss_chinese:
        log.info("【RUN】将只会下载含中文标题的影视资源！")
    ptsignin_cron = config['pt']['ptsignin_cron']
    if not ptsignin_cron:
        log.warn("【RUN】ptsignin_cron未配置，将无法使用PT站签到功能！")
    pt_seeding_time = config['pt']['pt_seeding_time']
    if not pt_seeding_time:
        log.warn("【RUN】pt_seeding_time未配置，自动删种功能要禁用！")
    else:
        log.info("【RUN】PT保种时间设置为：" + str(round(pt_seeding_time / 3600, 1)) + " 小时")

    pt_check_interval = config['pt']['pt_check_interval']
    if not pt_check_interval:
        log.warn("【RUN】pt_check_interval未配置，将不会自动检查和下载PT影视资源！")
    sites = config['pt']['sites']
    for key, value in sites.items():
        rssurl = sites[key]['rssurl']
        if not rssurl:
            log.warn("【RUN】" + key + "的 rssurl 未配置，该PT站的RSS订阅下载功能将禁用！")
        signin_url = sites[key]['signin_url']
        if not signin_url:
            log.warn("【RUN】" + key + "的 signin_url 未配置，该PT站的自动签到功能将禁用！")
        cookie = sites[key]['cookie']
        if not cookie:
            log.warn("【RUN】" + key + "的 cookie 未配置，该PT站的自动签到功能将禁用！")

    return True


if __name__ == "__main__":
    os.environ['NASTOOL_CONFIG'] = '/volume1/homes/admin/.config/nastool/config.yaml'
    cfg = get_config()
    print(cfg)
    check_config(cfg)