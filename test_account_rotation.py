"""
账号轮换策略测试和演示

展示账号轮换机制的工作原理
"""

import asyncio
from datetime import datetime, timedelta
from xhs_account_manager import AccountManager, AccountStatus


def demo_rotation_strategy():
    """演示账号轮换策略"""
    
    print("=" * 70)
    print("小红书账号轮换策略演示")
    print("=" * 70)
    
    # 创建测试账号管理器
    manager = AccountManager()
    
    # 模拟已有账号配置
    print("\n1. 模拟账号配置...")
    
    # 手动创建测试账号 (实际使用时通过 add_account 添加)
    from xhs_account_manager import AccountConfig
    
    test_accounts = [
        {"id": "acc_001", "username": "138****8000", "searches": 5, "status": "active", "last_used": None},
        {"id": "acc_002", "username": "139****9000", "searches": 12, "status": "active", "last_used": datetime.now() - timedelta(minutes=30)},
        {"id": "acc_003", "username": "137****7000", "searches": 3, "status": "active", "last_used": datetime.now() - timedelta(hours=2)},
        {"id": "acc_004", "username": "136****6000", "searches": 20, "status": "suspicious", "last_used": datetime.now() - timedelta(hours=5)},
        {"id": "acc_005", "username": "135****5000", "searches": 8, "status": "limited", "last_used": None},
    ]
    
    for acc_data in test_accounts:
        acc = AccountConfig(
            account_id=acc_data["id"],
            username=acc_data["username"],
            password_encrypted="encrypted_password",
            status=acc_data["status"],
            total_searches=acc_data["searches"],
            last_used_at=acc_data["last_used"].isoformat() if acc_data["last_used"] else "",
            consecutive_failures=0,
            last_error="",
            created_at=datetime.now().isoformat(),
            notes=""
        )
        manager.accounts[acc_data["id"]] = acc
    
    print(f"   创建了 {len(manager.accounts)} 个测试账号")
    
    # 显示账号列表
    print("\n2. 当前账号状态:")
    print("-" * 70)
    print(f"{'账号 ID':<10} {'用户名':<18} {'状态':<12} {'使用次数':<10} {'最后使用':<20}")
    print("-" * 70)
    
    for acc_id, acc in manager.accounts.items():
        last_used = acc.last_used_at[:19] if acc.last_used_at else "从未"
        print(f"{acc_id:<10} {acc.username:<18} {acc.status:<12} {acc.total_searches:<10} {last_used:<20}")
    
    print("-" * 70)
    
    # 演示轮换选择
    print("\n3. 轮换策略演示:")
    print("-" * 70)
    
    # 场景 1: 正常轮换
    print("\n场景 1: 正常轮换 (尊重冷却时间)")
    selected = manager.get_next_account(respect_cooldown=True, cooldown_hours=1.0)
    if selected:
        print(f"   选中账号：{selected.username}")
        print(f"   原因：使用次数较少 ({selected.total_searches}次) 且不在冷却中")
    else:
        print("   没有可用账号")
    
    # 场景 2: 忽略冷却时间
    print("\n场景 2: 忽略冷却时间 (紧急情况)")
    selected = manager.get_next_account(respect_cooldown=False)
    if selected:
        print(f"   选中账号：{selected.username}")
        print(f"   原因：使用次数最少的账号")
    
    # 场景 3: 综合评分选择
    print("\n场景 3: 综合评分选择 (考虑失败次数)")
    # 设置一个账号有连续失败
    manager.accounts["acc_002"].consecutive_failures = 5
    
    selected = manager.get_account_for_search()
    if selected:
        print(f"   选中账号：{selected.username}")
        print(f"   原因：综合评分最低 (考虑使用次数、失败次数、冷却时间)")
    
    # 场景 4: 获取统计信息
    print("\n场景 4: 账号统计信息")
    stats = manager.get_account_statistics()
    print(f"   总账号数：{stats['total']}")
    print(f"   按状态分布：{stats['by_status']}")
    print(f"   总搜索次数：{stats['total_searches']}")
    print(f"   冷却中账号：{stats['in_cooldown']}")
    
    print("\n" + "=" * 70)
    print("演示完成")
    print("=" * 70)


