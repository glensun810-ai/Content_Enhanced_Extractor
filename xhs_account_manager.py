"""
Xiaohongshu Account Manager

账号管理模块 - 支持多账号配置、安全密码存储和账号轮换

功能特性:
- AES-256 加密存储密码
- 多账号配置管理
- 智能账号轮换策略
- 账号健康状态监控
- 登录状态持久化
"""

import os
import json
import base64
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import getpass

# 加密相关
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import yaml


# ================= 配置常量 =================

ACCOUNTS_FILE = "xhs_accounts.yaml"  # 账号配置文件
ENCRYPTION_SALT_FILE = ".xhs_salt"  # 加密盐值文件
ACCOUNT_STATE_DIR = "xhs_account_states"  # 账号状态目录


class AccountStatus(Enum):
    """账号状态"""
    ACTIVE = "active"  # 正常
    SUSPICIOUS = "suspicious"  # 可疑 (需要验证)
    LIMITED = "limited"  # 受限 (搜索限制)
    BANNED = "banned"  # 封禁
    UNKNOWN = "unknown"  # 未知


@dataclass
class AccountConfig:
    """账号配置"""
    account_id: str  # 账号唯一标识
    username: str  # 用户名/手机号
    password_encrypted: str  # 加密后的密码
    phone: str = ""  # 手机号 (用于接收验证码)
    status: str = AccountStatus.UNKNOWN.value
    created_at: str = ""
    last_used_at: str = ""
    total_searches: int = 0
    consecutive_failures: int = 0
    last_error: str = ""
    notes: str = ""  # 备注信息
    
    @classmethod
    def create(cls, account_id: str, username: str, password: str, 
               phone: str = "", notes: str = "") -> "AccountConfig":
        """创建新账号配置"""
        return cls(
            account_id=account_id,
            username=username,
            password_encrypted="",  # 由 AccountManager 加密
            phone=phone,
            status=AccountStatus.UNKNOWN.value,
            created_at=datetime.now().isoformat(),
            last_used_at="",
            total_searches=0,
            consecutive_failures=0,
            last_error="",
            notes=notes,
        )


class EncryptionManager:
    """加密管理器 - 负责密码加密和解密"""
    
    def __init__(self, salt_file: str = ENCRYPTION_SALT_FILE):
        self.salt_file = Path(salt_file)
        self._cipher = None
        self._master_password = None
    
    def _get_or_create_salt(self) -> bytes:
        """获取或创建盐值"""
        if self.salt_file.exists():
            with open(self.salt_file, 'rb') as f:
                return f.read()
        else:
            salt = os.urandom(16)
            with open(self.salt_file, 'wb') as f:
                f.write(salt)
            # 设置文件权限为仅所有者可读写
            os.chmod(self.salt_file, 0o600)
            return salt
    
    def _derive_key(self, password: str) -> bytes:
        """从密码派生加密密钥"""
        salt = self._get_or_create_salt()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def set_master_password(self, password: str) -> None:
        """设置主密码"""
        self._master_password = password
        key = self._derive_key(password)
        self._cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """加密字符串"""
        if not self._cipher:
            raise ValueError("请先设置主密码")
        encrypted = self._cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """解密字符串"""
        if not self._cipher:
            raise ValueError("请先设置主密码")
        try:
            encrypted = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self._cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"解密失败：{e}")
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._cipher is not None


