# TVBox 接口整理

来源：[https://526900.pages.dev/p/Sb3e96Z0](https://526900.pages.dev/p/Sb3e96Z0)（TVBox 接口中心）

每天自动抓取、测活、整理。接口有增减或换地址时，这里会自动跟着变。

- **更新时间：2026-11-21 09:39:50**
- **点播接口：40 个**（测活通过 38 个，未验证 0 个）
- **直播接口：7 个**（测活通过 0 个，未验证 0 个）

## 直链（直接粘贴到 TVBox 里用）

- 点播：`https://raw.githubusercontent.com/mykingback/home/main/tvbox/vod.txt`
- 直播：`https://raw.githubusercontent.com/mykingback/home/main/tvbox/live.txt`
- 完整数据（含全部镜像地址与测活状态）：`https://raw.githubusercontent.com/mykingback/home/main/tvbox/interfaces.json`

## 文件说明

- `vod.txt` / `live.txt`：`名称,接口地址`，每行一个接口，首选地址是测活通过的镜像
- `interfaces.json`：每个接口的全部镜像地址、测活状态、备注

## 注意

- “未验证”是指本次抓取的机器连不上该地址（可能是网络限制），不等于死了；在你自己的网络或电视上可能能用，标出来是提醒你先试一下
- 全死的接口不会出现在 txt 里，只在 interfaces.json 里有记录
- 测活只看接口能不能打开、是不是有效的 TVBox 配置，不保证里面每个源都能播

## 本次状态

- 全死的点播接口：X4菠菜pro、X4更新专用接口
- 全死的直播接口：山东电信、北京腾讯、浙江电信、上海电信1、上海电信2、辽宁联通、广东电信
- 未验证的点播接口：无
- 未验证的直播接口：无
