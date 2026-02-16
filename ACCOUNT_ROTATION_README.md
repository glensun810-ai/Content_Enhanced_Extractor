# 账号轮换策略详解

## 目录
- [轮换机制概述](#轮换机制概述)
- [核心轮换算法](#核心轮换算法)
- [冷却时间机制](#冷却时间机制)
- [账号健康评分](#账号健康评分)
- [使用示例](#使用示例)
- [最佳实践](#最佳实践)

---

## 轮换机制概述

### 为什么需要账号轮换？

小红书对账号行为有严格的监控，单一账号频繁搜索容易被识别为异常行为。账号轮换可以：

1. **分散风险**: 避免单一账号过度使用
2. **模拟真人**: 不同账号交替使用更像真实用户
3. **延长寿命**: 每个账号都有休息时间
4. **容错机制**: 一个账号出问题时自动切换其他账号

### 轮换流程图

```
开始搜索关键词
    ↓
获取下一个可用账号
    ↓
┌──────────────────────┐
│  账号筛选            │
│  - 排除封禁/受限账号 │
│  - 排除冷却中账号    │
│  - 排除连续失败账号  │
└──────────────────────┘
    ↓
┌──────────────────────┐
│  综合评分排序        │
│  - 使用次数 (权重 10)  │
│  - 失败次数 (权重 50)  │
│  - 冷却剩余时间      │
│  - 账号状态          │
└──────────────────────┘
    ↓
选择评分最低的账号
    ↓
执行搜索任务
    ↓
记录使用并更新状态
    ↓
等待冷却时间
```

---

## 核心轮换算法

### 1. 账号筛选

```python
def get_next_account(self, respect_cooldown=True, cooldown_hours=1.0):
    """获取下一个可用账号"""
    
    available_accounts = []
    cooling_accounts = []
    
    for acc in self.accounts.values():
        # 排除被封禁或受限的账号
        if acc.status in [BANNED, LIMITED]:
            continue
        
        # 检查冷却时间
        if respect_cooldown and acc.last_used_at:
            last_used = datetime.fromisoformat(acc.last_used_at)
            cooldown_end = last_used + timedelta(hours=cooldown_hours)
            
            if now < cooldown_end:
                cooling_accounts.append((acc, cooldown_end))
                continue
        
        available_accounts.append(acc)
    
    # 优先从可用账号中选择
    if available_accounts:
        return best_account(available_accounts)
    
    # 所有账号都在冷却中，返回最早可用的
    elif cooling_accounts:
        return earliest_available(cooling_accounts)
    
    # 没有可用账号
    else:
        return None
```

### 2. 综合评分算法

```python
def get_account_for_search(self):
    """获取用于搜索的账号 (综合评分)"""
    
    candidates = []
    
    for acc in self.accounts.values():
        # 排除被封禁的账号
        if acc.status == BANNED:
            continue
        
        # 排除连续失败 3 次以上的账号
        if acc.consecutive_failures >= 3:
            continue
        
        # 计算冷却剩余时间 (分钟)
        cooldown_remaining = 0
        if acc.last_used_at:
            last_used = datetime.fromisoformat(acc.last_used_at)
            cooldown_end = last_used + timedelta(hours=1)
            if now < cooldown_end:
                cooldown_remaining = (cooldown_end - now).total_seconds() / 60
        
        # 计算综合得分 (越低越好)
        score = 0
        score += acc.total_searches * 10      # 使用次数权重
        score += acc.consecutive_failures * 50  # 失败次数权重
        score += cooldown_remaining            # 冷却剩余时间
        if acc.status != ACTIVE:
            score += 100  # 非活跃状态惩罚
        
        candidates.append((acc, score))
    
    # 返回得分最低的账号
    candidates.sort(key=lambda x: x[1])
    return candidates[0][0]
```

### 3. 评分权重说明

| 因素 | 权重 | 说明 |
|-----|------|------|
| **使用次数** | x10 | 每多使用 1 次，得分 +10 |
| **失败次数** | x50 | 每失败 1 次，得分 +50 |
| **冷却剩余** | x1 | 每分钟剩余冷却时间，得分 +1 |
| **非活跃状态** | +100 | 状态不是 ACTIVE，直接 +100 |

**示例计算**:

```
账号 A: 使用 5 次，失败 0 次，不在冷却，状态 ACTIVE
得分 = 5*10 + 0*50 + 0 + 0 = 50

账号 B: 使用 3 次，失败 1 次，冷却剩余 30 分钟，状态 ACTIVE
得分 = 3*10 + 1*50 + 30 + 0 = 110

账号 C: 使用 2 次，失败 0 次，不在冷却，状态 SUSPICIOUS
得分 = 2*10 + 0*50 + 0 + 100 = 120

结果：选择账号 A (得分最低)
```

---

## 冷却时间机制

### 冷却时间配置

```python
# 默认冷却时间
COOLDOWN_HOURS = 1.0  # 1 小时

# 可自定义
account = manager.get_next_account(
    respect_cooldown=True,
    cooldown_hours=2.0  # 设置为 2 小时
)
```

### 冷却时间计算

```python
# 假设账号最后使用时间：10:00
last_used = datetime(2026, 2, 17, 10, 0, 0)

# 冷却结束时间：11:00
cooldown_end = last_used + timedelta(hours=1)

# 当前时间：10:30
now = datetime(2026, 2, 17, 10, 30, 0)

# 冷却剩余：30 分钟
remaining = (cooldown_end - now).total_seconds() / 60  # 30
```

### 冷却状态

| 状态 | 说明 | 是否可用 |
|-----|------|---------|
| **冷却中** | 距离上次使用 < 1 小时 | ❌ 否 |
| **可用** | 距离上次使用 >= 1 小时 | ✅ 是 |
| **紧急** | 所有账号都在冷却中 | ⚠️ 选择最早可用的 |

---

## 账号健康评分

### 账号状态

```python
class AccountStatus(Enum):
    ACTIVE = "active"       # ✅ 正常
    SUSPICIOUS = "suspicious"  # ⚠️ 可疑
    LIMITED = "limited"     # 🚫 受限
    BANNED = "banned"       # ❌ 封禁
    UNKNOWN = "unknown"     # ❓ 未知
```

### 状态转换

```
UNKNOWN ──成功登录──> ACTIVE
  │                     │
  │                     └──登录失败 1-2 次──> SUSPICIOUS
  │                                           │
  │                     └──登录成功───────────┘
  │
  └─────────────────────> LIMITED (搜索被限制)
                          │
                          └──长时间未使用/违规──> BANNED
```

### 健康度评估

```python
def get_account_health(acc: AccountConfig) -> str:
    """评估账号健康度"""
    
    if acc.status == "banned":
        return "❌ 已封禁"
    
    if acc.status == "limited":
        return "🚫 已受限"
    
    if acc.consecutive_failures >= 3:
        return "⚠️ 高风险 (连续失败)"
    
    if acc.status == "suspicious":
        return "⚠️ 可疑 (需观察)"
    
    # 计算使用频率
    if acc.total_searches > 50:
        return "⚠️ 过度使用"
    
    if acc.total_searches > 20:
        return "🟡 中度使用"
    
    return "✅ 健康"
```

---

## 使用示例

### 基础使用

```python
from xhs_account_manager import AccountManager

# 初始化
manager = AccountManager()
manager.setup_master_password()

# 添加账号
manager.add_account("13800138000", "password123", notes="主账号")
manager.add_account("13900139000", "password456", notes="备用账号")

# 获取下一个可用账号
account = manager.get_next_account()
print(f"使用账号：{account.username}")

# 记录使用
manager.record_usage(account.account_id)
```

### 高级轮换

```python
# 获取用于搜索的账号 (综合评分)
account = manager.get_account_for_search()

# 获取所有可用账号
available = manager.get_all_available_accounts()

# 获取统计信息
stats = manager.get_account_statistics()
print(f"总账号：{stats['total']}")
print(f"可用：{stats['total'] - len([s for s in stats['by_status'] if s in ['banned', 'limited']])}")
print(f"冷却中：{stats['in_cooldown']}")
```

### 在监控器中使用

```python
from xhs_browser_monitor import XiaohongshuBrowserMonitor, MonitorConfig
from xhs_account_manager import AccountManager

# 配置
config = MonitorConfig(
    keywords=["GEO 优化", "AI 搜索排名", "品牌获客"],
    monitor_period=MonitorPeriod.ONE_WEEK,
    max_posts_per_keyword=30
)

# 初始化账号管理
account_manager = AccountManager()
account_manager.setup_master_password()

# 创建监控器 (带账号轮换)
monitor = XiaohongshuBrowserMonitor(config, account_manager=account_manager)

# 运行 (自动轮换账号)
results = await monitor.run()
```

---

## 最佳实践

### 1. 账号数量建议

| 场景 | 推荐账号数 | 说明 |
|-----|----------|------|
| **个人使用** | 1-2 个 | 低频率，手动控制 |
| **小团队** | 3-5 个 | 中等频率，自动轮换 |
| **企业使用** | 5+ 个 | 高频率，多账号分散 |

### 2. 冷却时间设置

```python
# 单账号：延长冷却时间
account = manager.get_next_account(cooldown_hours=2.0)

# 多账号：标准冷却时间
account = manager.get_next_account(cooldown_hours=1.0)

# 紧急情况：忽略冷却
account = manager.get_next_account(respect_cooldown=False)
```

### 3. 账号养护

```python
# 定期检查账号状态
for acc in manager.accounts.values():
    health = get_account_health(acc)
    print(f"{acc.username}: {health}")

# 标记异常账号
if acc.consecutive_failures >= 3:
    manager.update_account_status(acc.account_id, AccountStatus.SUSPICIOUS)

# 恢复健康账号
if acc.status == SUSPICIOUS and acc.consecutive_failures == 0:
    manager.update_account_status(acc.account_id, AccountStatus.ACTIVE)
```

### 4. 监控告警

```python
# 设置告警阈值
MAX_FAILURES = 3
MAX_SEARCHES_PER_DAY = 20

# 检查并告警
for acc in manager.accounts.values():
    if acc.consecutive_failures >= MAX_FAILURES:
        print(f"⚠️ 账号 {acc.username} 连续失败 {acc.consecutive_failures} 次")
    
    if acc.total_searches >= MAX_SEARCHES_PER_DAY:
        print(f"⚠️ 账号 {acc.username} 今日已达搜索上限")
```

### 5. 轮换日志

```python
# 记录轮换日志
import logging

logging.basicConfig(filename='account_rotation.log', level=logging.INFO)

def log_rotation(account, keyword):
    logging.info(
        f"{datetime.now().isoformat()} - "
        f"账号：{account.username}, "
        f"关键词：{keyword}, "
        f"使用次数：{account.total_searches}"
    )

# 使用
log_rotation(account, "GEO 优化")
```

---

## 故障排查

### 问题 1: 所有账号都在冷却中

```python
# 检查冷却状态
stats = manager.get_account_statistics()
print(f"冷却中：{stats['in_cooldown']}/{stats['total']}")

# 解决方案 1: 忽略冷却 (紧急)
account = manager.get_next_account(respect_cooldown=False)

# 解决方案 2: 缩短冷却时间
account = manager.get_next_account(cooldown_hours=0.5)

# 解决方案 3: 添加更多账号
manager.add_account("新账号", "密码")
```

### 问题 2: 账号连续失败

```python
# 检查失败账号
for acc in manager.accounts.values():
    if acc.consecutive_failures >= 3:
        print(f"账号 {acc.username} 连续失败 {acc.consecutive_failures} 次")
        
        # 暂停使用
        manager.update_account_status(acc.account_id, AccountStatus.SUSPICIOUS)
        
        # 手动登录测试
        # ...
```

### 问题 3: 轮换不均匀

```python
# 检查使用分布
for acc in sorted(manager.accounts.values(), key=lambda x: x.total_searches):
    print(f"{acc.username}: {acc.total_searches}次")

# 如果分布不均，手动调整
# 方案 1: 重置使用次数
acc.total_searches = 0

# 方案 2: 添加新账号稀释
manager.add_account("新账号", "密码")
```

---

**文档版本**: v1.0  
**更新时间**: 2026-02-17  
**相关文档**: ACCOUNT_MANAGER_README.md, ANTI_DETECTION_README.md