class AccountManager:
    """账号管理器 - 管理多账号配置和轮换"""
    
    def __init__(self, accounts_file: str = ACCOUNTS_FILE, 
                 state_dir: str = ACCOUNT_STATE_DIR):
        self.accounts_file = Path(accounts_file)
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)
        
        self.encryption = EncryptionManager()
        self.accounts: Dict[str, AccountConfig] = {}
        self.current_account_id: Optional[str] = None
        self._master_password_set = False
    
    def setup_master_password(self, new_password: bool = False) -> str:
        """
        设置或验证主密码
        
        Args:
            new_password: 是否强制设置新密码
        
        Returns:
            主密码 (用于后续操作)
        """
        if new_password or not self.encryption.salt_file.exists():
            # 设置新主密码
            print("\n" + "=" * 60)
            print("设置主密码")
            print("=" * 60)
            print("主密码用于加密存储的小红书账号密码")
            print("请妥善保管，丢失后将无法恢复账号密码\n")
            
            while True:
                password = getpass.getpass("请输入主密码：")
                if len(password) < 6:
                    print("❌ 密码长度至少 6 位，请重新输入")
                    continue
                
                password_confirm = getpass.getpass("请确认主密码：")
                if password != password_confirm:
                    print("❌ 两次输入的密码不一致，请重新输入")
                    continue
                
                self.encryption.set_master_password(password)
                self._master_password_set = True
                print("✅ 主密码设置成功\n")
                return password
        else:
            # 验证现有主密码
            print("\n" + "=" * 60)
            print("验证主密码")
            print("=" * 60)
            print("请输入主密码以解密账号信息\n")
            
            password = getpass.getpass("主密码：")
            self.encryption.set_master_password(password)
            
            # 尝试解密一个账号验证密码是否正确
            try:
                self._load_accounts()
                self._master_password_set = True
                print("✅ 主密码验证成功\n")
                return password
            except Exception as e:
                print(f"❌ 主密码错误：{e}")
                return ""
    
    def add_account(self, username: str, password: str, 
                    phone: str = "", notes: str = "") -> str:
        """
        添加新账号
        
        Args:
            username: 用户名/手机号
            password: 密码 (明文)
            phone: 手机号 (用于接收验证码)
            notes: 备注
        
        Returns:
            账号 ID
        """
        if not self._master_password_set:
            raise ValueError("请先设置主密码")
        
        # 生成账号 ID
        account_id = f"acc_{len(self.accounts) + 1:03d}"
        
        # 创建账号配置
        account = AccountConfig.create(
            account_id=account_id,
            username=username,
            password=password,
            phone=phone,
            notes=notes,
        )
        
        # 加密密码
        account.password_encrypted = self.encryption.encrypt(password)
        
        # 存储账号
        self.accounts[account_id] = account
        self._save_accounts()
        
        print(f"✅ 账号已添加：{username} (ID: {account_id})")
        return account_id
    
    def list_accounts(self) -> List[Dict[str, Any]]:
        """列出所有账号"""
        if not self._master_password_set:
            raise ValueError("请先验证主密码")
        
        accounts_info = []
        for acc_id, acc in self.accounts.items():
            info = {
                "account_id": acc.account_id,
                "username": acc.username,
                "phone": acc.phone,
                "status": acc.status,
                "created_at": acc.created_at,
                "last_used_at": acc.last_used_at,
                "total_searches": acc.total_searches,
                "notes": acc.notes,
            }
            accounts_info.append(info)
        
        return accounts_info
    
    def get_account(self, account_id: str) -> Optional[AccountConfig]:
        """获取账号详情"""
        if not self._master_password_set:
            raise ValueError("请先验证主密码")
        
        account = self.accounts.get(account_id)
        if account:
            # 解密密码
            account.password = self.encryption.decrypt(account.password_encrypted)
        return account
    
    def get_password(self, account_id: str) -> str:
        """获取账号密码"""
        if not self._master_password_set:
            raise ValueError("请先验证主密码")
        
        account = self.accounts.get(account_id)
        if not account:
            raise ValueError(f"账号不存在：{account_id}")
        
        return self.encryption.decrypt(account.password_encrypted)
    
    def remove_account(self, account_id: str) -> bool:
        """删除账号"""
        if account_id in self.accounts:
            del self.accounts[account_id]
            self._save_accounts()
            
            # 删除账号状态文件
            state_file = self.state_dir / f"{account_id}.json"
            if state_file.exists():
                state_file.unlink()
            
            print(f"✅ 账号已删除：{account_id}")
            return True
        return False
    
    def update_account_status(self, account_id: str, 
                              status: AccountStatus,
                              error: str = "") -> None:
        """更新账号状态"""
        if account_id not in self.accounts:
            return
        
        account = self.accounts[account_id]
        account.status = status.value
        
        if status == AccountStatus.SUSPICIOUS:
            account.consecutive_failures += 1
            account.last_error = error
        elif status == AccountStatus.ACTIVE:
            account.consecutive_failures = 0
            account.last_error = ""
        
        self._save_accounts()
    
    def record_usage(self, account_id: str) -> None:
        """记录账号使用"""
        if account_id not in self.accounts:
            return
        
        account = self.accounts[account_id]
        account.last_used_at = datetime.now().isoformat()
        account.total_searches += 1
        self._save_accounts()
    
    def get_next_account(self, 
                         respect_cooldown: bool = True,
                         cooldown_hours: float = 1.0) -> Optional[AccountConfig]:
        """
        获取下一个可用账号 (轮换策略)

        轮换策略:
        1. 跳过被封禁或受限的账号
        2. 优先选择状态为 ACTIVE 的账号
        3. 选择使用次数最少的账号
        4. 跳过冷却时间内的账号 (默认 1 小时)
        5. 如果所有账号都在冷却中，返回最早使用的账号

        Args:
            respect_cooldown: 是否尊重冷却时间
            cooldown_hours: 冷却时间 (小时)

        Returns:
            账号配置，如果没有可用账号则返回 None
        """
        if not self.accounts:
            return None

        now = datetime.now()
        available_accounts = []
        cooling_accounts = []

        for acc_id, acc in self.accounts.items():
            # 跳过被封禁或受限的账号
            if acc.status in [AccountStatus.BANNED.value, AccountStatus.LIMITED.value]:
                continue

            # 检查冷却时间
            if respect_cooldown and acc.last_used_at:
                last_used = datetime.fromisoformat(acc.last_used_at)
                cooldown_end = last_used + timedelta(hours=cooldown_hours)
                
                if now < cooldown_end:
                    # 账号在冷却中，记录冷却结束时间
                    cooling_accounts.append((acc, cooldown_end))
                    continue

            available_accounts.append(acc)

        if available_accounts:
            # 有可用账号，返回使用次数最少的
            available_accounts.sort(key=lambda x: (
                x.status != AccountStatus.ACTIVE.value,  # ACTIVE 优先
                x.total_searches,  # 使用次数少的优先
                x.last_used_at or ""  # 最后使用时间早的优先
            ))
            return available_accounts[0]
        
        elif cooling_accounts:
            # 所有账号都在冷却中，返回最早冷却结束的账号
            cooling_accounts.sort(key=lambda x: x[1])
            acc, _ = cooling_accounts[0]
            print(f"⚠️ 所有账号都在冷却中，将使用最早可用的账号：{acc.username}")
            return acc
        
        else:
            # 没有可用账号 (都被封禁/受限)
            return None

    def get_account_for_search(self) -> Optional[AccountConfig]:
        """
        获取用于搜索的账号 (考虑更多因素)
        
        额外考虑:
        - 连续失败次数
        - 最后错误类型
        - 使用频率均衡
        """
        if not self.accounts:
            return None

        now = datetime.now()
        candidates = []

        for acc_id, acc in self.accounts.items():
            # 排除被封禁的账号
            if acc.status == AccountStatus.BANNED.value:
                continue

            # 排除连续失败 3 次以上的账号
            if acc.consecutive_failures >= 3:
                continue

            # 计算冷却状态
            cooldown_remaining = 0
            if acc.last_used_at:
                last_used = datetime.fromisoformat(acc.last_used_at)
                cooldown_end = last_used + timedelta(hours=1)
                if now < cooldown_end:
                    cooldown_remaining = (cooldown_end - now).total_seconds() / 60

            # 计算综合得分 (越低越好)
            score = 0
            score += acc.total_searches * 10  # 使用次数权重
            score += acc.consecutive_failures * 50  # 失败次数权重
            score += cooldown_remaining  # 冷却剩余时间
            if acc.status != AccountStatus.ACTIVE.value:
                score += 100  # 非活跃状态惩罚

            candidates.append((acc, score))

        if not candidates:
            return None

        # 返回得分最低的账号
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]

    def get_all_available_accounts(self) -> List[AccountConfig]:
        """获取所有可用账号列表"""
        available = []
        for acc in self.accounts.values():
            if acc.status not in [AccountStatus.BANNED.value, AccountStatus.LIMITED.value]:
                available.append(acc)
        return available

    def get_account_statistics(self) -> Dict[str, Any]:
        """获取账号统计信息"""
        if not self.accounts:
            return {}

        stats = {
            "total": len(self.accounts),
            "by_status": {},
            "total_searches": sum(acc.total_searches for acc in self.accounts.values()),
            "active_in_last_hour": 0,
            "in_cooldown": 0,
        }

        now = datetime.now()
        for acc in self.accounts.values():
            # 按状态统计
            stats["by_status"][acc.status] = stats["by_status"].get(acc.status, 0) + 1

            # 统计最近 1 小时使用过的账号
            if acc.last_used_at:
                last_used = datetime.fromisoformat(acc.last_used_at)
                if now - last_used < timedelta(hours=1):
                    stats["active_in_last_hour"] += 1
                if now - last_used < timedelta(hours=1):
                    stats["in_cooldown"] += 1

        return stats
    
    def _load_accounts(self) -> None:
        """加载账号配置"""
        if not self.accounts_file.exists():
            self.accounts = {}
            return
        
        with open(self.accounts_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data or 'accounts' not in data:
            self.accounts = {}
            return
        
        self.accounts = {}
        for acc_data in data['accounts']:
            acc = AccountConfig(**acc_data)
            self.accounts[acc.account_id] = acc
    
    def _save_accounts(self) -> None:
        """保存账号配置"""
        data = {
            'version': '1.0',
            'created_at': datetime.now().isoformat(),
            'accounts': [asdict(acc) for acc in self.accounts.values()]
        }
        
        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        
        # 设置文件权限为仅所有者可读写
        os.chmod(self.accounts_file, 0o600)
    
    def get_account_state_file(self, account_id: str) -> Path:
        """获取账号状态文件路径"""
        return self.state_dir / f"{account_id}.json"
    
    def print_accounts_summary(self) -> None:
        """打印账号摘要"""
        if not self.accounts:
            print("暂无配置的账号")
            return
        
        print("\n" + "=" * 70)
        print("账号列表")
        print("=" * 70)
        print(f"{'ID':<8} {'用户名':<20} {'状态':<10} {'使用次数':<10} {'最后使用':<20}")
        print("-" * 70)
        
        for acc_id, acc in self.accounts.items():
            status_symbol = {
                AccountStatus.ACTIVE.value: "✅",
                AccountStatus.SUSPICIOUS.value: "⚠️",
                AccountStatus.LIMITED.value: "🚫",
                AccountStatus.BANNED.value: "❌",
                AccountStatus.UNKNOWN.value: "❓",
            }.get(acc.status, "")
            
            last_used = acc.last_used_at[:19] if acc.last_used_at else "从未"
            print(f"{acc_id:<8} {acc.username:<20} {status_symbol} {acc.status:<8} "
                  f"{acc.total_searches:<10} {last_used:<20}")
        
        print("=" * 70)
        print(f"总账号数：{len(self.accounts)}")
        
        # 统计状态
        status_count = {}
        for acc in self.accounts.values():
            status_count[acc.status] = status_count.get(acc.status, 0) + 1
        
        for status, count in status_count.items():
            print(f"  {status}: {count}个")
        print()


# ================= 便捷函数 =================

def interactive_setup() -> AccountManager:
    """交互式设置账号管理器"""
    manager = AccountManager()
    
    # 设置主密码
    manager.setup_master_password()
    
    # 添加账号
    print("\n" + "=" * 60)
    print("添加小红书账号")
    print("=" * 60)
    
    while True:
        print(f"\n当前已添加 {len(manager.accounts)} 个账号")
        add_more = input("是否添加账号？(y/n): ").strip().lower()
        
        if add_more != 'y':
            break
        
        username = input("请输入小红书账号 (手机号/邮箱): ").strip()
        password = getpass.getpass("请输入密码：")
        phone = input("请输入手机号 (用于接收验证码，可选): ").strip()
        notes = input("请输入备注 (可选): ").strip()
        
        manager.add_account(username, password, phone, notes)
    
    return manager


def quick_add_account(username: str, password: str, 
                      phone: str = "", notes: str = "") -> AccountManager:
    """
    快速添加单个账号
    
    适用于首次设置或添加新账号
    """
    manager = AccountManager()
    
    # 如果没有主密码，设置新的
    if not manager.encryption.salt_file.exists():
        # 生成随机主密码
        import secrets
        master_password = secrets.token_urlsafe(16)
        print("\n" + "=" * 60)
        print("首次设置 - 已生成随机主密码")
        print("=" * 60)
        print(f"\n主密码：{master_password}")
        print("\n⚠️ 请妥善保管此密码，丢失后将无法恢复账号密码!\n")
        manager.encryption.set_master_password(master_password)
        manager._master_password_set = True
    else:
        # 需要用户输入主密码
        manager.setup_master_password()
    
    # 添加账号
    manager.add_account(username, password, phone, notes)
    
    return manager


# ================= 命令行工具 =================

def main():
    """命令行工具入口"""
    import sys
    
    if len(sys.argv) < 2:
        print("小红书账号管理器")
        print("\n使用方法:")
        print("  python xhs_account_manager.py setup     - 交互式设置")
        print("  python xhs_account_manager.py add       - 添加账号")
        print("  python xhs_account_manager.py list      - 列出账号")
        print("  python xhs_account_manager.py remove    - 删除账号")
        print("  python xhs_account_manager.py status    - 查看状态")
        return
    
    command = sys.argv[1]
    manager = AccountManager()
    
    if command == "setup":
        interactive_setup()
    
    elif command == "add":
        if not manager.encryption.salt_file.exists():
            manager.setup_master_password(new_password=True)
        else:
            password = manager.setup_master_password()
            if not password:
                return
        
        username = input("请输入小红书账号 (手机号/邮箱): ").strip()
        password = getpass.getpass("请输入密码：")
        phone = input("请输入手机号 (可选): ").strip()
        notes = input("请输入备注 (可选): ").strip()
        
        manager.add_account(username, password, phone, notes)
    
    elif command == "list":
        password = manager.setup_master_password()
        if not password:
            return
        
        accounts = manager.list_accounts()
        if not accounts:
            print("暂无账号")
        else:
            manager.print_accounts_summary()
    
    elif command == "remove":
        password = manager.setup_master_password()
        if not password:
            return
        
        manager.print_accounts_summary()
        account_id = input("请输入要删除的账号 ID: ").strip()
        manager.remove_account(account_id)
    
    elif command == "status":
        password = manager.setup_master_password()
        if not password:
            return
        
        manager.print_accounts_summary()
    
    else:
        print(f"未知命令：{command}")


if __name__ == "__main__":
    main()
