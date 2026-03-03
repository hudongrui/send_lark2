# send_lark2
Feishu/Lark Message Service & Command-line Tool for IC R&D Environment
面向IC环境的飞书消息服务 & 命令行工具

## 简介 / Introduction

send_lark2 是一个面向IC（集成电路）研发环境设计网络环境的飞书消息服务工具，支持通过命令行和Webhook方式向飞书用户、群组发送消息。

send_lark2 is a Feishu/Lark message service tool designed for IC (Integrated Circuit) R&D environments. It supports sending messages to Feishu/Lark users and groups via command line and webhook.


## 主要功能 / Main Features

- 📨 向飞书用户、群组发送文本消息 / Send text messages to Feishu/Lark users and groups
- 🎨 支持富文本卡片消息 / Support rich text card messages
- ⚡ 提供命令行工具和Webhook服务 / Provide command-line tool and webhook service

## 安装说明 / Installation

- 完整管理员手册/用户手册 详见 doc 目录

### 服务器端安装 (Server Setup)

1. 进入服务器目录 / Enter server directory
   ```bash
   cd send_lark2/server
   ```

2. 安装依赖 / Install dependencies
   ```bash
   uv pip install -r requirements.txt
   ```

3. 配置服务器 / Configure server
   ```bash
   cp conf/example.config.ini conf/config.ini
   ```
   编辑 `conf/config.ini` 文件，填入服务端配置信息。
   Edit `conf/config.ini` and fill in server configuration.

4. 启动服务器 / Start server
   ```bash
   make run_local
   ```

### 客户端安装 (Client Setup)

1. 进入客户端目录 / Enter client directory
   ```bash
   cd send_lark2/client
   ```

2. 安装依赖 / Install dependencies
   ```bash
   uv pip install -r requirements.txt
   ```

3. 配置客户端 / Configure client
   ```bash
   cp conf/example.config.ini conf/config.ini
   ```
   编辑 `conf/config.ini` 文件，填入服务器地址和客户端设置。
   Edit `conf/config.ini` and fill in server address and client settings.

## 使用方法 / Usage

### 命令行工具 (Command-line Tool)

#### 发送文本消息 / Send text message
```bash
python send_lark2 --user "test_user" --text "Hello from send_lark2!"
```

#### 发送卡片消息 / Send card message
```bash
python send_lark2 --chat-id "oc_1234567890" --card-file "card_template.json"
```

#### 查看帮助 / View help
```bash
python send_lark2 --help
```

### Webhook服务 (Webhook Service)

1. 启动Webhook服务 / Start webhook service
   ```bash
   python -m uvicorn app.main:app --port 8000
   ```

2. 发送Webhook请求 / Send webhook request
   ```bash
   curl -X POST http://localhost:8000/webhook/lark \
     -H "Content-Type: application/json" \
     -d '{"type": "text", "user": "test_user", "content": "Hello from webhook!"}'
   ```

## 配置文件 / Configuration

### 服务器配置 (Server Config - conf/config.ini)

```ini
[default]
APP_ID=your-feishu-app-id  # 飞书应用ID
APP_SECRET=your-feishu-app-secret  # 飞书应用密钥
LOG_PATH=/tmp/lark_msg_service/log  # 日志路径
SERVER_PORT=5000  # 服务器端口
```

### 客户端配置 (Client Config - conf/config.ini)

```ini
[default]
SERVER_HOST=127.0.0.1  # 服务器地址
SERVER_PORT=5000  # 服务器端口
LOG_PATH=/tmp/send_lark_webhook/log  # 日志路径
```

## 许可证 / License

本项目采用 GNU General Public License v3.0 许可证。详情请查看 [LICENSE](LICENSE) 文件。

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.

## 作者 / Authors

- **dongruihu** - 初始开发 / Initial development

## 支持 / Support

如有问题或建议，请联系作者。

For issues or suggestions, please contact the author.