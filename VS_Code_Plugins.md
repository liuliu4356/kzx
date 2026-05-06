# VS Code 插件汇总（当前已安装）

## 基础开发插件

| 插件ID | 插件名称 | 功能说明 | X项目用途 |
|----------|----------|----------|----------|
| ms-python.python | Python | Python语言支持、调试、linting | X项目核心开发 |
| ms-python.pylance | Pylance | Python智能提示、类型检查 | 提升代码质量 |
| ms-python.debugpy | Debugpy | Python调试器 | 调试Web服务、巡检逻辑 |
| ms-python.vscode-python-envs | Python Envs | Python环境管理 | 管理虚拟环境 |
| ms-ceintl.vscode-language-pack-zh-hans | Chinese Language Pack | 中文语言包 | 中文界面 |

## AI编程插件（Vibe Coding核心）

| 插件ID | 插件名称 | 功能说明 | 用途 |
|----------|----------|----------|----------|
| anthropic.claude-code | Claude Code | Anthropic官方AI编程助手 | 主力AI编码工具 |
| sst-dev.opencode | OpenCode | 开源多模型AI编程工具 | 辅助调试、测试、文档 |
| saoudrizwan.claude-dev | Claude Dev | Claude编程助手扩展 | 增强AI编程体验 |
| openai.chatgpt | ChatGPT | ChatGPT集成 | 备用AI助手 |

## 版本管理插件

| 插件ID | 插件名称 | 功能说明 | 用途 |
|----------|----------|----------|----------|
| g8up.gitee | Gitee | Gitee集成 | 推送代码到Gitee |
| hbybyyang.gitee-vscode-plugin | Gitee Plugin | Gitee增强插件 | Gitee仓库管理 |
| cnblogs.vscode-cnb | 博客园 | 博客园发布 | 发布文档到博客园 |

## 远程开发插件

| 插件ID | 插件名称 | 功能说明 | 用途 |
|----------|----------|----------|----------|
| ms-vscode-remote.remote-ssh | Remote - SSH | SSH远程开发 | 连接远程服务器 |
| ms-vscode.remote-explorer | Remote Explorer | 远程资源管理 | 管理远程连接 |
| ms-azuretools.vscode-containers | Docker | Docker容器管理 | 管理X项目容器 |

## 文档编辑插件

| 插件ID | 插件名称 | 功能说明 | 用途 |
|----------|----------|----------|----------|
| yzhang.markdown-all-in-one | Markdown All in One | Markdown增强 | 编辑本文档 |
| toramaneseven.markdown-docx | Markdown DOCX | Markdown转Word | 文档格式转换 |
| tomoki1207.pdf | PDF | PDF查看器 | 查看PDF文档 |
| adamraichu.docx-viewer | DOCX Viewer | Word文档查看 | 查看Word文档 |
| ritwickdey.liveserver | Live Server | 本地开发服务器 | 预览Web页面 |

## 其他实用插件

| 插件ID | 插件名称 | 功能说明 |
|----------|----------|----------|
| vscode-icons-team.vscode-icons | VSCode Icons | 文件图标主题 |
| pkief.material-icon-theme | Material Icon Theme | 图标主题 |
| mermaidchart.vscode-mermaid-chart | Mermaid Chart | Mermaid图表编辑 |
| ecmel.vscode-html-css | HTML CSS | HTML/CSS支持 |
| pranaygp.vscode-css-peek | CSS Peek | CSS窥视 |
| mtxr.sqltools | SQLTools | SQL工具 |
| octref.vetur | Vetur | Vue工具 |
| ms-vscode.notepadplusplus-keybindings | Notepad++ Keybindings | 快捷键映射 |
| ms-vscode.powershell | PowerShell | PowerShell支持 |
| slevsque.vscode-zipexplorer | Zip Explorer | ZIP文件浏览 |
| golang.go | Go | Go语言支持 |
| docx-mt5.docx | DOCX | Word文档支持 |
| shahilkumar.docxreader | DOCX Reader | Word文档阅读 |

## VS Code 开发环境配置建议

### 推荐插件组合（X项目开发）
- **核心开发**: Python + Pylance + Debugpy + Python Envs
- **AI辅助**: Claude Code + OpenCode + Claude Dev
- **版本管理**: Gitee插件 + 博客园插件
- **远程开发**: Remote - SSH + Docker
- **文档编辑**: Markdown All in One + Markdown DOCX

### 调试配置（launch.json）
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: X Web服务",
            "type": "python",
            "request": "launch",
            "module": "src.main",
            "args": ["web", "--port", "8000"],
            "cwd": "${workspaceFolder}"
        },
        {
            "name": "Python: X 巡检",
            "type": "python",
            "request": "launch",
            "module": "src.main",
            "args": ["inspect", "--skip-llm", "--no-notify"],
            "cwd": "${workspaceFolder}"
        }
    ]
}
```

### 推荐设置（settings.json）
```json
{
    "python.analysis.typeCheckingMode": "basic",
    "editor.formatOnSave": true,
    "files.watcherExclude": {
        "**/.git/objects/**": true,
        "**/es-data/**": true,
        "**/grafana-data/**": true,
        "**/prometheus-data/**": true
    }
}
```
