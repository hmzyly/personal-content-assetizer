# Personal Content Assetizer

个人“一鱼多吃”内容资产化 skill：把小宇宙播客链接、播客逐字稿、访谈、会议纪要、读书笔记和临时想法，整理成可复用内容资产，并按需生成小红书、朋友圈、口播、公众号、金句库、观点库和方法论卡片。

## 包含什么

- `skill/`：Codex / WorkBuddy skill 本体。
- `scripts/xiaoyuzhou_import.py`：小宇宙单集转写到 Obsidian 的脚本。
- `requirements.txt`：脚本依赖。

## 安装 skill

把 `skill/` 文件夹复制到你的 skill 目录，并改名为：

```text
personal-content-assetizer
```

常见位置：

```text
~/.codex/skills/personal-content-assetizer
~/.workbuddy/skills/personal-content-assetizer
```

重启 Codex / WorkBuddy 后即可用这些说法触发：

- `帮我一鱼多吃这期播客`
- `把这段语料做成内容资产`
- `把这个播客转成小红书/朋友圈/口播`

## 安装脚本依赖

```powershell
pip install -r requirements.txt
```

## 配置转写 key

小宇宙转写依赖 AssemblyAI：

```powershell
$env:ASSEMBLYAI_API_KEY="你的 AssemblyAI API Key"
```

私有播客才需要：

```powershell
$env:XIAOYUZHOU_ACCESS_TOKEN="你的小宇宙 access token"
```

不要把 key 写进仓库或公开文档。

## 使用小宇宙转 Obsidian

```powershell
python .\scripts\xiaoyuzhou_import.py "https://www.xiaoyuzhoufm.com/episode/xxxx" --vault-root "D:\Your Obsidian Vault"
```

可选参数：

```powershell
--podcast "播客目录名"
--host "主播名"
--no-llm
```

脚本会写入：

```text
{VaultRoot}\02-博主素材库\{播客目录}\播客\
```

## 安全说明

- 不要提交 `ASSEMBLYAI_API_KEY`、`XIAOYUZHOU_ACCESS_TOKEN`、cookie、浏览器缓存或本机绝对路径。
- 公开文案里不要保留 Obsidian 本地路径。
- 生成后建议人工校准 `spk1/spk2` 的真实说话人。