async def simulate_multi_account_search():
    """模拟多账号轮换搜索"""
    
    print("\n" + "=" * 70)
    print("多账号轮换搜索模拟")
    print("=" * 70)
    
    manager = AccountManager()
    
    # 创建测试账号
    from xhs_account_manager import AccountConfig
    
    keywords = ["GEO 优化", "AI 搜索排名", "品牌获客", "社交媒体营销"]
    
    for i in range(3):
        acc = AccountConfig.create(
            account_id=f"acc_{i+1:03d}",
            username=f"1380013800{i}",
            password=f"password{i}",
            notes=f"测试账号{i+1}"
        )
        acc.password_encrypted = "encrypted"
        acc.status = AccountStatus.ACTIVE.value
        manager.accounts[acc.account_id] = acc
    
    print(f"\n配置了 {len(manager.accounts)} 个账号")
    print(f"需要搜索 {len(keywords)} 个关键词\n")
    
    # 模拟搜索过程
    for i, keyword in enumerate(keywords):
        print(f"\n[关键词 {i+1}/{len(keywords)}]: {keyword}")
        
        # 获取下一个可用账号
        account = manager.get_account_for_search()
        
        if account:
            print(f"  使用账号：{account.username} (ID: {account.account_id})")
            print(f"  该账号已使用：{account.total_searches}次")
            
            # 模拟搜索
            print(f"  正在搜索 '{keyword}'...")
            await asyncio.sleep(0.5)  # 模拟搜索时间
            
            # 记录使用
            manager.record_usage(account.account_id)
            print(f"  搜索完成，账号使用次数：{account.total_searches + 1}")
        else:
            print(f"  没有可用账号，跳过")
        
        # 模拟延迟
        await asyncio.sleep(0.5)
    
    # 显示最终统计
    print("\n" + "-" * 70)
    print("搜索完成 - 最终统计")
    print("-" * 70)
    
    for acc_id, acc in manager.accounts.items():
        print(f"{acc.username}: {acc.total_searches}次搜索")
    
    print("-" * 70)


def show_rotation_rules():
    """显示轮换规则说明"""
    
    print("\n" + "=" * 70)
    print("账号轮换规则说明")
    print("=" * 70)
    
    print("""
轮换策略核心规则:

1. 【排除规则】以下账号不会被选择:
   - 状态为 BANNED (封禁) 的账号
   - 状态为 LIMITED (受限) 的账号
   - 连续失败次数 >= 3 的账号

2. 【冷却时间】
   - 默认冷却时间：1 小时
   - 冷却时间内不会重复使用同一账号
   - 如果所有账号都在冷却中，选择最早可用的

3. 【优先级排序】(综合评分最低者优先)
   - 账号状态：ACTIVE 优先于其他状态
   - 使用次数：越少越优先 (权重 x10)
   - 失败次数：越少越优先 (权重 x50)
   - 冷却剩余时间：越短越优先

4. 【使用建议】
   - 1 个账号：每天最多 2-3 小时，搜索间隔 45-90 分钟
   - 2-3 个账号：轮换使用，每个账号每天最多 1 小时
   - 4+ 个账号：完全自动轮换，频率更低

5. 【状态管理】
   - ACTIVE: 正常使用
   - SUSPICIOUS: 可疑 (连续失败 1-2 次)
   - LIMITED: 受限 (搜索被限制)
   - BANNED: 封禁 (无法使用)
""")
    
    print("=" * 70)


if __name__ == "__main__":
    # 运行演示
    print("\n选择演示模式:")
    print("1. 轮换策略演示")
    print("2. 多账号搜索模拟")
    print("3. 轮换规则说明")
    
    choice = input("\n请输入选项 (1/2/3): ").strip()
    
    if choice == "1":
        demo_rotation_strategy()
    elif choice == "2":
        asyncio.run(simulate_multi_account_search())
    elif choice == "3":
        show_rotation_rules()
    else:
        print("无效选项")
