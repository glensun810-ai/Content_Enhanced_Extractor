# 小红书账号管理系统使用指南

## 目录
- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [命令行使用](#命令行使用)
- [编程接口](#编程接口)
- [安全说明](#安全说明)

---

## 功能特性

### 🔐 安全密码存储
- **AES-256 加密**: 使用 cryptography 库进行工业级加密
- **PBKDF2 密钥派生**: 100,000 次迭代，防止暴力破解
- **独立盐值**: 每个账号独立加密盐值
- **文件权限保护**: 配置文件权限设置为 600 (仅所有者可读写)

### 📋 多账号管理
- **无限账号数量**: 支持添加任意数量的小红书账号
- **账号备注**: 可为每个账号添加备注信息
- **账号状态追踪**: 记录账号使用状态 (正常/可疑/受限/封禁)
- **使用统计**: 记录每个账号的使用次数和最后使用时间

### 🔄 智能账号轮换
- **自动轮换**: 自动选择使用次数最少的账号
- **冷却时间**: 1 小时内不重复使用同一账号
- **状态过滤**: 自动跳过被封禁或受限的账号
- **手动选择**: 支持手动指定使用特定账号

### 📊 健康监控
- **登录状态持久化**: 每个账号独立的登录状态文件
- **失败记录**: 记录连续失败次数和最后错误信息
- **状态更新**: 根据登录结果自动更新账号状态

---

## 快速开始

### 1. 安装依赖

```bash
pip install cryptography pyyaml
```

### 2. 首次设置

运行主程序，会自动进入账号设置向导：

```bash
python3 xhs_browser_monitor.py
```

首次运行时会提示：
```
[!] 未检测到账号配置

请选择操作:
  1. 添加新账号
  2. 使用手动登录 (不保存账号)

请输入选项 (1/2):
```

### 3. 添加账号

选择 `1` 后，会提示设置主密码：

```
============================================================
设置主密码
============================================================
主密码用于加密存储的小红书账号密码
请妥善保管，丢失后将无法恢复账号密码

请输入主密码：********
请确认主密码：********
✅ 主密码设置成功
```

然后输入账号信息：

```
当前已添加 0 个账号
是否添加账号？(y/n): y

请输入小红书账号 (手机号/邮箱): 13800138000
请输入密码：********
请输入手机号 (可选): 13800138000
请输入备注 (可选): 主账号
```

### 4. 使用账号

设置完成后，再次运行程序时：

```bash
python3 xhs_browser_monitor.py
```

会提示验证主密码并选择账号：

```
============================================================
验证主密码
============================================================
请输入主密码以解密账号信息

主密码：********
✅ 主密码验证成功

======================================================================
账号列表
======================================================================
ID       用户名                 状态       使用次数   最后使用            
----------------------------------------------------------------------
acc_001  138****8000           ✅ active         5  2026-02-17 10:30:00
acc_002  139****9000           ⚠️ suspicious    12  2026-02-16 15:20:00
======================================================================
总账号数：2
  active: 1 个
  suspicious: 1 个

请选择账号:
  0. 使用自动轮换
  acc_001. 138****8000 (active)
  acc_002. 139****9000 (suspicious)

请输入账号 ID (直接回车使用自动轮换):
```

---

## 命令行使用

账号管理器提供独立的命令行工具：

### 查看帮助

```bash
python3 xhs_account_manager.py
```

### 交互式设置

```bash
python3 xhs_account_manager.py setup
```

### 添加账号

```bash
python3 xhs_account_manager.py add
```

### 列出账号

```bash
python3 xhs_account_manager.py list
```

### 删除账号

```bash
python3 xhs_account_manager.py remove
```

### 查看状态

```bash
python3 xhs_account_manager.py status
```

---

## 编程接口

### 初始化账号管理器

```python
from xhs_account_manager import AccountManager

# 创建管理器
manager = AccountManager()

# 设置主密码 (首次使用)
manager.setup_master_password(new_password=True)

# 或验证主密码 (已有账号)
password = manager.setup_master_password()
```

### 添加账号

```python
# 添加单个账号
account_id = manager.add_account(
    username="13800138000",
    password="your_password",
    phone="13800138000",
    notes="主账号"
)
```

### 获取账号

```python
# 获取账号配置
account = manager.get_account("acc_001")

# 获取账号密码
password = manager.get_password("acc_001")

# 获取下一个可用账号 (轮换策略)
next_account = manager.get_next_account()
```

### 更新账号状态

```python
from xhs_account_manager import AccountStatus

# 标记为正常
manager.update_account_status("acc_001", AccountStatus.ACTIVE)

# 标记为可疑
manager.update_account_status("acc_002", AccountStatus.SUSPICIOUS, "登录失败")

# 标记为受限
manager.update_account_status("acc_003", AccountStatus.LIMITED)
```

### 记录使用

```python
# 记录账号使用
manager.record_usage("acc_001")
```

### 删除账号

```python
manager.remove_account("acc_001")
```

### 在监控器中使用

```python
from xhs_browser_monitor import XiaohongshuBrowserMonitor, MonitorConfig
from xhs_account_manager import AccountManager

# 初始化账号管理器
account_manager = AccountManager()
account_manager.setup_master_password()

# 创建监控配置
config = MonitorConfig(
    keywords=["GEO 优化", "AI 搜索排名"],
    monitor_period=MonitorPeriod.ONE_WEEK,
    max_posts_per_keyword=30,
    extract_comments=True,
    headless=False
)

# 创建监控器 (传入账号管理器)
monitor = XiaohongshuBrowserMonitor(config, account_manager=account_manager)

# 运行监控
results = await monitor.run()
```

---

## 安全说明

### 🔒 主密码安全

1. **主密码强度**: 建议使用至少 12 位，包含大小写字母、数字和符号
2. **主密码保管**: 主密码不会保存在任何地方，丢失后无法恢复账号
3. **主密码修改**: 如需修改主密码，需要：
   - 删除所有账号
   - 删除盐值文件 (`.xhs_salt`)
   - 重新设置并添加账号

### 📁 文件安全

账号相关文件：
```
xhs_accounts.yaml        # 账号配置 (已加密)
.xhs_salt                # 加密盐值 (权限 600)
xhs_account_states/      # 账号登录状态目录
  acc_001.json
  acc_002.json
```

所有敏感文件的权限都设置为 `600` (仅所有者可读写)。

### ⚠️ 注意事项

1. **不要分享**: 不要将 `xhs_accounts.yaml` 和 `.xhs_salt` 文件分享给他人
2. **备份**: 建议定期备份账号配置文件
3. **清理**: 删除账号时，会同时删除状态文件，确保不留痕迹
4. **内存安全**: 密码只在内存中解密，使用后立即释放

### 🛡️ 加密细节

```python
# 加密流程
明文密码 → PBKDF2(盐值，100000 次迭代) → AES-256 密钥 → Fernet 加密 → Base64 编码

# 存储格式
password_encrypted: "Z0FBQUFBQm1kWF9vZ0VnN3hQTWpRb..."
```

---

## 账号轮换策略

### 自动轮换逻辑

```python
def get_next_account(self):
    """获取下一个可用账号"""
    # 1. 过滤掉被封禁/受限的账号
    # 2. 跳过最近 1 小时内使用过的账号
    # 3. 选择使用次数最少的账号
    
    available = [acc for acc in accounts 
                 if acc.status not in [BANNED, LIMITED]
                 and not used_in_last_hour(acc)]
    
    return min(available, key=lambda x: x.total_searches)
```

### 使用建议

| 账号数量 | 推荐策略 |
|---------|---------|
| 1 个 | 每天最多使用 2-3 小时，搜索间隔 45-90 分钟 |
| 2-3 个 | 轮换使用，每个账号每天最多 1 小时 |
| 4+ 个 | 完全自动轮换，每个账号使用频率更低 |

---

## 故障排查

### 忘记主密码

如果忘记主密码，只能重置：

```bash
# 1. 删除加密文件
rm xhs_accounts.yaml .xhs_salt

# 2. 重新设置
python3 xhs_account_manager.py setup
```

### 账号状态异常

如果账号状态变为 `suspicious` 或 `limited`：

1. 暂停使用该账号 24-48 小时
2. 手动登录账号，正常浏览小红书
3. 进行一些真人互动 (点赞、收藏)
4. 之后再尝试使用

### 自动登录失败

自动登录可能因为滑块验证失败，建议：

1. 首次使用手动登录
2. 保存登录状态
3. 后续使用保存的状态，避免重复登录

---

**文档版本**: v1.0  
**更新时间**: 2026-02-17  
**技术支持**: 请参考 xhs_account_manager.py 源码
