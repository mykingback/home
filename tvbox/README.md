# TVBox 接口整理

来源（每天自动抓取两个站，按地址去重、新的追加）：

- A 站：[https://526900.pages.dev/p/Sb3e96Z0](https://526900.pages.dev/p/Sb3e96Z0)（TVBox 接口中心）
- B 站：[https://tvbox.shenzjd.com/](https://tvbox.shenzjd.com/)（TvBox 资源导航）

每天自动抓取、测活、整理。任一站的接口有增减或换地址时，这里会自动跟着变。

- **更新时间：2026-11-23 05:48:58**
- **点播接口：58 个**（测活通过 55 个，未验证 0 个）
- **直播接口：117 个**（测活通过 105 个，未验证 0 个）
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

- B 站新追加的接口：软件小哥、小米、真六、王二小7线、王二小6线、挺好、香雅情、ray、高天流云_XYQ、高天流云、源聚合站、宝盒2线、老张、凯弟3线、王二小2线、少儿频道、菠菜园、刺桐、Kimentanm、B站直播1线、develop202、YanG1线、南风直播源、suxuang1线、初秋语、地方直播2、Yoursmile、易发源有、Tianmu、BMCH、全球TV直播、欧美大片直播、4GTV怡淳酒店梯子台湾节点720p、线路、FMMIPV6、suxuang、咪咕直播3、ipv63、新加坡梯子、综合直播、联通、移动、电视家、Ipv4、mlzlzj、gambiarras、华视TV直播、薄荷直播、各大源合集、TvLive、YY轮播1线、锋云直播、Kimentanm4线、斗鱼一起看1线、全球直播、虎牙一起看1线、易发TV直播、驸马影视电信专线、Guovin1线、无界UpdatedDaily版、夜空1、B站直播、应该能看、无界台标预览版、iptv直播、驸马影视移动专线、电视直播、斗鱼一起看2线、裤佬体育直播备、咪咕直播、yuan、PPV体育赛事直播.php、cluntop、乌拉TV直播、Mytv、综合直播2线、斗鱼一起看、很少、YY轮播、EPG直播、live1线、优选、手动不知何时更新、地方台直播、歌手直播、没4K.php、裤佬斗鱼直播、juli、YY轮播2线、韩国Panda直播、APTV、虎牙一起看、经典电视剧、裤佬体育直播、裤佬来疯直播、挺好直播、有效期27年7月.php、世界杯、俄罗斯源有、Kimentanm3线、裤佬抖音直播、develop2021线、港奥台国际、裤佬TikTok直播、MV、游魂、B站直播2线、裤佬IPTV直播、范明明需开启V6网络、虎牙一起看2线、裤佬酷狗直播、裤佬虎牙直播、奥斯卡、范明明需开启V6网络1线、裤佬快手直播、范明明、综合直播1线.php、cluntoptest、Guovin、探花、国际TV、综合直播3线、咪咕、台湾台、黄蚂蚁先锋推流源、央视频、澜露TV、咪咕TV直播.php
- 全死的点播接口：X4菠菜pro、X4更新专用接口、源聚合站
- 全死的直播接口：北京腾讯、浙江电信、上海电信1、上海电信2、辽宁联通、广东电信、develop202、无界UpdatedDaily版、无界台标预览版、综合直播2线、咪咕、央视频
- 全死的开车涩涩：无
- 未验证的点播接口：无
- 未验证的直播接口：无
- 未验证的开车涩涩：无
