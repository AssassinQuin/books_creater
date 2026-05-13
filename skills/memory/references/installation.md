# Memory MCP Server 安装指南

## 概览

| 项目 | 值 |
|------|-----|
| 包名 | `mcp-memory-service` |
| 版本 | ≥10.38.2 |
| 许可证 | Apache-2.0 |
| 作者 | Heinrich Krupp |
| GitHub | [doobidoo/mcp-memory-service](https://github.com/doobidoo/mcp-memory-service) |
| PyPI | [mcp-memory-service](https://pypi.org/project/mcp-memory-service/) |
| 存储后端 | SQLite-vec（本地，默认） |
| 嵌入模型 | all-MiniLM-L6-v2（首次运行自动下载 ~25MB） |
| 数据目录 | `~/Library/Application Support/mcp-memory/` |

## 安装

### 方法 1：pip（推荐）

```bash
pip install mcp-memory-service
```

### 方法 2：uv

```bash
pip install uv
uv pip install mcp-memory-service
```

### 方法 3：uvx（无需安装，直接运行）

```bash
uvx --from mcp-memory-service memory server
```

## AI 客户端配置

### Claude Code

```bash
claude mcp add memory -- memory server
```

### Claude Desktop / VS Code / Trae（mcp.json）

```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["-m", "mcp_memory_service.server"],
      "env": {
        "MCP_MEMORY_STORAGE_BACKEND": "sqlite_vec"
      }
    }
  }
}
```

### 已安装 pipx 的系统

若通过 `pip install --user` 安装，找到可执行路径：

```bash
# macOS: 通常在 ~/Library/Python/<version>/bin/memory
which memory
```

配置使用完整路径：

```json
{
  "mcpServers": {
    "memory": {
      "command": "/Users/<user>/Library/Python/3.12/bin/memory",
      "args": ["server"],
      "env": {
        "HF_ENDPOINT": "https://hf-mirror.com"
      }
    }
  }
}
```

> `HF_ENDPOINT` 为可选项，用于加速国内模型下载。

## 验证

```bash
# 查看版本
memory --version

# 健康检查（在 AI 会话内）
# 调用 memory_health 工具，应返回 healthy
```

## 数据位置

| 文件 | 路径 |
|------|------|
| 向量数据库 | `~/Library/Application Support/mcp-memory/sqlite_vec.db` |
| 备份 | `~/Library/Application Support/mcp-memory/backups/` |
| 合并归档 | `~/Library/Application Support/mcp-memory/consolidation_archive/` |

## 常见问题

| 问题 | 解决 |
|------|------|
| 首次启动慢 | 正常，下载嵌入模型需 1-2 分钟 |
| 端口占用 | `export MCP_HTTP_PORT=8081` |
| 模型下载失败（国内） | 设置 `HF_ENDPOINT=https://hf-mirror.com` |
| Python 版本 | 需要 ≥3.10 |

## 更新

```bash
pip install --upgrade mcp-memory-service
```

## 更多文档

- [GitHub Wiki](https://github.com/doobidoo/mcp-memory-service/wiki)
- [安装指南](https://github.com/doobidoo/mcp-memory-service/blob/master/docs/setup-guide.md)
- [macOS 安装](https://github.com/doobidoo/mcp-memory-service/blob/master/docs/installation/macOS-installation.md)
