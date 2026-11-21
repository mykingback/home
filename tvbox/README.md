# TVBox 接口整理

来源（每天自动抓取两个站，按地址去重、新的追加）：

- A 站：[https://526900.pages.dev/p/Sb3e96Z0](https://526900.pages.dev/p/Sb3e96Z0)（TVBox 接口中心）
- B 站：[https://tvbox.shenzjd.com/](https://tvbox.shenzjd.com/)（TvBox 资源导航）

每天自动抓取、测活、整理。任一站的接口有增减或换地址时，这里会自动跟着变。

- **更新时间：2026-11-21 07:59:25**
- **点播接口：58 个**（测活通过 55 个，未验证 0 个）
- **直播接口：117 个**（测活通过 104 个，未验证 0 个）
- **开车涩涩：1 个**（测活通过 1 个，未验证 0 个）
- **本次 B 站新追加：128 个**（地址在 A 站没有的）

## 直链（直接粘贴到 TVBox 里用）

- 点播：`https://raw.githubusercontent.com/mykingback/home/main/tvbox/vod.txt`
- 直播：`https://raw.githubusercontent.com/mykingback/home/main/tvbox/live.txt`
- 开车涩涩：`https://raw.githubusercontent.com/mykingback/home/main/tvbox/adult.txt`
- 完整数据（含全部镜像地址与测活状态）：`https://raw.githubusercontent.com/mykingback/home/main/tvbox/interfaces.json`

## 文件说明

- `vod.txt` / `live.txt` / `adult.txt`：`名称,接口地址`，每行一个接口，首选地址是测活通过的镜像
- `interfaces.json`：每个接口的全部镜像地址、测活状态、来源站、备注

## 注意

- “未验证”是指本次抓取的机器连不上该地址（可能是网络限制），不等于死了；在你自己的网络或电视上可能能用，标出来是提醒你先试一下
- 全死的接口不会出现在 txt 里，只在 interfaces.json 里有记录
- 测活只看接口能不能打开、是不是有效的 TVBox 配置，不保证里面每个源都能播

## 本次状态

- B 站新追加的接口：小米、菠菜园、高天流云_XYQ、软件小哥、王二小7线、王二小6线、真六、挺好、高天流云、宝盒2线、少儿频道、ray、凯弟3线、香雅情、王二小2线、刺桐、源聚合站、老张、驸马影视移动专线、地方直播2、夜空1、4GTV怡淳酒店梯子台湾节点720p、Guovin1线、cluntop、develop202、B站直播1线、南风直播源、虎牙一起看1线、应该能看、YanG1线、斗鱼一起看1线、线路、Yoursmile、欧美大片直播、咪咕直播3、裤佬体育直播备、Tianmu、BMCH、suxuang、初秋语、EPG直播、YY轮播1线、综合直播、全球TV直播、易发源有、suxuang1线、锋云直播、ipv63、华视TV直播、无界台标预览版、APTV、TvLive、移动、易发TV直播、gambiarras、yuan、无界UpdatedDaily版、电视直播、薄荷直播、mlzlzj、电视家、歌手直播、新加坡梯子、各大源合集、Ipv4、优选、全球直播、Kimentanm4线、PPV体育赛事直播.php、很少、Mytv、live1线、Kimentanm、驸马影视电信专线、FMMIPV6、综合直播2线、联通、没4K.php、裤佬斗鱼直播、iptv直播、咪咕直播、有效期27年7月.php、juli、手动不知何时更新、斗鱼一起看、虎牙一起看、B站直播、YY轮播、韩国Panda直播、乌拉TV直播、地方台直播、经典电视剧、YY轮播2线、范明明需开启V6网络、裤佬来疯直播、挺好直播、裤佬体育直播、俄罗斯源有、B站直播2线、MV、Kimentanm3线、范明明需开启V6网络1线、develop2021线、裤佬TikTok直播、斗鱼一起看2线、世界杯、裤佬抖音直播、裤佬IPTV直播、游魂、裤佬酷狗直播、奥斯卡、裤佬虎牙直播、港奥台国际、虎牙一起看2线、裤佬快手直播、综合直播3线、Guovin、综合直播1线.php、范明明、咪咕、国际TV、探花、台湾台、cluntoptest、黄蚂蚁先锋推流源、央视频、澜露TV、咪咕TV直播.php
- 全死的点播接口：X4菠菜pro、X4更新专用接口、源聚合站
- 全死的直播接口：北京腾讯、浙江电信、上海电信1、上海电信2、辽宁联通、广东电信、develop202、无界台标预览版、无界UpdatedDaily版、综合直播2线、地方台直播、咪咕、央视频
- 全死的开车涩涩：无
- 未验证的点播接口：无
- 未验证的直播接口：无
- 未验证的开车涩涩：无
