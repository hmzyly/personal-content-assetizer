# Personal Content Assetizer

个人“一鱼多吃”内容资产化 skill：把小宇宙播客链接、播客逐字稿、访谈、会议纪要、读书笔记和临时想法，整理成可复用内容资产，并按需生成小红书、朋友圈、口播、公众号、金句库、观点库和方法论卡片。

## 一句话介绍

把一条小宇宙播客链接先录入 Obsidian：抓取音频、转写逐字稿、生成播客笔记，再把这份原始语料拆成金句、观点、方法论、小红书、朋友圈、口播和公众号素材。

## 直接复制给 AI 的安装请求

```text
帮我安装一下这个 Skill，并且改造成适合我的 Obsidian 知识库和内容创作工作流。

这个 Skill 可以先把小宇宙播客链接录入到我的 Obsidian：抓取单集信息和音频，调用 AssemblyAI 转写逐字稿，生成包含导读、章节速览、要点回顾和原文逐字稿的播客笔记。然后再把播客逐字稿、访谈、会议纪要、读书笔记和临时想法，整理成可复用内容资产，并按需生成小红书、朋友圈、口播、公众号、金句库、观点库和方法论卡片。

请你先阅读仓库说明，帮我完成安装；如果涉及 Obsidian Vault 路径、播客素材目录、知识库目录结构、常用平台、内容风格、播客来源、AssemblyAI 转写 API key、小宇宙私有播客 token 等信息，你需要先向我提问，不要擅自写死路径或泄露账号信息。

安装后，请根据我的实际目录结构，协助我配置完整流程：小宇宙链接录入 Obsidian → 生成播客逐字稿笔记 → 校准说话人 → 提炼内容资产 → 输出小红书/朋友圈/口播/公众号版本。请把播客素材目录、内容资产目录、小红书/朋友圈/口播输出规则调整成适合我长期复用的版本。

仓库地址：
https://github.com/hmzyly/personal-content-assetizer
```

## 它适合做什么

- 把小宇宙播客单集录入 Obsidian：抓取单集信息、下载/提交音频转写、生成逐字稿笔记。
- 生成包含导读、章节速览、要点回顾和原文逐字稿的播客资料页。
- 根据用户提供的信息，把 `spk1/spk2` 校准为真实说话人。
- 从长逐字稿里提炼金句、观点、高光片段和 Q&A。
- 把一份材料拆成小红书、朋友圈、口播、公众号等多种版本。
- 把零散灵感沉淀成方法论卡片和可复用选题库。
- 根据个人 Obsidian 目录结构，形成长期内容资产工作流。

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

完整录入流程：

1. 准备 Obsidian Vault 路径。
2. 设置 `ASSEMBLYAI_API_KEY`。
3. 运行 `scripts/xiaoyuzhou_import.py`。
4. 检查生成的播客笔记。
5. 如果有 `spk1/spk2`，人工确认后替换为真实说话人。
6. 再用 skill 对这篇播客笔记做一鱼多吃。

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
