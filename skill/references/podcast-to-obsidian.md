# 播客转 Obsidian 后一鱼多吃

## 适用场景

用户给出小宇宙单集链接，或说“把这期播客转成小红书/朋友圈/口播/内容资产”。

## 使用脚本

主脚本：

```text
scripts/xiaoyuzhou_import.py
```

依赖说明：

```text
README.md
```

Obsidian Vault：

```text
由使用者通过 --vault-root 显式指定
```

## 执行顺序

1. 确认用户输入是小宇宙 episode URL。
2. 确认当前环境有 `ASSEMBLYAI_API_KEY`。如果没有，只问用户要 key，不要让用户自己找脚本。
3. 执行 `xiaoyuzhou_import.py`，写入 Obsidian。
4. 检查生成的 Markdown 是否存在、大小是否合理、是否包含 `## 原文逐字稿`。
5. 如果说话人是 `spk1/spk2`，根据用户提供的信息替换为真实姓名。
6. 读取生成笔记，进入一鱼多吃流程。

## 命令模板

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:ASSEMBLYAI_API_KEY='<从用户处临时获得，不写入文件>'
python '.\scripts\xiaoyuzhou_import.py' '<小宇宙 episode URL>' --vault-root '<你的 Obsidian Vault 路径>'
```

可选参数：

```powershell
--podcast '<Obsidian 播客目录名>'
--host '<主播名>'
--no-llm
```

## 输出后的内容资产化

优先从生成笔记中抽取：

- 章节速览：用于选题拆分。
- 要点回顾：用于 Q&A 和方法论卡片。
- 原文逐字稿：用于金句、高光片段和口播素材。
- 用户新增想法：优先级高于原文总结。

默认输出：

- 内容资产包。
- 小红书正文，1000 字以内。
- 朋友圈短版。
- 口播开头和 60-90 秒脚本。
- 方法论卡片。

## 安全规则

- 不要把 `ASSEMBLYAI_API_KEY`、`XIAOYUZHOU_ACCESS_TOKEN`、cookie、浏览器缓存路径写入任何公开内容。
- 不要把本机绝对路径写进小红书、朋友圈、公众号等公开文案。
- 转移或清理缓存时，必须先复制、校验文件数量和体积，再删除源路径。
