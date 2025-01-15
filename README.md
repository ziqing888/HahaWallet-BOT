# Haha Wallet



## 概述

**Haha Wallet** 是一个自动化脚本，旨在帮助用户定时登录 **Karma Haha Wallet** 并自动领取每日签到奖励。通过该脚本，用户无需手动操作即可定期获取奖励，简化了日常维护流程。

## 功能

- **自动登录**：使用多个账户自动登录 Karma Haha Wallet。
- **获取用户信息**：获取每个账户的当前 Karma 及余额信息。
- **检查并领取签到奖励**：自动检查每日签到状态，并在可领取时自动领取奖励。
- **多线程处理**：支持同时处理多个账户，提高效率。
- **ASCII 艺术横幅**：启动时显示美观的ASCII艺术横幅，提升用户体验。
- **日志轮转**：自动管理日志文件大小，避免日志文件过大。

## 目录

- [Haha Wallet](#haha-wallet)
  - [概述](#概述)
  - [功能](#功能)
  - [目录](#目录)
  - [安装](#安装)
  - [配置](#配置)
  - [使用](#使用)
  - [日志管理](#日志管理)
  - [安全性](#安全性)
  - [常见问题](#常见问题)
  - [贡献](#贡献)
  - [许可证](#许可证)
  - [联系方式](#联系方式)

## 安装

### 1. 克隆仓库

首先，克隆本仓库到您的本地机器：

```bash
git clone https://github.com/ziqing888/HahaWallet-BOT.git
cd HahaWallet-BOT
```
2. 创建虚拟环境（推荐）
为了避免依赖冲突，建议使用虚拟环境：
```
python3 -m venv venv
source venv/bin/activate  # 对于Windows用户使用 `venv\Scripts\activate`
```
3. 安装依赖
使用 pip 安装所需的Python库：
```
pip install -r requirements.txt
```
## 配置
1. 配置账户信息
在项目根目录下，创建或编辑 accounts.json 文件，添加您的账户信息。确保每个账户包含 Email 和 Password 字段。

示例 accounts.json：
```
[
    {
        "Email": "user1@example.com",
        "Password": "password1"
    },
    {
        "Email": "user2@example.com",
        "Password": "password2"
    },
    {
        "Email": "user3@example.com",
        "Password": "password3"
    }
]
```
## 启动脚本
在项目根目录下，运行以下命令启动脚本：
```
python3 main.py
```

